import os
from pathlib import Path
from io import StringIO
from typing import Optional, List, Dict, Any, Callable
import threading
import time
import asyncio
import sys
from contextlib import contextmanager

# Set environment variables for API keys and other configuration
# This should be done BEFORE importing aider modules
os.environ["OPENROUTER_API_KEY"] = "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"

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from aider.repo import GitRepo  # type: ignore
from aider.commands import Commands  # type: ignore
from aider.history import ChatSummary  # type: ignore
from aider.analytics import Analytics  # type: ignore


MODEL_NAME = "openrouter/google/gemini-2.5-flash-preview-05-20"

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
                        sys.stderr.write(f"Callback error: {e}\n")
                        sys.stderr.flush()

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
        try:
            output_capture.write(f"ERROR: {message}")
        except Exception:
            pass  # Don't let capture errors break aider
        if not suppress_terminal_output and original_tool_error:
            original_tool_error(message, strip=strip)

    def patched_tool_warning(message="", strip=True):
        """Patched version that captures tool warnings."""
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
                    sys.stderr.write(f"Completion callback error: {e}\n")
                    sys.stderr.flush()

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
                    sys.stderr.write(f"Completion callback error: {e}\n")
                    sys.stderr.flush()

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
    model_name: str = "gpt-4o-mini",
    files: Optional[List[str]] = None,
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
        code_theme="default",
    )

    # Create model instance
    main_model = Model(model_name)

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
        max_tokens = 4096
    elif isinstance(max_tokens, float):
        max_tokens = int(max_tokens)

    summarizer = ChatSummary(
        [main_model.weak_model, main_model],
        max_tokens,
    )

    # Create analytics (disabled for programmatic usage)
    analytics = Analytics(permanently_disable=True)

    # Convert file paths to absolute paths
    absolute_files = [str(Path(f).resolve()) for f in files]

    # Create coder instance FIRST, without any monkey patching
    coder = Coder.create(
        main_model=main_model,
        io=io,
        repo=repo,
        fnames=absolute_files,
        read_only_fnames=[],
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
        **kwargs
    )

    # Set up commands reference
    commands.coder = coder

    # NOW apply monkey patching after coder is successfully created
    monkey_patch_io_for_capture(io, output_capture, suppress_terminal_output)

    # Create streaming wrapper
    streaming_wrapper = StreamingAiderWrapper(coder, output_capture)

    return streaming_wrapper, output_capture


def example_simple_capture():
    """Simple example of capturing aider output."""

    print("=== Simple Output Capture Example ===")

    # Create test file
    test_file = "captured_test.py"
    with open(test_file, "w") as f:
        f.write("# This is a test file\n")

    try:
        # Create streaming aider coder
        streaming_coder, output_capture = create_streaming_aider_coder(
            model_name=MODEL_NAME,
            files=[test_file],
            dry_run=True,  # Safe mode
            verbose=False
        )

        print("Running aider command (output will be captured)...")

        # Execute command with capture
        result = streaming_coder.run_with_capture("add a print('Hello, World!') statement to this file")

        # Display results
        if result['success']:
            print("✓ Command executed successfully!")
            print(f"Execution time: {result['execution_time']:.2f} seconds")
            print(f"Model used: {result['model']}")
        else:
            print("✗ Command failed:", result['error'])

        print("\n--- Captured Output ---")
        print(result['captured_output'])

        print(f"\n--- Messages ({len(result['messages'])}) ---")
        for i, msg in enumerate(result['messages'][:5]):  # Show first 5 messages
            print(f"{i + 1}. [{msg['type']}] {msg['content'][:100]}...")

        return result

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up test file
        if Path(test_file).exists():
            Path(test_file).unlink()


def example_streaming_callback():
    """Example with streaming callbacks (no threading)."""

    print("=== Streaming Callback Example (Thread-Free) ===")

    # Create test file
    test_file = "streaming_test.py"
    with open(test_file, "w") as f:
        f.write("# Streaming test file\n")

    def response_callback(response_type: str, content: str):
        """Callback function for streaming responses."""
        # Use stderr to avoid stdout capture recursion
        sys.stderr.write(f"[CALLBACK {response_type}] {content[:50]}{'...' if len(content) > 50 else ''}\n")
        sys.stderr.flush()

    try:
        # Create streaming aider coder with terminal output suppressed
        print("Creating streaming aider coder...")
        streaming_coder, output_capture = create_streaming_aider_coder(
            model_name=MODEL_NAME,
            files=[test_file],
            dry_run=True,
            verbose=False,
            suppress_terminal_output=True  # This suppresses direct terminal output
        )
        print("✓ Aider coder created successfully")

        print("Running aider command with terminal output suppressed...")
        print("(You should only see callback output, not direct aider output)")

        # Execute with streaming callback - start without stdout capture to avoid hanging
        print("Starting aider execution...")
        result = streaming_coder.run_with_streaming_callback(
            "add a function that calculates fibonacci numbers",
            response_callback,
        )

        print(f"\nFinal result: {'Success' if result['success'] else 'Failed'}")
        if not result['success']:
            print(f"Error: {result.get('error', 'Unknown error')}")

        print("Note: All aider output was captured and only callbacks were shown!")

        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up test file
        if Path(test_file).exists():
            Path(test_file).unlink()


async def example_async_streaming():
    """Example of async streaming without threading."""

    print("=== Async Streaming Example ===")

    # Create test file
    test_file = "async_streaming_test.py"
    with open(test_file, "w") as f:
        f.write("# Async streaming test file\n")

    def response_callback(response_type: str, content: str):
        """Callback function for streaming responses."""
        # Use stderr to avoid stdout capture recursion
        sys.stderr.write(f"[ASYNC {response_type}] {content[:40]}{'...' if len(content) > 40 else ''}\n")
        sys.stderr.flush()

    try:
        # Create streaming aider coder
        streaming_coder, output_capture = create_streaming_aider_coder(
            model_name=MODEL_NAME,
            files=[test_file],
            dry_run=True,
            verbose=False,
            suppress_terminal_output=True,
        )

        print("Running async aider command with streaming callback...")

        # Execute with async streaming
        result = await streaming_coder.run_with_streaming_async(
            "create a class for managing user sessions with login and logout methods",
            response_callback,
        )

        print(f"\nAsync execution completed: {'Success' if result['success'] else 'Failed'}")
        print("Note: This ran without blocking the event loop!")
        print("=" * 60)
        print(output_capture.get_output())
        print("=" * 60)
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up test file
        if Path(test_file).exists():
            Path(test_file).unlink()


def example_custom_streaming():
    """Example of custom streaming implementation."""

    print("=== Custom Streaming Example ===")

    # Create test file
    test_file = "custom_streaming_test.py"
    with open(test_file, "w") as f:
        f.write("# Custom streaming test\n")

    try:
        streaming_coder, output_capture = create_streaming_aider_coder(
            model_name=MODEL_NAME,
            files=[test_file],
            dry_run=True,
            suppress_terminal_output=True
        )

        # Add multiple callbacks for different purposes
        responses = []

        def log_callback(response_type: str, content: str):
            responses.append(f"[{response_type}] {content}")

        def progress_callback(response_type: str, content: str):
            if response_type == 'assistant_response':
                sys.stderr.write(".")
                sys.stderr.flush()
            elif response_type == 'completion':
                sys.stderr.write(" Done!\n")
                sys.stderr.flush()

        streaming_coder.add_response_callback(log_callback)
        streaming_coder.add_response_callback(progress_callback)

        print("Running command with multiple callbacks: ", end="")

        result = streaming_coder.run_with_streaming_callback(
            "create a class for managing a todo list with add, remove, and list methods"
        )

        print(f"\nLogged {len(responses)} response chunks")
        print("Final status:", "Success" if result['success'] else "Failed")

        # Show some of the logged responses
        print("\nFirst 3 logged responses:")
        for i, response in enumerate(responses[:3]):
            print(f"{i + 1}. {response[:100]}...")

        return result, responses

    except Exception as e:
        print(f"Error: {e}")
        return None, []
    finally:
        if Path(test_file).exists():
            Path(test_file).unlink()


def test_basic_aider():
    """Test basic aider functionality without any customizations."""
    print("=== Basic Aider Test (No Customizations) ===")

    # Create test file
    test_file = "basic_test.py"
    with open(test_file, "w") as f:
        f.write("# Basic test file\n")

    try:
        print("Creating basic aider coder...")

        # Create minimal aider setup
        main_model = Model(MODEL_NAME)
        io = InputOutput(
            yes=True,
            dry_run=True,
        )

        coder = Coder.create(
            main_model=main_model,
            io=io,
            fnames=[test_file],
            dry_run=True,
            verbose=False,
            stream=False,  # Disable streaming for basic test
            auto_commits=False,
        )

        print("✓ Basic aider coder created")
        print("Running basic command...")

        # Simple test command
        result = coder.run("add a comment saying 'Hello from aider'")

        print(f"✓ Basic test completed: {result}")
        return True

    except Exception as e:
        print(f"✗ Basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if Path(test_file).exists():
            Path(test_file).unlink()


def test_minimal_streaming():
    """Minimal streaming test to debug hanging issues."""
    print("=== Minimal Streaming Test ===")

    # Create test file
    test_file = "minimal_test.py"
    with open(test_file, "w") as f:
        f.write("# Minimal test\n")

    io = None  # Initialize to avoid linter warning
    try:
        print("Creating minimal streaming setup...")

        # Create output capture
        output_capture = OutputCapture()

        # Create standard InputOutput
        io = InputOutput(
            yes=True,
            dry_run=True,
            pretty=False,
        )

        print("Applying minimal monkey patching...")
        # Apply only basic patching
        monkey_patch_io_for_capture(io, output_capture, suppress_terminal_output=True)

        # Create simple callback
        def test_callback(response_type: str, content: str):
            sys.stderr.write(f"[CALLBACK] {response_type}: {content[:30]}...\n")
            sys.stderr.flush()

        output_capture.add_callback(test_callback)

        # Create basic model and coder
        main_model = Model(MODEL_NAME)
        coder = Coder.create(
            main_model=main_model,
            io=io,
            fnames=[test_file],
            dry_run=True,
            verbose=False,
            stream=True,  # Enable streaming
            auto_commits=False,
        )

        print("✓ Minimal setup created")
        print("Running test command...")

        # Simple test
        result = coder.run("add a simple comment")

        print(f"✓ Minimal test completed: {type(result)}")
        return True

    except Exception as e:
        print(f"✗ Minimal test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if Path(test_file).exists():
            Path(test_file).unlink()
        # Restore methods
        if io is not None:
            restore_io_methods(io)


@contextmanager
def suppress_all_output():
    """Context manager that suppresses all stdout/stderr output completely."""
    # Save original streams
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Create dummy streams that discard everything
    class DevNull:

        def write(self, text):
            return len(text) if text else 0

        def flush(self):
            pass

        def isatty(self):
            return False

    try:
        # Replace with dummy streams
        sys.stdout = DevNull()
        sys.stderr = DevNull()
        yield
    finally:
        # Restore original streams
        sys.stdout = original_stdout
        sys.stderr = original_stderr


def debug_streaming_test():
    """Debug test to check what exactly is being captured."""
    print("=== DEBUG STREAMING TEST ===")

    # Create test file
    test_file = "debug_streaming_test.py"
    with open(test_file, "w") as f:
        f.write("# Debug streaming test\n")

    captured_responses = []

    def debug_callback(response_type: str, content: str):
        """Debug callback that tracks all responses."""
        captured_responses.append((response_type, content))
        # Use stderr to avoid stdout capture recursion
        sys.stderr.write(f"[DEBUG {response_type}] Length: {len(content)}, Content: {repr(content[:100])}...\n")
        sys.stderr.flush()

    try:
        # Create streaming aider coder
        streaming_coder, output_capture = create_streaming_aider_coder(
            model_name=MODEL_NAME,
            files=[test_file],
            dry_run=True,
            verbose=False,
            suppress_terminal_output=True,
        )

        print("Running debug command...")

        # Execute with streaming callback
        result = streaming_coder.run_with_streaming_callback(
            "add a simple hello world function",
            debug_callback,
        )

        print("\nDEBUG RESULTS:")
        print(f"Success: {result['success']}")
        print(f"Captured output length: {len(result['captured_output'])}")
        print(f"Total messages: {len(result['messages'])}")
        print(f"Callback responses captured: {len(captured_responses)}")

        print("\nCAPTURED OUTPUT:")
        print(repr(result['captured_output']))

        print("\nALL CALLBACK RESPONSES:")
        for i, (resp_type, content) in enumerate(captured_responses):
            print(f"{i + 1}. [{resp_type}] {repr(content[:50])}...")

        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if Path(test_file).exists():
            Path(test_file).unlink()


if __name__ == "__main__":
    # Check if API keys are set
    if not os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY") == "your-openrouter-key-here":
        print("=" * 60)
        print("API KEY SETUP REQUIRED")
        print("=" * 60)
        print("To use aider-chat with real AI models, you need to set up API keys:")
        print("  export OPENROUTER_API_KEY='your-actual-openrouter-key'")
        print("  # OR")
        print("  export OPENAI_API_KEY='your-actual-openai-key'")
        print("  export ANTHROPIC_API_KEY='your-actual-anthropic-key'")
        print()
        print("For testing the output capture functionality, we'll proceed with")
        print("placeholder keys (this will work for demonstration but not real AI calls).")
        print("=" * 60)
        print()

    print("Note: Running in dry_run mode for safety\n")

    # First run debug test
    print("=== DEBUG STREAMING TEST ===")
    debug_streaming_test()

    print("\n" + "=" * 60 + "\n")

    # First run basic test to make sure aider works at all
    print("=== BASIC AIDER TEST ===")
    if test_basic_aider():
        print("✓ Basic aider works, proceeding with streaming tests\n")
    else:
        print("✗ Basic aider failed, skipping streaming tests")
        exit(1)

    print("\n" + "=" * 60 + "\n")

    # Run minimal streaming test first
    print("=== MINIMAL STREAMING TEST ===")
    if test_minimal_streaming():
        print("✓ Minimal streaming test passed\n")
    else:
        print("✗ Minimal streaming test failed, this may indicate the core issue\n")

    print("\n" + "=" * 60 + "\n")

    # Run synchronous example
    print("=== SYNCHRONOUS STREAMING (Thread-Free) ===")
    example_streaming_callback()

    print("\n" + "=" * 60 + "\n")

    # Run async example
    print("=== ASYNC STREAMING ===")
    try:
        # Run the async example
        asyncio.run(example_async_streaming())
    except Exception as e:
        print(f"Async example failed: {e}")

    print("\n" + "=" * 60 + "\n")
    print("✓ All examples completed!")
    print("Both approaches avoid separate monitor threads:")
    print("  1. Synchronous: Callbacks called immediately when output is written")
    print("  2. Async: Non-blocking execution with immediate callbacks")
    print("\nNote: Some verbose output may still appear in terminal during coder creation,")
    print("but all assistant responses are captured and passed to callbacks.")
