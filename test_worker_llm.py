"""
LLM Worker Implementation for FastA2A Testing

This worker uses litellm to handle more sophisticated tasks requiring language model capabilities.
"""

import os
from typing import Any, List

try:
    import litellm
except ImportError:
    print("Warning: litellm not available. Install with: pip install litellm")
    litellm = None

from fasta2a import Worker
from fasta2a.schema import Artifact, Message, TaskIdParams, TaskSendParams, TextPart

# Configuration constants
DEFAULT_MODEL = "gpt-3.5-turbo"  # Can be changed to other models
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TIMEOUT = 30

# Alternative models you can use:
# "claude-3-sonnet" (requires ANTHROPIC_API_KEY)
# "openai/gpt-4" (requires OPENAI_API_KEY)
# "openrouter/meta-llama/llama-2-70b-chat" (requires OPENROUTER_API_KEY)
# "ollama/llama2" (requires local Ollama installation)


class LLMTestWorker(Worker):
    """An LLM-powered worker that can handle complex language tasks."""

    def __init__(self, broker, storage, model=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE):
        super().__init__(broker=broker, storage=storage)
        self.model = model
        self.temperature = temperature
        self.active_tasks = set()

        if litellm is None:
            raise ImportError("litellm is required for LLMTestWorker. Install with: pip install litellm")

        # Set up litellm configuration
        self._setup_litellm()

    def _setup_litellm(self):
        """Configure litellm with API keys and settings."""
        # Check for API keys in environment variables
        api_keys = {
            "OPENAI_API_KEY": ["openai", "gpt"],
            "ANTHROPIC_API_KEY": ["claude", "anthropic"],
            "OPENROUTER_API_KEY": ["openrouter"],
            "TOGETHER_API_KEY": ["together"],
            "REPLICATE_API_TOKEN": ["replicate"]
        }

        available_providers = []
        for env_var, providers in api_keys.items():
            if os.getenv(env_var):
                available_providers.extend(providers)

        if not available_providers:
            print("Warning: No API keys found in environment variables.")
            print("Set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY")
            print("For local models, you can use Ollama with models like 'ollama/llama2'")

        # Configure litellm settings
        if hasattr(litellm, 'set_verbose'):
            litellm.set_verbose = False  # Set to True for debugging

    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using LLM capabilities."""
        task_id = params['id']
        message = params['message']

        try:
            # Mark task as working
            await self.storage.update_task(task_id, state='working')
            self.active_tasks.add(task_id)

            # Process the message with LLM
            result = await self._process_with_llm(message)

            # Create artifacts from result
            artifacts = self.build_artifacts(result)

            # Create response message
            response_message = Message(
                role='agent',
                parts=[TextPart(type='text', text=result['response'])]
            )

            # Mark task as completed
            await self.storage.update_task(
                task_id,
                state='completed',
                message=response_message,
                artifacts=artifacts
            )

        except Exception as e:
            # Mark task as failed
            error_message = Message(
                role='agent',
                parts=[TextPart(type='text', text=f"LLM Error: {str(e)}")]
            )
            await self.storage.update_task(
                task_id,
                state='failed',
                message=error_message
            )
        finally:
            self.active_tasks.discard(task_id)

    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task."""
        task_id = params['id']
        if task_id in self.active_tasks:
            self.active_tasks.discard(task_id)
            await self.storage.update_task(task_id, state='canceled')

    async def _process_with_llm(self, message: Message) -> dict[str, Any]:
        """Process the message using an LLM."""
        # Extract text content from message parts
        user_content = ""
        for part in message['parts']:
            if part['type'] == 'text':
                user_content += part['text'] + " "

        user_content = user_content.strip()

        try:
            # Determine the type of task and create appropriate prompt
            system_prompt = self._create_system_prompt(user_content)

            # Call LLM
            response = await self._call_llm(system_prompt, user_content)

            return {
                'task_type': 'llm_processing',
                'response': response,
                'input': user_content,
                'model': self.model,
                'system_prompt': system_prompt
            }

        except Exception as e:
            return {
                'task_type': 'llm_processing',
                'response': f"Failed to process with LLM: {str(e)}",
                'input': user_content,
                'error': str(e)
            }

    def _create_system_prompt(self, user_content: str) -> str:
        """Create an appropriate system prompt based on the user's request."""
        content_lower = user_content.lower()

        if any(keyword in content_lower for keyword in ['summarize', 'summary', 'tldr']):
            return "You are a helpful assistant that creates clear, concise summaries. Focus on the key points and main ideas."

        elif any(keyword in content_lower for keyword in ['question', 'answer', 'explain', 'what', 'how', 'why']):
            return "You are a knowledgeable assistant that provides accurate, helpful answers to questions. Be clear and informative."

        elif any(keyword in content_lower for keyword in ['write', 'create', 'generate', 'compose']):
            return "You are a creative writing assistant. Help create well-structured, engaging content based on the user's requirements."

        elif any(keyword in content_lower for keyword in ['analyze', 'analysis', 'examine', 'evaluate']):
            return "You are an analytical assistant. Provide thorough, structured analysis with clear reasoning and insights."

        elif any(keyword in content_lower for keyword in ['translate', 'translation']):
            return "You are a translation assistant. Provide accurate translations while preserving meaning and context."

        elif any(keyword in content_lower for keyword in ['code', 'programming', 'function', 'algorithm']):
            return "You are a programming assistant. Provide clear, well-commented code solutions and explanations."

        else:
            return "You are a helpful, knowledgeable assistant. Respond appropriately to the user's request with accurate and useful information."

    async def _call_llm(self, system_prompt: str, user_content: str) -> str:
        """Make the actual LLM API call."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=DEFAULT_MAX_TOKENS,
                timeout=DEFAULT_TIMEOUT
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            # Try fallback to synchronous call if async fails
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    timeout=DEFAULT_TIMEOUT
                )
                return response.choices[0].message.content
            except Exception as sync_error:
                raise Exception(f"LLM call failed (async: {str(e)}, sync: {str(sync_error)})")

    def build_message_history(self, task_history: List[Message]) -> List[Any]:
        """Build message history for LLM context."""
        history = []
        for msg in task_history:
            content = ""
            for part in msg['parts']:
                if part['type'] == 'text':
                    content += part['text'] + " "

            history.append({
                'role': msg['role'],
                'content': content.strip()
            })

        return history

    def build_artifacts(self, result: Any) -> List[Artifact]:
        """Build artifacts from LLM result."""
        artifacts = []

        # Create a data artifact with the full result
        artifacts.append(Artifact(
            name="llm_result",
            description="Result from LLM processing",
            parts=[{
                'type': 'data',
                'data': result
            }],
            index=0
        ))

        # If the response is long enough, also create a text artifact
        if len(result.get('response', '')) > 100:
            artifacts.append(Artifact(
                name="llm_response_text",
                description="Text response from LLM",
                parts=[{
                    'type': 'text',
                    'text': result['response']
                }],
                index=1
            ))

        return artifacts


# Utility function to check if LLM worker can be used
def can_use_llm_worker() -> bool:
    """Check if LLM worker can be instantiated (litellm available and API keys set)."""
    if litellm is None:
        return False

    # Check for at least one API key
    api_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "TOGETHER_API_KEY",
        "REPLICATE_API_TOKEN"
    ]

    return any(os.getenv(key) for key in api_keys)


# Available models for different providers
AVAILABLE_MODELS = {
    "openai": [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo-preview"
    ],
    "anthropic": [
        "claude-3-sonnet",
        "claude-3-opus",
        "claude-3-haiku"
    ],
    "openrouter": [
        "openrouter/meta-llama/llama-2-70b-chat",
        "openrouter/anthropic/claude-3-sonnet",
        "openrouter/openai/gpt-4-turbo-preview"
    ],
    "ollama": [
        "ollama/llama2",
        "ollama/mistral",
        "ollama/codellama"
    ]
}
