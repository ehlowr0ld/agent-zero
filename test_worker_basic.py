"""
Basic Worker Implementation for FastA2A Testing

This worker handles simple tasks without requiring external LLM services.
"""

import json
import re
from typing import Any, List

from fasta2a import Worker
from fasta2a.schema import Artifact, Message, TaskIdParams, TaskSendParams, TextPart


class BasicTestWorker(Worker):
    """A basic worker that handles simple computational tasks without LLMs."""

    def __init__(self, broker, storage):
        super().__init__(broker=broker, storage=storage)
        self.active_tasks = set()

    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task based on the message content."""
        task_id = params['id']
        message = params['message']

        try:
            # Mark task as working
            await self.storage.update_task(task_id, state='working')
            self.active_tasks.add(task_id)

            # Process the message to determine task type and execute
            result = await self._process_message(message)

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
                parts=[TextPart(type='text', text=f"Error: {str(e)}")]
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

    async def _process_message(self, message: Message) -> dict[str, Any]:
        """Process the message and determine what task to perform."""
        # Extract text from message parts
        text_content = ""
        for part in message['parts']:
            if part['type'] == 'text':
                text_content += part['text'] + " "

        text_content = text_content.strip().lower()

        # Determine task type and execute
        if 'echo' in text_content or 'repeat' in text_content:
            return self._handle_echo_task(text_content)
        elif any(op in text_content for op in ['add', 'multiply', 'subtract', 'divide', 'math']):
            return self._handle_math_task(text_content)
        elif any(cmd in text_content for cmd in ['uppercase', 'lowercase', 'reverse', 'count']):
            return self._handle_text_task(text_content)
        elif 'json' in text_content and ('parse' in text_content or 'format' in text_content):
            return self._handle_json_task(text_content)
        else:
            return self._handle_general_task(text_content)

    def _handle_echo_task(self, text: str) -> dict[str, Any]:
        """Handle echo/repeat tasks."""
        # Extract the text to echo (after 'echo' or 'repeat')
        patterns = [r'echo\s+(.+)', r'repeat\s+(.+)']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                echo_text = match.group(1)
                return {
                    'task_type': 'echo',
                    'response': f"Echo: {echo_text}",
                    'input': echo_text
                }
        return {
            'task_type': 'echo',
            'response': f"Echo: {text}",
            'input': text
        }

    def _handle_math_task(self, text: str) -> dict[str, Any]:
        """Handle basic math operations."""
        try:
            # Extract numbers from the text
            numbers = re.findall(r'-?\d+\.?\d*', text)
            numbers = [float(n) for n in numbers]

            if len(numbers) < 2:
                return {
                    'task_type': 'math',
                    'response': "Error: Need at least two numbers for math operations",
                    'numbers': numbers
                }

            if 'add' in text or '+' in text:
                result = sum(numbers)
                operation = 'addition'
            elif 'multiply' in text or '*' in text:
                result = 1
                for n in numbers:
                    result *= n
                operation = 'multiplication'
            elif 'subtract' in text or '-' in text:
                result = numbers[0]
                for n in numbers[1:]:
                    result -= n
                operation = 'subtraction'
            elif 'divide' in text or '/' in text:
                result = numbers[0]
                for n in numbers[1:]:
                    if n == 0:
                        return {
                            'task_type': 'math',
                            'response': "Error: Division by zero",
                            'numbers': numbers
                        }
                    result /= n
                operation = 'division'
            else:
                return {
                    'task_type': 'math',
                    'response': f"Math result for numbers {numbers}: {sum(numbers)} (default: sum)",
                    'numbers': numbers,
                    'result': sum(numbers)
                }

            return {
                'task_type': 'math',
                'response': f"{operation.title()} of {numbers} = {result}",
                'numbers': numbers,
                'operation': operation,
                'result': result
            }

        except Exception as e:
            return {
                'task_type': 'math',
                'response': f"Error in math calculation: {str(e)}",
                'error': str(e)
            }

    def _handle_text_task(self, text: str) -> dict[str, Any]:
        """Handle text processing tasks."""
        # Extract the text to process (usually after the command)
        target_text = text

        if 'uppercase' in text:
            # Try to find text after 'uppercase'
            match = re.search(r'uppercase\s+(.+)', text)
            if match:
                target_text = match.group(1)
            result = target_text.upper()
            operation = 'uppercase'

        elif 'lowercase' in text:
            match = re.search(r'lowercase\s+(.+)', text)
            if match:
                target_text = match.group(1)
            result = target_text.lower()
            operation = 'lowercase'

        elif 'reverse' in text:
            match = re.search(r'reverse\s+(.+)', text)
            if match:
                target_text = match.group(1)
            result = target_text[::-1]
            operation = 'reverse'

        elif 'count' in text:
            match = re.search(r'count\s+(?:words?\s+in\s+)?(.+)', text)
            if match:
                target_text = match.group(1)
            word_count = len(target_text.split())
            char_count = len(target_text)
            result = f"Words: {word_count}, Characters: {char_count}"
            operation = 'count'
        else:
            result = target_text
            operation = 'unknown'

        return {
            'task_type': 'text_processing',
            'response': f"{operation.title()} result: {result}",
            'input': target_text,
            'operation': operation,
            'result': result
        }

    def _handle_json_task(self, text: str) -> dict[str, Any]:
        """Handle JSON parsing and formatting tasks."""
        try:
            # Try to find JSON in the text
            json_pattern = r'\{.*\}|\[.*\]'
            json_match = re.search(json_pattern, text, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed = json.loads(json_str)
                    formatted = json.dumps(parsed, indent=2)
                    return {
                        'task_type': 'json',
                        'response': f"Parsed and formatted JSON:\n{formatted}",
                        'input': json_str,
                        'parsed': parsed
                    }
                except json.JSONDecodeError as e:
                    return {
                        'task_type': 'json',
                        'response': f"Invalid JSON: {str(e)}",
                        'input': json_str,
                        'error': str(e)
                    }
            else:
                return {
                    'task_type': 'json',
                    'response': "No JSON found in the text",
                    'input': text
                }

        except Exception as e:
            return {
                'task_type': 'json',
                'response': f"Error processing JSON: {str(e)}",
                'error': str(e)
            }

    def _handle_general_task(self, text: str) -> dict[str, Any]:
        """Handle general/unknown tasks."""
        return {
            'task_type': 'general',
            'response': f"Processed general task: {text}",
            'input': text,
            'capabilities': [
                "echo <text> - repeat the text",
                "add/multiply/subtract/divide <numbers> - basic math",
                "uppercase/lowercase/reverse/count <text> - text processing",
                "parse/format json - JSON handling"
            ]
        }

    def build_message_history(self, task_history: List[Message]) -> List[Any]:
        """Build message history for task context."""
        return [
            {
                'role': msg['role'],
                'content': ' '.join(part.get('text', '') for part in msg['parts'] if part['type'] == 'text')
            }
            for msg in task_history
        ]

    def build_artifacts(self, result: Any) -> List[Artifact]:
        """Build artifacts from task result."""
        artifacts = []

        # Create a data artifact with the result
        artifacts.append(Artifact(
            name="task_result",
            description="Result of the processed task",
            parts=[{
                'type': 'data',
                'data': result
            }],
            index=0
        ))

        return artifacts
