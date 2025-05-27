import os
from pathlib import Path
from io import StringIO
from typing import Optional, List, Dict, Any, Callable
import threading
import time
import asyncio
import sys
from contextlib import contextmanager

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from aider.repo import GitRepo  # type: ignore
from aider.commands import Commands  # type: ignore
from aider.history import ChatSummary  # type: ignore
from aider.analytics import Analytics  # type: ignore
from prompt_toolkit.enums import EditingMode

from python.helpers import settings
from python.helpers.settings import Settings
from python.helpers.print_style import PrintStyle

from models import get_api_key


conf: Settings = settings.get_settings()
MODEL_NAME = conf["chat_model_name"]
MODEL_PROVIDER = conf["chat_model_provider"]
MODEL_MAX_TOKENS = int(conf["chat_model_ctx_length"]) - int(conf["chat_model_ctx_history"])

for provider in ["OPENAI", "ANTHROPIC", "GROQ", "GOOGLE", "DEEPSEEK", "OPENROUTER", "SAMBANOVA", "MISTRALAI", "HUGGINGFACE", "CHUTES"]:
    api_key = get_api_key(provider)
    if api_key:
        os.environ[f"{provider}_API_KEY"] = api_key

# Global flag to prevent stdout patching recursion
_stdout_patching_active = False
_stdout_patching_lock = threading.RLock()

# Global flag to prevent double capture when stdout patching is active
_stdout_patch_mode_active = False


class OutputCapture:
    """Captures and buffers output from aider operations with immediate callback support."""

    def __init__(self):
        self.buffer = StringIO()
        self.messages: List[Dict[str, Any]] = []
        self.lock = threading.RLock()
        self.callbacks: List[Callable[[str, str], None]] = []

    def add_callback(self, callback: Callable[[str, str], None]):
        """Add a callback to be called immediately when output is written."""
        with self.lock:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, str], None]):
        """Remove a callback."""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)

    def clear_callbacks(self):
        """Clear all callbacks."""
        with self.lock:
            self.callbacks.clear()

    def write(self, text: str) -> int:
        """Write text to the buffer and immediately call callbacks (file-like interface)."""
        with self.lock:
            result = self.buffer.write(text)
            if text.strip():
                message = {
                    'type': 'output',
                    'content': text,
                    'timestamp': time.time()
                }
                self.messages.append(message)

                # Call callbacks immediately when output is written
                for callback in self.callbacks:
                    try:
                        callback('assistant_response', text)
                    except Exception as e:
                        # Don't let callback errors break the output capture
                        # Use stderr to avoid stdout capture recursion
                        PrintStyle().error(f"Callback error: {e}")

            return result

    def flush(self):
        """Flush the buffer."""
        self.buffer.flush()

    def readable(self) -> bool:
        """Required for file-like interface."""
        return False

    def writable(self) -> bool:
        """Required for file-like interface."""
        return True

    def isatty(self) -> bool:
        """Required for terminal interface."""
        return False

    def fileno(self) -> int:
        """Required for file-like interface."""
        raise OSError("OutputCapture has no file descriptor")

    # Terminal/prompt-toolkit compatibility attributes and methods
    @property
    def responds_to_cpr(self) -> bool:
        """Terminal capability - Cursor Position Report."""
        return False

    @property
    def encoding(self) -> str:
        """Text encoding."""
        return 'utf-8'

    @property
    def errors(self) -> str:
        """Error handling mode."""
        return 'strict'

    def get_output(self) -> str:
        """Get all captured output."""
        with self.lock:
            return self.buffer.getvalue()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all captured messages."""
        with self.lock:
            return self.messages.copy()

    def clear(self):
        """Clear the buffer and messages."""
        with self.lock:
            self.buffer = StringIO()
            self.messages = []


def monkey_patch_io_for_capture(io_instance, output_capture: OutputCapture, suppress_terminal_output: bool = True, patch_stdout: bool = False):
    """
    Monkey patch an InputOutput instance to capture output and call callbacks.

    This approach is much cleaner than inheritance and doesn't interfere with input methods.

    Args:
        io_instance: The InputOutput instance to patch
        output_capture: The OutputCapture instance to send output to
        suppress_terminal_output: Whether to suppress terminal output
        patch_stdout: Whether to patch sys.stdout.write (can cause hanging, use carefully)
    """
    # Store original methods
    original_assistant_output = getattr(io_instance, 'assistant_output', None)
    original_tool_output = getattr(io_instance, 'tool_output', None)
    original_tool_error = getattr(io_instance, 'tool_error', None)
    original_tool_warning = getattr(io_instance, 'tool_warning', None)
    original_ai_output = getattr(io_instance, 'ai_output', None)

    # Store original console and stdout/stderr for comprehensive capture
    original_console_print = None
    original_stdout_write = None
    original_stderr_write = None

    if hasattr(io_instance, 'console') and hasattr(io_instance.console, 'print'):
        original_console_print = io_instance.console.print

    # Only store stdout/stderr if explicitly requested to avoid hanging
    if patch_stdout:
        original_stdout_write = sys.stdout.write
        original_stderr_write = sys.stderr.write

    def patched_assistant_output(message, pretty=None):
        """Patched version that captures output and optionally calls original."""
        # Only capture via monkey-patch if stdout patching is not active
        if not _stdout_patch_mode_active:
            try:
                output_capture.write(str(message))
            except Exception:
                pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_assistant_output:
            original_assistant_output(message, pretty)

    def patched_tool_output(*messages, log_only=False, bold=False):
        """Patched version that captures tool output."""
        # Only capture via monkey-patch if stdout patching is not active
        if not _stdout_patch_mode_active:
            try:
                message_text = " ".join(str(msg) for msg in messages)
                if message_text:
                    output_capture.write(message_text)
            except Exception:
                pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_tool_output:
            original_tool_output(*messages, log_only=log_only, bold=bold)

    def patched_tool_error(message="", strip=True):
        """Patched version that captures tool errors."""
        # Only capture via monkey-patch if stdout patching is not active
        if not _stdout_patch_mode_active:
            try:
                output_capture.write(f"ERROR: {message}")
            except Exception:
                pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_tool_error:
            original_tool_error(message, strip=strip)

    def patched_tool_warning(message="", strip=True):
        """Patched version that captures tool warnings."""
        # Only capture via monkey-patch if stdout patching is not active
        if not _stdout_patch_mode_active:
            try:
                output_capture.write(f"WARNING: {message}")
            except Exception:
                pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_tool_warning:
            original_tool_warning(message, strip=strip)

    def patched_ai_output(content):
        """Patched version that captures ai output."""
        # Only capture via monkey-patch if stdout patching is not active
        if not _stdout_patch_mode_active:
            try:
                output_capture.write(str(content))
            except Exception:
                pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_ai_output:
            original_ai_output(content)

    def patched_console_print(*args, **kwargs):
        """Patched version that captures console.print output."""
        try:
            # Convert print arguments to string
            if args:
                message = " ".join(str(arg) for arg in args)
                output_capture.write(message)
        except Exception:
            pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_console_print:
            original_console_print(*args, **kwargs)

    def patched_stdout_write(text):
        """Patched version that captures direct stdout writes from aider streaming."""
        try:
            if text and text.strip():  # Only capture non-empty meaningful text
                output_capture.write(text)
        except Exception:
            pass  # Don't let capture errors break aider

        # Only write to original stdout if we're not suppressing terminal output
        if not suppress_terminal_output and original_stdout_write:
            return original_stdout_write(text)
        else:
            # When suppressing output, just return the expected length
            return len(text) if text else 0

    def patched_stderr_write(text):
        """Patched version that captures direct stderr writes."""
        try:
            if text and text.strip():  # Only capture non-empty meaningful text
                output_capture.write(f"STDERR: {text}")
        except Exception:
            pass  # Don't let capture errors break aider

        # Only write to original stderr if we're not suppressing terminal output
        if not suppress_terminal_output and original_stderr_write:
            return original_stderr_write(text)
        else:
            # When suppressing output, just return the expected length
            return len(text) if text else 0

    # Apply the patches
    if original_assistant_output:
        io_instance.assistant_output = patched_assistant_output
    if original_tool_output:
        io_instance.tool_output = patched_tool_output
    if original_tool_error:
        io_instance.tool_error = patched_tool_error
    if original_tool_warning:
        io_instance.tool_warning = patched_tool_warning
    if original_ai_output:
        io_instance.ai_output = patched_ai_output

    # Patch console.print if it exists
    if original_console_print:
        io_instance.console.print = patched_console_print  # type: ignore

    # Only patch stdout if explicitly requested to avoid hanging issues
    if patch_stdout and original_stdout_write:
        sys.stdout.write = patched_stdout_write  # type: ignore
        sys.stderr.write = patched_stderr_write  # type: ignore

    # Store original methods for potential restoration
    io_instance._original_methods = {
        'assistant_output': original_assistant_output,
        'tool_output': original_tool_output,
        'tool_error': original_tool_error,
        'tool_warning': original_tool_warning,
        'ai_output': original_ai_output,
        'console_print': original_console_print,
        'stdout_write': original_stdout_write if patch_stdout else None,
        'stderr_write': original_stderr_write if patch_stdout else None,
    }


def restore_io_methods(io_instance):
    """Restore original methods if they were monkey patched."""
    if hasattr(io_instance, '_original_methods'):
        for method_name, original_method in io_instance._original_methods.items():
            if original_method:
                if method_name == 'console_print' and hasattr(io_instance, 'console'):
                    io_instance.console.print = original_method
                elif method_name == 'stdout_write':
                    sys.stdout.write = original_method
                elif method_name == 'stderr_write':
                    sys.stderr.write = original_method
                else:
                    setattr(io_instance, method_name, original_method)
        delattr(io_instance, '_original_methods')


@contextmanager
def temporary_stdout_patch(output_capture):
    """Context manager to temporarily patch sys.stdout.write."""
    global _stdout_patch_mode_active
    original_stdout_write = sys.stdout.write

    def patched_stdout_write(text):
        """Temporarily patch stdout to capture aider's direct streaming output."""
        global _stdout_patching_active

        # Check if we're already in a patched stdout write to prevent infinite loops
        with _stdout_patching_lock:
            if _stdout_patching_active:
                # Don't capture output from callbacks to prevent recursion
                return len(text) if text else 0

            try:
                _stdout_patching_active = True
                if text and text.strip():  # Only capture non-empty meaningful text
                    output_capture.write(text)
            except Exception:
                pass  # Don't let capture errors break aider
            finally:
                _stdout_patching_active = False

        # Don't write to original stdout - we want to suppress terminal output
        return len(text) if text else 0

    try:
        # Set flag to prevent monkey-patched methods from also capturing
        _stdout_patch_mode_active = True
        # Patch stdout.write
        sys.stdout.write = patched_stdout_write  # type: ignore
        yield
    finally:
        # Always restore original stdout.write and clear flag
        _stdout_patch_mode_active = False
        sys.stdout.write = original_stdout_write  # type: ignore


class StreamingAiderWrapper:
    """Wrapper that provides streaming capabilities for Aider responses."""

    def __init__(self, coder: Coder, output_capture: OutputCapture):
        self.coder = coder
        self.output_capture = output_capture
        self.response_callbacks: List[Callable[[str, str], None]] = []

    def add_response_callback(self, callback: Callable[[str, str], None]):
        """
        Add a callback function that will be called with streaming responses.

        Args:
            callback: Function that takes (response_type, content) as arguments
        """
        self.response_callbacks.append(callback)

    def run_with_capture(self, message: str) -> Dict[str, Any]:
        """
        Run aider command and capture all output.

        Args:
            message: The instruction to send to aider

        Returns:
            Dict with execution results and captured output
        """
        # Clear previous output
        self.output_capture.clear()

        # Capture initial state
        initial_time = time.time()

        try:
            # Use context manager to patch stdout during execution
            with temporary_stdout_patch(self.output_capture):
                # Execute the aider command - now all output will be captured
                result = self.coder.run(message)

            # Get final captured output
            captured_output = self.output_capture.get_output()
            messages = self.output_capture.get_messages()

            return {
                'success': True,
                'result': result,
                'captured_output': captured_output,
                'messages': messages,
                'execution_time': time.time() - initial_time,
                'model': self.coder.main_model.name
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'captured_output': self.output_capture.get_output(),
                'messages': self.output_capture.get_messages(),
                'execution_time': time.time() - initial_time,
                'model': self.coder.main_model.name
            }

    def run_with_streaming_callback(self, message: str,
                                    response_callback: Optional[Callable[[str, str], None]] = None):
        """
        Run aider command with a callback for streaming responses (no threading).

        Args:
            message: The instruction to send to aider
            response_callback: Optional callback for streaming responses
        """
        if response_callback:
            self.add_response_callback(response_callback)

        # Add all registered callbacks to the output capture for immediate calling
        for callback in self.response_callbacks:
            self.output_capture.add_callback(callback)

        try:
            # Execute the command - callbacks will be called immediately as output is written
            result = self.run_with_capture(message)

            # Final callback with completion
            for callback in self.response_callbacks:
                try:
                    callback('completion', 'Command execution completed')
                except Exception as e:
                    PrintStyle().error(f"Completion callback error: {e}")

            return result

        finally:
            # Clean up: remove callbacks from output capture
            for callback in self.response_callbacks:
                self.output_capture.remove_callback(callback)

    async def run_with_streaming_async(self, message: str,
                                       response_callback: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
        """
        Async version of run_with_streaming_callback.

        Args:
            message: The instruction to send to aider
            response_callback: Optional callback for streaming responses

        Returns:
            Dict with execution results
        """
        if response_callback:
            self.add_response_callback(response_callback)

        # Add all registered callbacks to the output capture for immediate calling
        for callback in self.response_callbacks:
            self.output_capture.add_callback(callback)

        def _run_in_thread():
            """Wrapper function that runs in the executor thread with proper output suppression."""
            return self.run_with_capture(message)

        try:
            # Execute the command in a thread pool with proper output suppression
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _run_in_thread)

            # Final callback with completion
            for callback in self.response_callbacks:
                try:
                    callback('completion', 'Command execution completed')
                except Exception as e:
                    PrintStyle().error(f"Completion callback error: {e}")

            return result

        finally:
            # Clean up: remove callbacks from output capture
            for callback in self.response_callbacks:
                self.output_capture.remove_callback(callback)

    def __del__(self):
        """Ensure proper cleanup when wrapper is destroyed."""
        try:
            restore_io_methods(self.coder.io)
        except Exception:
            pass  # Don't let cleanup errors break anything


def create_streaming_aider_coder(
    model_name: str = MODEL_PROVIDER.lower() + "/" + MODEL_NAME,
    files: Optional[List[str]] = None,
    read_only_files: Optional[List[str]] = None,
    git_repo_path: Optional[str] = None,
    auto_commits: bool = True,
    verbose: bool = False,
    stream: bool = True,
    dry_run: bool = False,
    suppress_terminal_output: bool = True,
    **kwargs
) -> tuple[StreamingAiderWrapper, OutputCapture]:
    """
    Create an aider Coder instance with output capture and streaming capabilities.

    Args:
        model_name: The model to use
        files: List of files to add to the chat
        git_repo_path: Path to git repository
        auto_commits: Whether to auto-commit changes
        verbose: Enable verbose output
        stream: Enable streaming responses
        dry_run: Enable dry run mode
        suppress_terminal_output: If True, suppress direct terminal output (default: True)
        **kwargs: Additional arguments

    Returns:
        Tuple of (StreamingAiderWrapper, OutputCapture)
    """

    if files is None:
        files = []

    if read_only_files is None:
        read_only_files = []

    # Create output capture
    output_capture = OutputCapture()

    # Create standard InputOutput instance
    io = InputOutput(
        root=git_repo_path or os.getcwd(),
        pretty=False,  # Disable pretty output for capture
        yes=True,  # Auto-confirm prompts
        dry_run=dry_run,
        encoding="utf-8",
        user_input_color="green",
        tool_output_color="blue",
        tool_warning_color="yellow",
        tool_error_color="red",
        assistant_output_color="cyan",
        code_theme="default"
    )

    # Create model instance
    main_model = Model(model_name, editor_model=model_name, weak_model=model_name)

    # Setup git repository if path provided
    repo = None
    if git_repo_path:
        try:
            repo = GitRepo(
                io=io,
                fnames=files,
                git_dname=git_repo_path,
                attribute_author=True,
                attribute_committer=True,
            )
        except Exception as e:
            output_capture.write(f"Git repository setup failed: {e}\n")

    # Create commands instance
    commands = Commands(
        io=io,
        coder=None,  # Will be set later
        verbose=verbose,
    )

    # Create chat summarizer
    max_tokens = main_model.max_chat_history_tokens
    if max_tokens is None:
        max_tokens = MODEL_MAX_TOKENS
    elif isinstance(max_tokens, float):
        max_tokens = int(max_tokens)

    summarizer = ChatSummary(
        [main_model.weak_model, main_model],
        max_tokens,
    )

    # Create analytics (disabled for programmatic usage)
    analytics = Analytics(permanently_disable=True)

    # Create coder instance FIRST, without any monkey patching
    coder = Coder.create(
        main_model=main_model,
        io=io,
        repo=repo,
        fnames=files,
        read_only_fnames=read_only_files,
        show_diffs=True,
        auto_commits=auto_commits,
        dirty_commits=True,
        dry_run=dry_run,
        verbose=verbose,
        stream=stream,
        use_git=bool(repo),
        auto_lint=False,
        auto_test=False,
        commands=commands,
        summarizer=summarizer,
        analytics=analytics,
        suggest_shell_commands=True,
        git_repo_path=git_repo_path,
        edit_format="architect",
        restore_chat_history=True,
        detect_urls=True,
        auto_copy_context=True,
        auto_accept_architect=True,
        **kwargs
    )

    # Set up commands reference
    commands.coder = coder

    # NOW apply monkey patching after coder is successfully created
    monkey_patch_io_for_capture(io, output_capture, suppress_terminal_output)

    # Create streaming wrapper
    streaming_wrapper = StreamingAiderWrapper(coder, output_capture)

    return streaming_wrapper, output_capture
