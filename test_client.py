"""
FastA2A Test Client

This client demonstrates how to interact with a FastA2A agent using the A2AClient.
Run test_server.py first, then use this client to send tasks.
"""

import asyncio
import argparse
import json
from typing import Dict, Any

try:
    from fasta2a.client import A2AClient
    from fasta2a.schema import Message, TextPart
except ImportError as e:
    print(f"Error importing fasta2a: {e}")
    print("Make sure fasta2a is installed: pip install fasta2a")
    exit(1)

# Configuration constants
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 30

# Authentication configuration
DEFAULT_AUTH_TOKEN = "test-agent-token-123"  # Should match server token
USE_AUTH = True  # Set to False to disable authentication


class FastA2ATestClient:
    """A test client for interacting with FastA2A agents."""

    def __init__(self, server_url: str = DEFAULT_SERVER_URL, auth_token: str | None = None, use_auth: bool = USE_AUTH):
        self.client = A2AClient(base_url=server_url)
        self.server_url = server_url
        self.use_auth = use_auth

        # Set up authentication
        if use_auth:
            # Get token from parameter, environment variable, or default
            if auth_token:
                self.auth_token = auth_token
            else:
                import os
                self.auth_token = os.getenv('FASTA2A_AUTH_TOKEN', DEFAULT_AUTH_TOKEN)

            # Add authentication headers to HTTP client
            if self.auth_token:
                self.client.http_client.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                print("🔐 Authentication enabled with Bearer token")
            else:
                print("⚠️  Authentication enabled but no token provided")
                self.use_auth = False
        else:
            self.auth_token = ""
            print("🔓 Authentication disabled")

    async def get_agent_info(self) -> Dict[str, Any]:
        """Get the agent card to see what skills are available."""
        try:
            response = await self.client.http_client.get("/.well-known/agent.json")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get agent info: {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to connect to agent: {str(e)}"}

    async def send_task(self, text: str, history_length: int | None = None) -> Dict[str, Any]:
        """Send a task to the agent and return the result."""
        try:
            # Create message
            message = Message(
                role='user',
                parts=[TextPart(type='text', text=text)]
            )

            # Send task
            response = await self.client.send_task(
                message=message,
                history_length=history_length
            )

            return {
                "success": True,
                "task_id": response.get('result', {}).get('id'),
                "response": response
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get the result of a task by ID."""
        try:
            response = await self.client.get_task(task_id)
            return {
                "success": True,
                "response": response
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def wait_for_task_completion(self, task_id: str, max_wait: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Wait for a task to complete and return the final result."""
        import time
        start_time = time.time()

        while time.time() - start_time < max_wait:
            result = await self.get_task_result(task_id)

            if not result["success"]:
                return result

            task_data = result["response"].get("result", {})
            status = task_data.get("status", {})
            state = status.get("state", "unknown")

            if state in ["completed", "failed", "canceled"]:
                return {
                    "success": True,
                    "state": state,
                    "task": task_data
                }

            # Wait a bit before checking again
            await asyncio.sleep(0.5)

        return {
            "success": False,
            "error": f"Task did not complete within {max_wait} seconds"
        }

    async def send_and_wait(self, text: str, max_wait: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Send a task and wait for it to complete."""
        # Send the task
        send_result = await self.send_task(text)
        if not send_result["success"]:
            return send_result

        task_id = send_result["task_id"]
        if not task_id:
            return {"success": False, "error": "No task ID returned"}

        # Wait for completion
        return await self.wait_for_task_completion(task_id, max_wait)


# Test scenarios
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

LLM_TESTS = [
    "What is the capital of France?",
    "Explain quantum computing in simple terms",
    "Write a short poem about artificial intelligence",
    "Summarize the benefits of the FastA2A protocol",
    "Create a story about a robot learning to paint"
]


async def run_test_scenario(client: FastA2ATestClient, test_name: str, tests: list):
    """Run a series of tests."""
    print(f"\n🧪 Running {test_name} Tests")
    print("=" * 50)

    for i, test_text in enumerate(tests, 1):
        print(f"\n📝 Test {i}: {test_text}")

        result = await client.send_and_wait(test_text)

        if result["success"]:
            state = result["state"]
            task = result["task"]

            if state == "completed":
                # Extract response from the task
                history = task.get("history", [])
                if history:
                    last_message = history[-1]
                    if last_message.get("role") == "agent":
                        parts = last_message.get("parts", [])
                        for part in parts:
                            if part.get("type") == "text":
                                print(f"✅ Response: {part.get('text', 'No text content')}")
                                break
                        else:
                            print("✅ Task completed but no text response found")
                    else:
                        print("✅ Task completed but no agent response found")
                else:
                    print("✅ Task completed but no history available")

                # Show artifacts if available
                artifacts = task.get("artifacts", [])
                if artifacts:
                    print(f"📎 Artifacts: {len(artifacts)} created")

            elif state == "failed":
                print(f"❌ Task failed: {task.get('status', {}).get('message', 'Unknown error')}")
            else:
                print(f"⚠️  Task ended with state: {state}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")


async def interactive_mode(client: FastA2ATestClient):
    """Run in interactive mode where user can type commands."""
    print("\n🎮 Interactive Mode")
    print("Type 'quit' or 'exit' to stop")
    print("Type 'help' to see available commands")
    print("-" * 40)

    while True:
        try:
            user_input = input("\n💬 Enter task: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if not user_input:
                continue

            print("⏳ Processing...")
            result = await client.send_and_wait(user_input)

            if result["success"]:
                state = result["state"]
                task = result["task"]

                if state == "completed":
                    history = task.get("history", [])
                    if history:
                        last_message = history[-1]
                        if last_message.get("role") == "agent":
                            parts = last_message.get("parts", [])
                            for part in parts:
                                if part.get("type") == "text":
                                    print(f"🤖 {part.get('text', 'No response text')}")
                                    break
                elif state == "failed":
                    print(f"❌ Task failed: {task.get('status', {}).get('message', 'Unknown error')}")
                else:
                    print(f"⚠️  Task state: {state}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print("\n👋 Goodbye!")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="FastA2A Test Client")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help=f"Server URL (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("--auth-token", help=f"Bearer token for authentication (default: {DEFAULT_AUTH_TOKEN})")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--info", action="store_true", help="Show agent info and exit")
    parser.add_argument("--basic-tests", action="store_true", help="Run basic tests only")
    parser.add_argument("--llm-tests", action="store_true", help="Run LLM tests only")
    parser.add_argument("--task", help="Send a single task and exit")

    args = parser.parse_args()

    # Determine authentication settings
    use_auth = not args.no_auth
    auth_token = args.auth_token

    # Create client
    client = FastA2ATestClient(args.server, auth_token=auth_token, use_auth=use_auth)

    print(f"🔗 Connecting to FastA2A agent at: {args.server}")

    # Get agent info
    agent_info = await client.get_agent_info()
    if "error" in agent_info:
        print(f"❌ {agent_info['error']}")
        print("Make sure the test server is running with: python test_server.py")
        return

    if args.info:
        print("\n📋 Agent Information:")
        print(json.dumps(agent_info, indent=2))
        return

    print(f"✅ Connected to: {agent_info.get('name', 'Unknown Agent')}")
    print(f"📖 Description: {agent_info.get('description', 'No description')}")
    print(f"🛠️  Skills: {len(agent_info.get('skills', []))}")

    if args.task:
        print(f"\n📝 Sending task: {args.task}")
        result = await client.send_and_wait(args.task)

        if result["success"] and result["state"] == "completed":
            task = result["task"]
            history = task.get("history", [])
            if history:
                last_message = history[-1]
                if last_message.get("role") == "agent":
                    parts = last_message.get("parts", [])
                    for part in parts:
                        if part.get("type") == "text":
                            print(f"🤖 {part.get('text')}")
                            break
        else:
            print(f"❌ Error: {result.get('error', 'Task failed')}")
        return

    if args.interactive:
        await interactive_mode(client)
        return

    # Run tests
    if args.basic_tests or (not args.llm_tests):
        await run_test_scenario(client, "Basic", BASIC_TESTS)

    if args.llm_tests or (not args.basic_tests):
        # Check if agent supports LLM skills
        skills = agent_info.get('skills', [])
        llm_skills = [s for s in skills if 'llm' in s.get('tags', [])]

        if llm_skills:
            await run_test_scenario(client, "LLM", LLM_TESTS)
        else:
            print("\n📝 Skipping LLM tests - agent has no LLM skills")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
