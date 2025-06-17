import zipfile
import json
import os
import tempfile
import datetime
import platform
from typing import List, Dict, Any

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern

from python.helpers import files, runtime, git
from python.helpers.print_style import PrintStyle


class BackupService:
    """
    Core backup and restore service for Agent Zero.

    Features:
    - JSON-based metadata with user-editable path specifications
    - Comprehensive system information collection
    - Checksum validation for integrity
    - RFC compatibility through existing file helpers
    - Git version integration consistent with main application
    """

    def __init__(self):
        self.agent_zero_version = self._get_agent_zero_version()
        self.agent_zero_root = files.get_abs_path("")  # Resolved Agent Zero root
        self.user_home = os.path.expanduser("~")       # Current user's home directory

        # Build base paths map for pattern resolution
        self.base_paths = {
            self.agent_zero_root: self.agent_zero_root,
            self.user_home: self.user_home,
        }

    def get_default_backup_metadata(self) -> Dict[str, Any]:
        """Get default backup patterns and metadata"""
        timestamp = datetime.datetime.now().isoformat()

        default_patterns = self._get_default_patterns()
        include_patterns, exclude_patterns = self._parse_patterns(default_patterns)

        return {
            "backup_name": f"agent-zero-backup-{timestamp[:10]}",
            "include_hidden": False,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "backup_config": {
                "compression_level": 6,
                "integrity_check": True
            }
        }

    def _get_default_patterns(self) -> str:
        """Get default backup patterns with resolved absolute paths"""
        # Ensure paths don't have double slashes
        agent_root = self.agent_zero_root.rstrip('/')
        user_home = self.user_home.rstrip('/')

        return f"""# Agent Zero Knowledge (excluding defaults)
{agent_root}/knowledge/**
!{agent_root}/knowledge/default/**

# Agent Zero Instruments (excluding defaults)
{agent_root}/instruments/**
!{agent_root}/instruments/default/**

# Memory (excluding embeddings cache)
{agent_root}/memory/**
!{agent_root}/memory/embeddings/**

# Configuration and Settings (CRITICAL)
{agent_root}/.env
{agent_root}/tmp/settings.json
{agent_root}/tmp/chats/**
{agent_root}/tmp/scheduler/**
{agent_root}/tmp/uploads/**

# User Home Directory (excluding hidden files by default)
{user_home}/**
!{user_home}/.*/**
!{user_home}/.*"""

    def _get_agent_zero_version(self) -> str:
        """Get current Agent Zero version"""
        try:
            # Get version from git info (same as run_ui.py)
            gitinfo = git.get_git_info()
            return gitinfo.get("version", "development")
        except Exception:
            return "unknown"

    def _resolve_path(self, pattern_path: str) -> str:
        """Resolve pattern path to absolute system path (now patterns are already absolute)"""
        return pattern_path

    def _unresolve_path(self, abs_path: str) -> str:
        """Convert absolute path back to pattern path (now patterns are already absolute)"""
        return abs_path

    def _parse_patterns(self, patterns: str) -> tuple[list[str], list[str]]:
        """Parse patterns string into include and exclude pattern arrays"""
        include_patterns = []
        exclude_patterns = []

        for line in patterns.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('!'):
                # Exclude pattern
                exclude_patterns.append(line[1:])  # Remove the '!' prefix
            else:
                # Include pattern
                include_patterns.append(line)

        return include_patterns, exclude_patterns

    def _patterns_to_string(self, include_patterns: list[str], exclude_patterns: list[str]) -> str:
        """Convert pattern arrays back to patterns string for pathspec processing"""
        patterns = []

        # Add include patterns
        for pattern in include_patterns:
            patterns.append(pattern)

        # Add exclude patterns with '!' prefix
        for pattern in exclude_patterns:
            patterns.append(f"!{pattern}")

        return '\n'.join(patterns)

    async def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information for metadata"""
        import psutil

        try:
            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "architecture": platform.architecture()[0],
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu_count": str(psutil.cpu_count()),
                "memory_total": str(psutil.virtual_memory().total),
                "disk_usage": str(psutil.disk_usage('/').total if os.path.exists('/') else 0)
            }
        except Exception as e:
            return {"error": f"Failed to collect system info: {str(e)}"}

    async def _get_environment_info(self) -> Dict[str, Any]:
        """Collect environment information for metadata"""
        try:
            return {
                "user": os.environ.get("USER", "unknown"),
                "home": os.environ.get("HOME", "unknown"),
                "shell": os.environ.get("SHELL", "unknown"),
                "path": os.environ.get("PATH", "")[:200] + "..." if len(os.environ.get("PATH", "")) > 200 else os.environ.get("PATH", ""),
                "timezone": str(datetime.datetime.now().astimezone().tzinfo),
                "working_directory": os.getcwd(),
                "agent_zero_root": files.get_abs_path(""),
                "runtime_mode": "development" if runtime.is_development() else "production"
            }
        except Exception as e:
            return {"error": f"Failed to collect environment info: {str(e)}"}

    async def _get_backup_author(self) -> str:
        """Get backup author/system identifier"""
        try:
            import getpass
            username = getpass.getuser()
            hostname = platform.node()
            return f"{username}@{hostname}"
        except Exception:
            return "unknown"

    def _count_directories(self, matched_files: List[Dict[str, Any]]) -> int:
        """Count unique directories in file list"""
        directories = set()
        for file_info in matched_files:
            dir_path = os.path.dirname(file_info["path"])
            if dir_path:
                directories.add(dir_path)
        return len(directories)

    def _get_explicit_patterns(self, include_patterns: List[str]) -> set[str]:
        """Extract explicit (non-wildcard) patterns that should always be included"""
        explicit_patterns = set()

        for pattern in include_patterns:
            # If pattern doesn't contain wildcards, it's explicit
            if '*' not in pattern and '?' not in pattern:
                # Remove leading slash for comparison
                explicit_patterns.add(pattern.lstrip('/'))

                # Also add parent directories as explicit (so hidden dirs can be traversed)
                path_parts = pattern.lstrip('/').split('/')
                for i in range(1, len(path_parts)):
                    parent_path = '/'.join(path_parts[:i])
                    explicit_patterns.add(parent_path)

        return explicit_patterns

    def _is_explicitly_included(self, file_path: str, explicit_patterns: set[str]) -> bool:
        """Check if a file/directory is explicitly included in patterns"""
        relative_path = file_path.lstrip('/')
        return relative_path in explicit_patterns

    async def test_patterns(self, metadata: Dict[str, Any], max_files: int = 1000) -> List[Dict[str, Any]]:
        """Test backup patterns and return list of matched files"""
        include_patterns = metadata.get("include_patterns", [])
        exclude_patterns = metadata.get("exclude_patterns", [])
        include_hidden = metadata.get("include_hidden", False)

        # Convert to patterns string for pathspec
        patterns_string = self._patterns_to_string(include_patterns, exclude_patterns)

        # Parse patterns using pathspec
        pattern_lines = [line.strip() for line in patterns_string.split('\n') if line.strip() and not line.strip().startswith('#')]

        if not pattern_lines:
            return []

        # Get explicit patterns for hidden file handling
        explicit_patterns = self._get_explicit_patterns(include_patterns)

        matched_files = []
        processed_count = 0

        try:
            spec = PathSpec.from_lines(GitWildMatchPattern, pattern_lines)

            # Walk through base directories
            for base_pattern_path, base_real_path in self.base_paths.items():
                if not os.path.exists(base_real_path):
                    continue

                for root, dirs, files_list in os.walk(base_real_path):
                    # Filter hidden directories if not included, BUT allow explicit ones
                    if not include_hidden:
                        dirs_to_keep = []
                        for d in dirs:
                            if not d.startswith('.'):
                                dirs_to_keep.append(d)
                            else:
                                # Check if this hidden directory is explicitly included
                                dir_path = os.path.join(root, d)
                                pattern_path = self._unresolve_path(dir_path)
                                if self._is_explicitly_included(pattern_path, explicit_patterns):
                                    dirs_to_keep.append(d)
                        dirs[:] = dirs_to_keep

                    for file in files_list:
                        if processed_count >= max_files:
                            break

                        file_path = os.path.join(root, file)
                        pattern_path = self._unresolve_path(file_path)

                        # Skip hidden files if not included, BUT allow explicit ones
                        if not include_hidden and file.startswith('.'):
                            if not self._is_explicitly_included(pattern_path, explicit_patterns):
                                continue

                        # Remove leading slash for pathspec matching
                        relative_path = pattern_path.lstrip('/')

                        if spec.match_file(relative_path):
                            try:
                                stat = os.stat(file_path)
                                matched_files.append({
                                    "path": pattern_path,
                                    "real_path": file_path,
                                    "size": stat.st_size,
                                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                    "type": "file"
                                })
                                processed_count += 1
                            except (OSError, IOError):
                                # Skip files we can't access
                                continue

                    if processed_count >= max_files:
                        break

                if processed_count >= max_files:
                    break

        except Exception as e:
            raise Exception(f"Error processing patterns: {str(e)}")

        return matched_files

    async def create_backup(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str],
        include_hidden: bool = False,
        backup_name: str = "agent-zero-backup"
    ) -> str:
        """Create backup archive and return path to created file"""

        # Create metadata for test_patterns
        metadata = {
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "include_hidden": include_hidden
        }

        # Get matched files
        matched_files = await self.test_patterns(metadata, max_files=50000)

        if not matched_files:
            raise Exception("No files matched the backup patterns")

        # Create temporary zip file
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{backup_name}.zip")

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add comprehensive metadata
                metadata = {
                    # Basic backup information
                    "agent_zero_version": self.agent_zero_version,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "backup_name": backup_name,
                    "include_hidden": include_hidden,

                    # Pattern arrays for granular control during restore
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,

                    # System and environment information
                    "system_info": await self._get_system_info(),
                    "environment_info": await self._get_environment_info(),
                    "backup_author": await self._get_backup_author(),

                    # Backup configuration
                    "backup_config": {
                        "include_patterns": include_patterns,
                        "exclude_patterns": exclude_patterns,
                        "include_hidden": include_hidden,
                        "compression_level": 6,
                        "integrity_check": True
                    },

                    # File information
                    "files": [
                        {
                            "path": f["path"],
                            "size": f["size"],
                            "modified": f["modified"],
                            "type": "file"
                        }
                        for f in matched_files
                    ],

                    # Statistics
                    "total_files": len(matched_files),
                    "backup_size": sum(f["size"] for f in matched_files),
                    "directory_count": self._count_directories(matched_files),
                }

                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))

                # Add files
                for file_info in matched_files:
                    real_path = file_info["real_path"]
                    archive_path = file_info["path"].lstrip('/')

                    try:
                        if os.path.exists(real_path) and os.path.isfile(real_path):
                            zipf.write(real_path, archive_path)
                    except (OSError, IOError) as e:
                        # Log error but continue with other files
                        PrintStyle().warning(f"Warning: Could not backup file {real_path}: {e}")
                        continue

            return zip_path

        except Exception as e:
            # Cleanup on error
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise Exception(f"Error creating backup: {str(e)}")

    async def inspect_backup(self, backup_file) -> Dict[str, Any]:
        """Inspect backup archive and return metadata"""

        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "backup.zip")

        try:
            backup_file.save(temp_file)

            with zipfile.ZipFile(temp_file, 'r') as zipf:
                # Read metadata
                if "metadata.json" not in zipf.namelist():
                    raise Exception("Invalid backup file: missing metadata.json")

                metadata_content = zipf.read("metadata.json").decode('utf-8')
                metadata = json.loads(metadata_content)

                # Add file list from archive
                files_in_archive = [name for name in zipf.namelist() if name != "metadata.json"]
                metadata["files_in_archive"] = files_in_archive

                return metadata

        except zipfile.BadZipFile:
            raise Exception("Invalid backup file: not a valid zip archive")
        except json.JSONDecodeError:
            raise Exception("Invalid backup file: corrupted metadata")
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
