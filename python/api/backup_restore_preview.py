from python.helpers.api import ApiHandler
from flask import Request, Response
from werkzeug.datastructures import FileStorage
import tempfile
import os
import zipfile
import json
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern


class BackupRestorePreview(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Handle file upload
        if 'backup_file' not in request.files:
            return {"success": False, "error": "No backup file provided"}

        backup_file: FileStorage = request.files['backup_file']
        if backup_file.filename == '':
            return {"success": False, "error": "No file selected"}

        # Get restore patterns from form data
        metadata_json = request.form.get('metadata', '{}')

        try:
            metadata = json.loads(metadata_json)
            restore_include_patterns = metadata.get("include_patterns", [])
            restore_exclude_patterns = metadata.get("exclude_patterns", [])
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid metadata JSON"}

        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "backup.zip")

        files_to_restore = []
        skipped_files = []

        try:
            backup_file.save(temp_file)

            with zipfile.ZipFile(temp_file, 'r') as zipf:
                # Read backup metadata
                backup_metadata = {}
                if "metadata.json" in zipf.namelist():
                    metadata_content = zipf.read("metadata.json").decode('utf-8')
                    backup_metadata = json.loads(metadata_content)

                # Get files from archive (excluding metadata files)
                archive_files = [name for name in zipf.namelist()
                                 if name not in ["metadata.json", "checksums.json"]]

                # Create pathspec for restore patterns if provided
                restore_spec = None
                if restore_include_patterns or restore_exclude_patterns:
                    pattern_lines = []
                    for pattern in restore_include_patterns:
                        # Remove leading slash for pathspec matching
                        pattern_lines.append(pattern.lstrip('/'))
                    for pattern in restore_exclude_patterns:
                        # Remove leading slash for pathspec matching
                        pattern_lines.append(f"!{pattern.lstrip('/')}")

                    if pattern_lines:
                        restore_spec = PathSpec.from_lines(GitWildMatchPattern, pattern_lines)

                # Process each file in archive
                for archive_path in archive_files:
                    # Archive path is already the correct relative path (e.g., "a0/tmp/settings.json")
                    original_path = archive_path

                    # Determine target path (add leading slash for absolute path)
                    target_path = "/" + original_path

                    # Check if file matches restore patterns
                    if restore_spec:
                        if restore_spec.match_file(original_path):
                            files_to_restore.append({
                                "archive_path": archive_path,
                                "original_path": original_path,
                                "target_path": target_path,
                                "action": "restore"
                            })
                        else:
                            skipped_files.append({
                                "archive_path": archive_path,
                                "original_path": original_path,
                                "reason": "not_matched_by_pattern"
                            })
                    else:
                        # No patterns specified, restore all files
                        files_to_restore.append({
                            "archive_path": archive_path,
                            "original_path": original_path,
                            "target_path": target_path,
                            "action": "restore"
                        })

            return {
                "success": True,
                "files": files_to_restore,
                "skipped_files": skipped_files,
                "total_count": len(files_to_restore),
                "skipped_count": len(skipped_files),
                "backup_metadata": backup_metadata
            }

        except zipfile.BadZipFile:
            return {"success": False, "error": "Invalid backup file: not a valid zip archive"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid backup file: corrupted metadata"}
        except Exception as e:
            return {"success": False, "error": f"Error previewing restore: {str(e)}"}
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
