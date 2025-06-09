#!/usr/bin/env python3
"""
FastA2A Test Client with Authentication

This client demonstrates FastA2A agent interaction with Bearer token authentication.
It supports both basic and LLM testing scenarios.
"""

import asyncio
import argparse
import json
import httpx
from typing import Dict, Any

from fasta2a.client import A2AClient
from fasta2a.schema import Message

# Import authentication utilities
from test_auth_setup import SimpleAuthManager, create_auth_headers, get_auth_token

# Configuration constants
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 30


class AuthenticatedA2AClient:
    """An authenticated client for the A2A protocol."""

    def __init__(self, server_url: str = DEFAULT_SERVER_URL, auth_token: str | None = None, use_auth: bool = True):
        self.server_url = server_url
        self.use_auth = use_auth

        # Set up authentication
        if use_auth:
            self.auth_token = auth_token or get_auth_token()

            # Create HTTP client with authentication headers
            headers = create_auth_headers(self.auth_token)
            self.http_client = httpx.AsyncClient(base_url=server_url, headers=headers)

            print("🔐 Authentication enabled with Bearer token")
        else:
            self.http_client = httpx.AsyncClient(base_url=server_url)
            self.auth_token = ""
            print("🔓 Authentication disabled")

        # Create A2A client with our authenticated HTTP client
        self.client = A2AClient(base_url=server_url, http_client=self.http_client)

    async def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information from the /.well-known/agent.json endpoint."""
        try:
            # Agent card endpoint is typically public, so we can access it without auth
            # But we'll still use our client to be consistent
            response = await self.http_client.get("/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"error": f"Failed to get agent info: {e}"}

    async def send_task(self, text: str, history_length: int | None = None) -> Dict[str, Any]:
        """Send a task to the agent."""
        try:
            message = Message(role="user", parts=[{"type": "text", "text": text}])
            response = await self.client.send_task(message, history_length=history_length)

            if hasattr(response, 'error') and response.error:
                return {"error": response.error.message, "success": False}
            else:
                return {"task_id": response.result.id, "success": True}

        except Exception as e:
            return {"error": str(e), "success": False}

    async def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get the result of a task."""
        try:
            response = await self.client.get_task(task_id)

            if hasattr(response, 'error') and response.error:
                return {"error": response.error.message, "success": False}
            else:
                task = response.result
                return {
                    "task": task,
                    "state": task.get("state", "unknown"),
                    "success": True
                }

        except Exception as e:
            return {"error": str(e), "success": False}

    async def wait_for_task_completion(self, task_id: str, max_wait: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Wait for a task to complete and return the result."""
        for attempt in range(max_wait):
            result = await self.get_task_result(task_id)

            if not result["success"]:
                return result

            state = result["state"]
            if state in ["completed", "failed", "cancelled"]:
                return result

            await asyncio.sleep(1)

        return {"error": "Task timeout", "success": False}

    async def send_and_wait(self, text: str, max_wait: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Send a task and wait for completion."""
        # Send the task
        send_result = await self.send_task(text)
        if not send_result["success"]:
            return send_result

        # Wait for completion
        task_id = send_result["task_id"]
        return await self.wait_for_task_completion(task_id, max_wait)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


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


async def run_test_scenario(client: AuthenticatedA2AClient, test_name: str, tests: list):
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


async def interactive_mode(client: AuthenticatedA2AClient):
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
    parser = argparse.ArgumentParser(description="FastA2A Test Client with Authentication")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help=f"Server URL (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("--auth-token", help="Bearer token for authentication")
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
    client = AuthenticatedA2AClient(args.server, auth_token=auth_token, use_auth=use_auth)

    print(f"🔗 Connecting to FastA2A agent at: {args.server}")

    try:
        # Get agent info
        agent_info = await client.get_agent_info()
        if "error" in agent_info:
            print(f"❌ {agent_info['error']}")
            print("Make sure the test server is running with: python test_server_auth.py")
            return

        if args.info:
            print("\n📋 Agent Information:")
            print(json.dumps(agent_info, indent=2))
            return

        print(f"✅ Connected to: {agent_info.get('name', 'Unknown Agent')}")
        print(f"📖 Description: {agent_info.get('description', 'No description')}")
        print(f"🛠️  Skills: {len(agent_info.get('skills', []))}")

        # Show authentication info if present
        auth_info = agent_info.get('authentication')
        if auth_info:
            print(f"🔐 Authentication: {', '.join(auth_info.get('schemes', []))}")

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

    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
