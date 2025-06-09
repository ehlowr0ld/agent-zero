# FastA2A Testing Implementation

This repository contains a comprehensive testing implementation for Google's FastA2A (Agent-to-Agent) protocol using the `fasta2a` Python library.

## Overview

FastA2A is Google's agent-to-agent communication protocol that enables structured task-based interactions between AI agents. This implementation provides:

- **Basic Worker**: Handles simple computational tasks without LLM dependencies
- **LLM Worker**: Integrates with language models via litellm for sophisticated tasks
- **Test Server**: FastA2A-compliant server with both worker types
- **Test Client**: Comprehensive client for interacting with FastA2A agents
- **Example Tests**: Demonstrates protocol usage patterns

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Test Client   │────│   Test Server   │
│   (A2AClient)   │    │   (FastA2A)     │
└─────────────────┘    └─────────────────┘
                                │
                       ┌────────┴────────┐
                       │   TaskManager   │
                       └────────┬────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
            ┌───────▼────────┐      ┌──────▼──────┐
            │     Broker     │      │   Storage   │
            │   (InMemory)   │      │ (InMemory)  │
            └───────┬────────┘      └─────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐      ┌──────▼──────┐
│  BasicWorker   │      │ LLMWorker   │
│   (No LLM)     │      │ (litellm)   │
└────────────────┘      └─────────────┘
```

## Files

### Core Implementation

- **`test_worker_basic.py`**: Basic worker for simple tasks (echo, math, text processing, JSON)
- **`test_worker_llm.py`**: LLM-powered worker using litellm (Q&A, generation, summarization)
- **`test_server.py`**: FastA2A server with both workers
- **`test_client.py`**: Comprehensive client with test scenarios
- **`test_basic_functionality.py`**: Direct protocol testing without server

### Configuration Constants

Located at the top of each file:

#### Server Configuration (`test_server.py`)
```python
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_WORKERS = 2
```

#### LLM Configuration (`test_worker_llm.py`)
```python
DEFAULT_MODEL = "gpt-3.5-turbo"  # Can use: claude-3-sonnet, ollama/llama2, etc.
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TIMEOUT = 30
```

#### Client Configuration (`test_client.py`)
```python
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 30
```

## Installation

### Prerequisites

1. **Install fasta2a**:
   ```bash
   pip install fasta2a
   ```

2. **Install optional dependencies**:
   ```bash
   # For running the server
   pip install uvicorn

   # For LLM capabilities
   pip install litellm

   # For HTTP client functionality
   pip install httpx
   ```

### API Keys (Optional - for LLM features)

Set environment variables for your preferred LLM provider:

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# Anthropic Claude
export ANTHROPIC_API_KEY="your-anthropic-key"

# OpenRouter (multiple models)
export OPENROUTER_API_KEY="your-openrouter-key"

# For local models with Ollama (no API key needed)
# Just install Ollama and use model names like "ollama/llama2"
```

## Usage

### 1. Start the Test Server

```bash
python test_server.py
```

Options:
```bash
python test_server.py --host 0.0.0.0 --port 8080
python test_server.py --test-agent-card  # Test agent card generation
```

Expected output:
```
📝 LLM worker not available (no API keys or litellm missing)
📝 Only basic worker will be available
🚀 Starting FastA2A test server on 127.0.0.1:8000
📋 Agent card available at: http://127.0.0.1:8000/.well-known/agent.json
🔗 Main endpoint at: http://127.0.0.1:8000/
🛠️  Available skills: 4
```

### 2. Test with the Client

#### Run All Tests
```bash
python test_client.py
```

#### Interactive Mode
```bash
python test_client.py --interactive
```

#### Single Task
```bash
python test_client.py --task "add 15 and 27"
```

#### Specific Test Sets
```bash
python test_client.py --basic-tests    # Non-LLM tests only
python test_client.py --llm-tests      # LLM tests only (if available)
```

#### Agent Information
```bash
python test_client.py --info           # Show agent capabilities
```

### 3. Direct Protocol Testing

```bash
python test_basic_functionality.py
```

This tests the FastA2A protocol directly without running a server.

## Available Skills

### Basic Skills (No LLM Required)

1. **Echo/Repeat Text**
   - Examples: `echo Hello World!`, `repeat this message`
   - Returns the input text with an "Echo:" prefix

2. **Basic Mathematics**
   - Examples: `add 15 and 27`, `multiply 6 by 8`, `divide 100 by 5`
   - Supports: addition, subtraction, multiplication, division

3. **Text Processing**
   - Examples: `uppercase hello world`, `reverse FastA2A`, `count words in this sentence`
   - Operations: uppercase, lowercase, reverse, word/character counting

4. **JSON Processing**
   - Examples: `parse json {"name": "test"}`, `format json data`
   - Parses and formats JSON with error handling

### LLM Skills (Requires API Keys)

1. **Question Answering**
   - Examples: `What is the capital of France?`, `Explain quantum computing`
   - Uses appropriate system prompts for knowledge tasks

2. **Text Generation**
   - Examples: `Write a short story about robots`, `Create a poem about nature`
   - Creative content generation with context awareness

3. **Summarization**
   - Examples: `Summarize this article`, `Create a TLDR for this document`
   - Concise summary generation

## Testing Scenarios

### Basic Tests (Non-LLM)
```python
BASIC_TESTS = [
    "echo Hello World!",
    "add 15 and 27",
    "multiply 6 by 8",
    "uppercase hello world",
    "reverse FastA2A",
    "count words in this sentence",
    'parse json {"name": "test", "value": 42}',
    "help"
]
```

### LLM Tests (Requires API Keys)
```python
LLM_TESTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms",
    "Write a short poem about artificial intelligence",
    "Summarize the benefits of the FastA2A protocol",
    "Create a story about a robot learning to paint"
]
```

## Protocol Details

### Agent Card Endpoint

`GET /.well-known/agent.json`

Returns agent capabilities:
```json
{
  "name": "FastA2A Test Agent",
  "description": "A test agent demonstrating FastA2A capabilities",
  "version": "1.0.0",
  "skills": [...],
  "capabilities": {
    "streaming": false,
    "pushNotifications": false,
    "stateTransitionHistory": false
  },
  "authentication": {
    "schemes": []
  },
  "defaultInputModes": ["application/json"],
  "defaultOutputModes": ["application/json"]
}
```

### Task Submission

`POST /` with JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "tasks/send",
  "params": {
    "id": "task-uuid",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "echo Hello World!"
        }
      ]
    }
  }
}
```

### Task Retrieval

`POST /` with method `tasks/get`:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "tasks/get",
  "params": {
    "id": "task-uuid"
  }
}
```

## Customization

### Adding New Skills

1. **Extend BasicTestWorker**:
   ```python
   def _handle_new_skill(self, text: str) -> dict[str, Any]:
       # Your implementation
       return {
           'task_type': 'new_skill',
           'response': 'Response text',
           'input': text
       }
   ```

2. **Update skill detection in `_process_message()`**:
   ```python
   elif 'new_keyword' in text_content:
       return self._handle_new_skill(text_content)
   ```

3. **Add to agent skills**:
   ```python
   skills.append(Skill(
       id="new_skill",
       name="New Skill Name",
       description="Description of what it does",
       tags=["category", "keywords"],
       examples=["example command"],
       input_modes=["application/json"],
       output_modes=["application/json"]
   ))
   ```

### LLM Model Configuration

Change the model in `test_worker_llm.py`:

```python
# OpenAI models
DEFAULT_MODEL = "gpt-4"
DEFAULT_MODEL = "gpt-3.5-turbo"

# Anthropic models
DEFAULT_MODEL = "claude-3-sonnet"
DEFAULT_MODEL = "claude-3-opus"

# OpenRouter models
DEFAULT_MODEL = "openrouter/meta-llama/llama-2-70b-chat"

# Local Ollama models
DEFAULT_MODEL = "ollama/llama2"
DEFAULT_MODEL = "ollama/mistral"
```

## Troubleshooting

### Common Issues

1. **"fasta2a module not found"**
   ```bash
   pip install fasta2a
   ```

2. **"uvicorn module not found"**
   ```bash
   pip install uvicorn
   ```

3. **"LLM worker failed to initialize"**
   - Check API key environment variables
   - Install litellm: `pip install litellm`
   - Verify model name is correct

4. **"Failed to connect to agent"**
   - Ensure test server is running
   - Check host/port configuration
   - Verify firewall settings

5. **Server import errors**
   - Files must be in the same directory
   - Check Python path includes current directory

### Debugging

Enable verbose logging in LLM worker:
```python
litellm.set_verbose = True  # In _setup_litellm method
```

Add debug prints:
```python
print(f"Task {task_id} received: {text_content}")
```

## Examples

### Example 1: Basic Echo Task

Client:
```python
result = await client.send_and_wait("echo Hello FastA2A!")
print(result['task']['history'][-1]['parts'][0]['text'])
# Output: "Echo: echo Hello FastA2A!"
```

### Example 2: Math Calculation

Client:
```python
result = await client.send_and_wait("add 15 and 27")
print(result['task']['history'][-1]['parts'][0]['text'])
# Output: "Addition of [15.0, 27.0] = 42.0"
```

### Example 3: LLM Question (if configured)

Client:
```python
result = await client.send_and_wait("What is the capital of France?")
print(result['task']['history'][-1]['parts'][0]['text'])
# Output: "The capital of France is Paris. Paris is the largest city..."
```

## Protocol Compliance

This implementation follows the FastA2A specification:

- ✅ JSON-RPC 2.0 messaging
- ✅ Agent card discovery endpoint
- ✅ Task lifecycle management (submitted → working → completed/failed/canceled)
- ✅ Message history tracking
- ✅ Artifact generation
- ✅ Skill-based capability declaration
- ✅ Structured error handling

## Next Steps

1. **Production Deployment**: Add authentication, rate limiting, persistent storage
2. **Advanced Workers**: Implement file processing, web browsing, tool integration
3. **Multi-Agent**: Create agent networks with task delegation
4. **Streaming**: Add real-time streaming responses
5. **Push Notifications**: Implement notification endpoints

## License

This implementation is provided as-is for educational and testing purposes.
