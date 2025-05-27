# Aider Programming Guide

This guide explains how to programmatically configure and use the aider-chat package in your Python applications.

## Overview

Aider is typically used as a command-line tool, but it can also be integrated into Python applications programmatically. The key is understanding how aider initializes its configuration, which is normally done through command-line arguments, configuration files, and environment variables.

## Key Configuration Methods

### 1. Environment Variables (Recommended)

The most straightforward way to configure aider programmatically is through environment variables. These should be set **before** importing aider modules:

```python
import os

# API Keys
os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
os.environ["ANTHROPIC_API_KEY"] = "your-anthropic-api-key"
os.environ["OPENROUTER_API_KEY"] = "your-openrouter-api-key"
os.environ["GEMINI_API_KEY"] = "your-gemini-api-key"

# API Configuration
os.environ["OPENAI_API_BASE"] = "https://custom-endpoint.com/v1"
os.environ["OPENAI_API_VERSION"] = "2023-12-01-preview"
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_ORGANIZATION"] = "your-org-id"

# Other settings
os.environ["SSL_VERIFY"] = "false"  # Disable SSL verification if needed
```

### 2. Configuration Components

Aider's configuration involves several key components:

#### InputOutput (IO)
Handles all input/output operations, user interaction, and display formatting.

```python
from aider.io import InputOutput

io = InputOutput(
    pretty=True,           # Enable pretty output
    yes=True,             # Auto-confirm prompts
    dry_run=False,        # Set to True for testing
    encoding="utf-8",     # Text encoding
    user_input_color="green",
    tool_output_color="blue",
    tool_warning_color="yellow",
    tool_error_color="red",
    assistant_output_color="cyan",
    code_theme="default",  # Syntax highlighting theme
)
```

#### Model
Represents the AI model configuration.

```python
from aider.models import Model

# Basic model creation
model = Model("gpt-4o-mini")

# With additional models
model = Model(
    "gpt-4o",
    weak_model="gpt-4o-mini",      # For commit messages and summaries
    editor_model="gpt-4o-mini",    # For editing tasks
)
```

#### GitRepo (Optional)
Handles git repository integration.

```python
from aider.repo import GitRepo

repo = GitRepo(
    io=io,
    fnames=files,
    git_dname="/path/to/repo",
    attribute_author=True,
    attribute_committer=True,
)
```

#### Commands
Handles aider's command system.

```python
from aider.commands import Commands

commands = Commands(
    io=io,
    coder=None,  # Set after coder creation
    verbose=False,
)
```

#### Analytics
Handles usage analytics (typically disabled for programmatic use).

```python
from aider.analytics import Analytics

analytics = Analytics(permanently_disable=True)
```

### 3. Complete Configuration Function

Here's a complete function that sets up aider with proper configuration:

```python
def create_aider_coder(
    model_name="gpt-4o-mini",
    files=None,
    git_repo_path=None,
    auto_commits=True,
    verbose=False,
    stream=True,
    dry_run=False,
    **kwargs
):
    """
    Create a fully configured aider Coder instance.

    Args:
        model_name: AI model to use
        files: List of files to include in the chat
        git_repo_path: Path to git repository
        auto_commits: Enable automatic git commits
        verbose: Enable verbose output
        stream: Enable streaming responses
        dry_run: Test mode without making changes
        **kwargs: Additional Coder.create() arguments

    Returns:
        Configured Coder instance
    """
    # ... (see test_aider.py for full implementation)
```

## Suppressing Output and Streaming Responses

### Output Capture

By default, aider prints output directly to the terminal. To suppress this and capture output programmatically:

```python
from io import StringIO
from aider.io import InputOutput

# Create output capture buffer
output_buffer = StringIO()

# Configure InputOutput to use custom output
io = InputOutput(
    output=output_buffer,  # Redirect output to buffer
    pretty=False,          # Disable pretty formatting
    yes=True,             # Auto-confirm prompts
)

# After running aider commands
captured_output = output_buffer.getvalue()
print("Captured:", captured_output)
```

### Streaming Implementation

For streaming responses like traditional LLM APIs, use the `StreamingAiderWrapper`:

```python
from test_aider_streaming import create_streaming_aider_coder

# Create streaming-capable aider
streaming_coder, output_capture = create_streaming_aider_coder(
    model_name="gpt-4o-mini",
    files=["your_file.py"],
    capture_output=True
)

# Method 1: Simple capture
result = streaming_coder.run_with_capture("your instruction here")
print("Output:", result['captured_output'])

# Method 2: Streaming with callbacks
def response_callback(response_type, content):
    print(f"[{response_type}] {content}")

streaming_coder.run_with_streaming_callback(
    "your instruction here",
    response_callback
)
```

### Advanced Streaming Example

```python
class MyAiderStreamer:
    def __init__(self):
        self.responses = []

    def stream_callback(self, response_type: str, content: str):
        """Handle streaming responses."""
        self.responses.append({
            'type': response_type,
            'content': content,
            'timestamp': time.time()
        })

        # Real-time processing
        if response_type == 'assistant_response':
            # Process AI response chunks
            self.process_ai_response(content)
        elif response_type == 'completion':
            # Handle completion
            self.handle_completion()

    def process_ai_response(self, content: str):
        """Process AI response chunks in real-time."""
        # Your custom logic here
        print(f"AI: {content[:50]}...")

    def handle_completion(self):
        """Handle completion event."""
        print("✓ Command completed")

# Usage
streamer = MyAiderStreamer()
streaming_coder, output_capture = create_streaming_aider_coder(
    model_name="gpt-4o-mini",
    files=["app.py"],
    dry_run=True
)

streaming_coder.add_response_callback(streamer.stream_callback)
result = streaming_coder.run_with_streaming_callback(
    "refactor this code to use classes"
)
```

### Output Capture Patterns

#### Pattern 1: Silent Execution
```python
# Completely suppress aider output
streaming_coder, output_capture = create_streaming_aider_coder(
    capture_output=True,
    verbose=False
)

result = streaming_coder.run_with_capture("your command")
# Only your code prints to terminal, aider output is captured
```

#### Pattern 2: Custom Logging
```python
import logging

# Set up custom logger
logger = logging.getLogger('aider_integration')

def log_callback(response_type: str, content: str):
    logger.info(f"[{response_type}] {content}")

streaming_coder.add_response_callback(log_callback)
```

#### Pattern 3: Real-time UI Updates
```python
# For GUI applications
def ui_update_callback(response_type: str, content: str):
    if response_type == 'assistant_response':
        # Update progress bar or text widget
        update_ui_element(content)
    elif response_type == 'completion':
        # Show completion status
        show_completion_dialog()

streaming_coder.add_response_callback(ui_update_callback)
```

## Environment Variables Reference

### API Keys
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic (Claude) API key
- `OPENROUTER_API_KEY`: OpenRouter API key
- `GEMINI_API_KEY`: Google Gemini API key
- `DEEPSEEK_API_KEY`: DeepSeek API key
- `COHERE_API_KEY`: Cohere API key

### OpenAI Configuration
- `OPENAI_API_BASE`: Custom API endpoint
- `OPENAI_API_VERSION`: API version for Azure OpenAI
- `OPENAI_API_TYPE`: API type (e.g., "azure")
- `OPENAI_ORGANIZATION`: Organization ID

### Other Settings
- `SSL_VERIFY`: Set to "false" to disable SSL verification
- `AIDER_*`: Any command-line argument can be set as environment variable with AIDER_ prefix

## Model Selection

Aider supports many models. Some popular choices:

### OpenAI Models
- `gpt-4o`: Latest GPT-4 model
- `gpt-4o-mini`: Smaller, faster GPT-4 model
- `gpt-4-turbo`: Previous generation GPT-4

### Anthropic Models
- `claude-3-5-sonnet-20241022`: Latest Claude 3.5 Sonnet
- `claude-3-sonnet-20240229`: Claude 3 Sonnet
- `claude-3-haiku-20240307`: Claude 3 Haiku (faster, cheaper)

### Other Providers
- `openrouter/*`: Models via OpenRouter
- `gemini/*`: Google Gemini models
- `deepseek/*`: DeepSeek models

## Advanced Configuration

### Custom Model Settings

You can create custom model settings files:

**.aider.model.settings.yml**
```yaml
- name: my-custom-model
  edit_format: whole
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  streaming: true
```

### Custom Model Metadata

**.aider.model.metadata.json**
```json
{
  "my-custom-model": {
    "max_tokens": 4096,
    "max_input_tokens": 8192,
    "max_output_tokens": 4096,
    "input_cost_per_token": 0.00001,
    "output_cost_per_token": 0.00003
  }
}
```

### Configuration Files

Aider supports YAML configuration files:

**.aider.conf.yml**
```yaml
model: gpt-4o-mini
auto-commits: true
show-diffs: true
stream: true
edit-format: whole
```

## Error Handling

When using aider programmatically, handle these common exceptions:

```python
try:
    coder = create_aider_coder(model_name="gpt-4o-mini")
    coder.run("make a hello world script")
except Exception as e:
    if "API key" in str(e):
        print("API key not configured")
    elif "model" in str(e):
        print("Model not available")
    else:
        print(f"Unexpected error: {e}")
```

## Best Practices

1. **Set environment variables first**: Always configure environment variables before importing aider modules.

2. **Use dry_run for testing**: Set `dry_run=True` when testing to avoid making actual file changes.

3. **Disable analytics**: Set `Analytics(permanently_disable=True)` for programmatic usage.

4. **Handle git repositories**: Ensure your target directory is a git repository for full functionality.

5. **Choose appropriate models**: Use smaller models for development and larger ones for production.

6. **Error handling**: Always wrap aider operations in try-catch blocks.

7. **Output capture**: Use output capture to prevent terminal spam and enable custom handling.

8. **Streaming callbacks**: Implement callbacks for real-time response processing.

## Example Usage

### Basic Example
See `test_aider.py` for a complete working example that demonstrates:
- Setting up environment variables
- Creating a configured coder
- Executing commands
- Error handling

### Streaming Example
See `test_aider_streaming.py` for streaming capabilities:
- Output capture and suppression
- Streaming response callbacks
- Multiple callback handlers
- Custom response processing

Run the examples:
```bash
# Set your API key first
export OPENAI_API_KEY="your-key-here"

# Basic example
python test_aider.py

# Streaming example
python test_aider_streaming.py
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure aider-chat is installed: `pip install aider-chat`

2. **API key errors**: Verify environment variables are set correctly

3. **Model not found**: Check if the model name is correct and you have access

4. **Git errors**: Ensure you're in a git repository or provide a valid git path

5. **Permission errors**: Check file permissions and disk space

6. **Output not captured**: Ensure you're using the correct InputOutput configuration

7. **Streaming not working**: Verify callbacks are properly registered and threading is enabled

### Debug Mode

Enable verbose logging for troubleshooting:

```python
coder = create_aider_coder(
    model_name="gpt-4o-mini",
    verbose=True,  # Enable debug output
    dry_run=True,  # Safe testing mode
)
```

### Performance Tips

1. **Use smaller models for testing**: `gpt-4o-mini` is faster and cheaper than `gpt-4o`

2. **Enable streaming**: Set `stream=True` for real-time responses

3. **Disable pretty output**: Set `pretty=False` when capturing output

4. **Optimize file lists**: Only include necessary files in the chat context

5. **Use dry_run during development**: Avoid unnecessary API calls and file changes
