import os
import sys
from pathlib import Path
from io import StringIO
from typing import Optional, List, Generator, Dict, Any

# Set environment variables for API keys and other configuration
# This should be done BEFORE importing aider modules
os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-api-key-here"
# Example of other environment variables you can set:
# os.environ["OPENAI_API_BASE"] = "https://custom-endpoint.com/v1"
# os.environ["OPENROUTER_API_KEY"] = "your-openrouter-key"
# os.environ["GEMINI_API_KEY"] = "your-gemini-key"

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from aider.repo import GitRepo  # type: ignore
from aider.commands import Commands  # type: ignore
from aider.history import ChatSummary  # type: ignore
from aider.analytics import Analytics  # type: ignore


class CapturedOutput:
    """Captures output from aider operations."""

    def __init__(self):
        self.output_buffer = StringIO()
        self.messages: List[Dict[str, Any]] = []

    def write(self, text: str):
        """Write text to the buffer."""
        self.output_buffer.write(text)
        # You can also parse and categorize different types of messages here
        if text.strip():
            self.messages.append({
                'type': 'output',
                'content': text,
                'timestamp': str(Path().cwd())  # You could use actual timestamp
            })

    def flush(self):
        """Flush the buffer."""
        self.output_buffer.flush()

    def get_output(self) -> str:
        """Get all captured output."""
        return self.output_buffer.getvalue()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all captured messages."""
        return self.messages.copy()

    def clear(self):
        """Clear the buffer and messages."""
        self.output_buffer = StringIO()
        self.messages = []


class StreamingAiderCoder:
    """Wrapper for Aider that captures output and provides streaming capabilities."""

    def __init__(self, coder: Coder, captured_output: CapturedOutput):
        self.coder = coder
        self.captured_output = captured_output

    def run_with_streaming(self, message: str) -> Generator[Dict[str, Any], None, None]:
        """
        Run aider command and yield streaming responses.

        Args:
            message: The instruction to send to aider

        Yields:
            Dict with response chunks and metadata
        """
        # Clear previous output
        self.captured_output.clear()

        # Store original assistant_output method
        original_assistant_output = self.coder.io.assistant_output

        def streaming_assistant_output(content, pretty=None):
            """Custom assistant output that yields streaming responses."""
            # Yield the content as a streaming response
            yield {
                'type': 'assistant_response',
                'content': content,
                'timestamp': str(Path().cwd()),  # You could use actual timestamp
                'model': self.coder.main_model.name
            }
            # Also call the original method but capture its output
            original_assistant_output(content, pretty)

        # Temporarily replace the assistant output method
        self.coder.io.assistant_output = streaming_assistant_output

        try:
            # Execute the aider command
            # Note: This might not work exactly as expected because aider's streaming
            # is more complex. You may need to hook into the model's streaming directly.
            result = self.coder.run(message)

            # Yield final completion
            yield {
                'type': 'completion',
                'content': 'Command completed',
                'result': result,
                'captured_output': self.captured_output.get_output()
            }

        finally:
            # Restore original method
            self.coder.io.assistant_output = original_assistant_output

    def get_captured_output(self) -> str:
        """Get all captured output from aider operations."""
        return self.captured_output.get_output()

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all captured messages."""
        return self.captured_output.get_messages()


def create_aider_coder(
    model_name="gpt-4o-mini",
    files=None,
    git_repo_path=None,
    auto_commits=True,
    verbose=False,
    stream=True,
    dry_run=False,
    capture_output=True,
    **kwargs
) -> tuple[Coder, Optional[CapturedOutput]]:
    """
    Create an aider Coder instance with programmatic configuration.

    Args:
        model_name: The model to use (e.g., "gpt-4o-mini", "claude-3-sonnet-20240229")
        files: List of files to add to the chat
        git_repo_path: Path to git repository (if None, uses current directory)
        auto_commits: Whether to auto-commit changes
        verbose: Enable verbose output
        stream: Enable streaming responses
        dry_run: Enable dry run mode (don't make actual changes)
        capture_output: Whether to capture output instead of printing to terminal
        **kwargs: Additional arguments passed to Coder.create()

    Returns:
        Tuple of (Configured Coder instance, CapturedOutput instance if capture_output=True)
    """

    if files is None:
        files = []

    # Set up output capture if requested
    captured_output = None
    custom_output = None
    if capture_output:
        captured_output = CapturedOutput()
        custom_output = captured_output

    # Create InputOutput instance with configuration
    io = InputOutput(
        root=git_repo_path or os.getcwd(),  # Fixed root_path issue
        pretty=not capture_output,  # Disable pretty output if capturing
        yes=True,  # Auto-confirm prompts
        dry_run=dry_run,
        encoding="utf-8",
        output=custom_output,  # Redirect output to our capture object
        user_input_color="green",
        tool_output_color="blue",
        tool_warning_color="yellow",
        tool_error_color="red",
        assistant_output_color="cyan",
        code_theme="default",
    )

    # Create model instance
    try:
        main_model = Model(model_name)
    except Exception as e:
        if captured_output:
            captured_output.write(f"Failed to create model {model_name}: {e}")
        else:
            print(f"Failed to create model {model_name}: {e}")
        raise

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
            if captured_output:
                captured_output.write(f"Git repository setup failed: {e}")
            else:
                print(f"Git repository setup failed: {e}")

    # Create commands instance
    commands = Commands(
        io=io,
        coder=None,  # Will be set later
        verbose=verbose,
    )

    # Create chat summarizer with proper type handling
    max_tokens = main_model.max_chat_history_tokens
    if max_tokens is None:
        max_tokens = 4096  # Default fallback
    elif isinstance(max_tokens, float):
        max_tokens = int(max_tokens)  # Convert float to int

    summarizer = ChatSummary(
        [main_model.weak_model, main_model],
        max_tokens,
    )

    # Create analytics (disabled for programmatic usage)
    analytics = Analytics(permanently_disable=True)

    # Convert file paths to absolute paths
    absolute_files = [str(Path(f).resolve()) for f in files]

    # Create coder instance with all configuration
    try:
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

        return coder, captured_output

    except Exception as e:
        error_msg = f"Failed to create coder: {e}"
        if captured_output:
            captured_output.write(error_msg)
        else:
            print(error_msg)
        raise


def example_usage():
    """Example of how to use the configured aider coder with output capture."""

    # Create a test file to work with
    test_file = "greeting.py"
    if not Path(test_file).exists():
        with open(test_file, "w") as f:
            f.write("# A simple greeting script\n")

    try:
        # Create coder with output capture enabled
        coder, captured_output = create_aider_coder(
            model_name="gpt-4o-mini",  # Use a model you have API key for
            files=[test_file],
            git_repo_path=os.getcwd(),  # Use current directory as git repo
            auto_commits=True,
            verbose=False,  # Reduce verbosity when capturing
            stream=True,
            dry_run=True,  # Safe mode for testing
            capture_output=True,  # Enable output capture
        )

        print("Aider coder created successfully!")
        print(f"Model: {coder.main_model.name}")
        print(f"Files: {coder.abs_fnames}")
        print(f"Git repo: {coder.repo.root if coder.repo else 'None'}")

        # Create streaming wrapper
        streaming_coder = StreamingAiderCoder(coder, captured_output)

        # Execute a command with streaming
        print("\nExecuting command with streaming: 'make a script that prints hello world'")

        for response_chunk in streaming_coder.run_with_streaming("make a script that prints hello world"):
            print(f"[{response_chunk['type']}] {response_chunk['content'][:100]}...")

        # Get all captured output
        print("\n--- Captured Output ---")
        print(streaming_coder.get_captured_output())

        # Get structured messages
        print("\n--- Structured Messages ---")
        for msg in streaming_coder.get_messages():
            print(f"{msg['type']}: {msg['content'][:50]}...")

        return coder

    except Exception as e:
        print(f"Error: {e}")
        return None


def example_simple_capture():
    """Simple example of capturing aider output without streaming."""

    test_file = "simple_test.py"
    if not Path(test_file).exists():
        with open(test_file, "w") as f:
            f.write("# Simple test\n")

    try:
        # Create coder with output capture
        coder, captured_output = create_aider_coder(
            model_name="gpt-4o-mini",
            files=[test_file],
            dry_run=True,
            capture_output=True
        )

        print("Running aider command (output will be captured)...")

        # Run command - output goes to captured_output instead of terminal
        coder.run("add a print statement to this file")

        # Get the captured output
        output = captured_output.get_output()
        print("--- Captured Aider Output ---")
        print(output)

        return output

    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    # Check if API keys are set
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: No API keys found in environment variables.")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY before running.")
        print("You can also set other provider keys like OPENROUTER_API_KEY, GEMINI_API_KEY, etc.")
        sys.exit(1)

    print("=== Example 1: Simple Output Capture ===")
    example_simple_capture()

    print("\n=== Example 2: Streaming with Output Capture ===")
    example_usage()
