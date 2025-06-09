"""
Basic FastA2A Functionality Test

This script tests basic FastA2A functionality without complex dependencies.
It creates a minimal working example with just the basic worker.
"""

import asyncio
import json
from typing import Any, Dict

try:
    from fasta2a import FastA2A, Skill
    from fasta2a.broker import InMemoryBroker
    from fasta2a.storage import InMemoryStorage
    from fasta2a.worker import Worker
    from fasta2a.schema import Artifact, Message, TaskIdParams, TaskSendParams, TextPart
except ImportError as e:
    print(f"Error importing fasta2a: {e}")
    print("Install fasta2a with: pip install fasta2a")
    exit(1)


class SimpleTestWorker(Worker):
    """A very simple worker for basic testing."""

    def __init__(self, broker, storage):
        super().__init__(broker=broker, storage=storage)
        self.active_tasks = set()

    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a simple task."""
        task_id = params['id']
        message = params['message']

        try:
            # Mark task as working
            await self.storage.update_task(task_id, state='working')
            self.active_tasks.add(task_id)

            # Get text from message
            text_content = ""
            for part in message['parts']:
                if part['type'] == 'text':
                    text_content += part['text']

            # Simple processing
            if 'echo' in text_content.lower():
                response_text = f"Echo: {text_content}"
            elif 'hello' in text_content.lower():
                response_text = "Hello! I'm a FastA2A test agent."
            elif 'add' in text_content.lower():
                try:
                    # Simple math: extract two numbers and add them
                    import re
                    numbers = re.findall(r'\d+', text_content)
                    if len(numbers) >= 2:
                         result = int(numbers[0]) + int(numbers[1])
                         response_text = f"Adding {numbers[0]} + {numbers[1]} = {result}"
                     else:
                         response_text = "Please provide two numbers to add"
                 except Exception:
                     response_text = "Error processing math request"
            else:
                response_text = f"I received: {text_content}. Try 'echo <text>', 'hello', or 'add <num1> <num2>'"

            # Create response
            response_message = Message(
                role='agent',
                parts=[TextPart(type='text', text=response_text)]
            )

            # Mark as completed
            await self.storage.update_task(
                task_id,
                state='completed',
                message=response_message
            )

        except Exception as e:
            # Mark as failed
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
        """Cancel a task."""
        task_id = params['id']
        if task_id in self.active_tasks:
            self.active_tasks.discard(task_id)
            await self.storage.update_task(task_id, state='canceled')

    def build_message_history(self, task_history) -> list:
        """Build message history."""
        return [
            {
                'role': msg['role'],
                'content': ' '.join(part.get('text', '') for part in msg['parts'] if part['type'] == 'text')
            }
            for msg in task_history
        ]

    def build_artifacts(self, result: Any) -> list:
        """Build artifacts."""
        return []


class SimpleBroker(InMemoryBroker):
    """A simple broker that runs one worker."""

    def __init__(self, worker):
        super().__init__()
        self.worker = worker
        self.running = False

    async def __aenter__(self):
        await super().__aenter__()
        self.running = True
        # Start worker task
        asyncio.create_task(self._run_worker())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.running = False
        await super().__aexit__(exc_type, exc_value, traceback)

    async def _run_worker(self):
        """Run the worker loop."""
        async with self.worker.run():
            while self.running:
                await asyncio.sleep(0.1)


async def test_basic_functionality():
    """Test basic FastA2A functionality."""
    print("🧪 Testing Basic FastA2A Functionality")
    print("=" * 40)

    # Create components
    storage = InMemoryStorage()
    worker = SimpleTestWorker(broker=None, storage=storage)  # Will set broker later
    broker = SimpleBroker(worker)
    worker.broker = broker  # Set the broker reference

    # Create skills
    skills = [
        Skill(
            id="echo",
            name="Echo Text",
            description="Echoes back the provided text",
            tags=["text", "echo"],
            examples=["echo hello world"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        ),
        Skill(
            id="greeting",
            name="Greeting",
            description="Responds to greetings",
            tags=["social", "greeting"],
            examples=["hello", "hi there"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        ),
        Skill(
            id="math",
            name="Simple Math",
            description="Basic addition",
            tags=["math", "calculation"],
            examples=["add 5 and 3"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        )
    ]

    # Create FastA2A app
    app = FastA2A(
        storage=storage,
        broker=broker,
        name="Simple Test Agent",
        url="http://localhost:8000",
        version="1.0.0",
        description="A simple test agent for FastA2A",
        skills=skills
    )

    print("✅ FastA2A app created successfully")

    # Test agent card
    print("\n📋 Testing agent card...")

    # Mock request
    from unittest.mock import Mock
    mock_request = Mock()

    response = await app._agent_card_endpoint(mock_request)
    agent_card = json.loads(response.body)

    print(f"📄 Agent name: {agent_card.get('name')}")
    print(f"📝 Description: {agent_card.get('description')}")
    print(f"🛠️ Skills: {len(agent_card.get('skills', []))}")

    # Test task submission and execution
    print("\n📤 Testing task submission...")

    # Start the task manager
    async with app.task_manager:
        # Test 1: Echo task
        print("\n🧪 Test 1: Echo task")

        # Create a task request
        from fasta2a.schema import SendTaskRequest, TaskSendParams

        message = Message(
            role='user',
            parts=[TextPart(type='text', text='echo Hello FastA2A!')]
        )

        task_params = TaskSendParams(
            id='test-task-1',
            message=message
        )

        request = SendTaskRequest(
            jsonrpc='2.0',
            id='req-1',
            method='tasks/send',
            params=task_params
        )

        # Send task
        send_response = await app.task_manager.send_task(request)

        if 'error' in send_response:
            print(f"❌ Error sending task: {send_response['error']}")
        else:
            print("✅ Task submitted successfully")

            # Wait a bit for processing
            await asyncio.sleep(1)

            # Get task result
            from fasta2a.schema import GetTaskRequest

            get_request = GetTaskRequest(
                jsonrpc='2.0',
                id='req-2',
                method='tasks/get',
                params={'id': 'test-task-1'}
            )

            get_response = await app.task_manager.get_task(get_request)

            if 'error' in get_response:
                print(f"❌ Error getting task: {get_response['error']}")
            else:
                task = get_response['result']
                status = task.get('status', {})
                state = status.get('state', 'unknown')

                print(f"📊 Task state: {state}")

                if state == 'completed':
                    history = task.get('history', [])
                    if history:
                        last_message = history[-1]
                        if last_message.get('role') == 'agent':
                            parts = last_message.get('parts', [])
                            for part in parts:
                                if part.get('type') == 'text':
                                    print(f"🤖 Response: {part.get('text')}")
                                    break

        # Test 2: Math task
        print("\n🧪 Test 2: Math task")

        message2 = Message(
            role='user',
            parts=[TextPart(type='text', text='add 15 and 27')]
        )

        task_params2 = TaskSendParams(
            id='test-task-2',
            message=message2
        )

        request2 = SendTaskRequest(
            jsonrpc='2.0',
            id='req-3',
            method='tasks/send',
            params=task_params2
        )

        send_response2 = await app.task_manager.send_task(request2)

        if 'error' in send_response2:
            print(f"❌ Error sending math task: {send_response2['error']}")
        else:
            print("✅ Math task submitted successfully")

            # Wait for processing
            await asyncio.sleep(1)

            # Get result
            get_request2 = GetTaskRequest(
                jsonrpc='2.0',
                id='req-4',
                method='tasks/get',
                params={'id': 'test-task-2'}
            )

            get_response2 = await app.task_manager.get_task(get_request2)

            if 'error' in get_response2:
                print(f"❌ Error getting math task: {get_response2['error']}")
            else:
                task2 = get_response2['result']
                status2 = task2.get('status', {})
                state2 = status2.get('state', 'unknown')

                print(f"📊 Math task state: {state2}")

                if state2 == 'completed':
                    history2 = task2.get('history', [])
                    if history2:
                        last_message2 = history2[-1]
                        if last_message2.get('role') == 'agent':
                            parts2 = last_message2.get('parts', [])
                            for part in parts2:
                                if part.get('type') == 'text':
                                    print(f"🤖 Math response: {part.get('text')}")
                                    break

    print("\n✅ Basic functionality test completed!")


async def main():
    """Main function."""
    try:
        await test_basic_functionality()
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
