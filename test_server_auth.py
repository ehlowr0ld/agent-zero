#!/usr/bin/env python3
"""
FastA2A Test Server with Authentication

This server demonstrates FastA2A agent capabilities with Bearer token authentication.
It supports both basic computational tasks and LLM-powered interactions.
"""

import asyncio
import argparse
import json
from typing import Dict, Any

try:
    import uvicorn
except ImportError:
    print("Warning: uvicorn not available. Install with: pip install uvicorn")
    uvicorn = None

from fasta2a import FastA2A, Skill
from fasta2a.broker import InMemoryBroker
from fasta2a.storage import InMemoryStorage

# Import our authentication utilities
from test_auth_setup import SimpleAuthManager, get_auth_token, print_auth_info

# Import workers
from test_worker_basic import BasicTestWorker
from test_worker_llm import LLMTestWorker, can_use_llm_worker

# Configuration constants
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_WORKERS = 2


class AuthenticatedBroker(InMemoryBroker):
    """Enhanced broker with authentication support."""

    def __init__(self, auth_manager: SimpleAuthManager | None = None):
        super().__init__()
        self.auth_manager = auth_manager
        self.workers = []

    def add_worker(self, worker):
        """Add a worker to the broker."""
        self.workers.append(worker)

    async def authenticate_request(self, request_headers: Dict[str, str]) -> bool:
        """Authenticate a request using the auth manager."""
        if not self.auth_manager or not self.auth_manager.require_auth:
            return True

        auth_header = request_headers.get('Authorization')
        return self.auth_manager.validate_request(auth_header)


def create_agent_skills() -> list[Skill]:
    """Create the skills that define what our agent can do."""

    skills = []

    # Basic computational skills
    basic_skills = [
        Skill(
            name="echo_task",
            description="Echo back any text provided by the user",
            parameters={"text": "string"},
            tags=["basic", "text"]
        ),
        Skill(
            name="math_operations",
            description="Perform basic math operations like addition, subtraction, multiplication, division",
            parameters={"operation": "string", "numbers": "array"},
            tags=["basic", "math", "computation"]
        ),
        Skill(
            name="text_processing",
            description="Process text with operations like uppercase, lowercase, reverse, word count",
            parameters={"text": "string", "operation": "string"},
            tags=["basic", "text", "processing"]
        ),
        Skill(
            name="json_operations",
            description="Parse, validate, and manipulate JSON data",
            parameters={"json_data": "string", "operation": "string"},
            tags=["basic", "json", "data"]
        )
    ]

    skills.extend(basic_skills)

    # Add LLM skills if available
    if can_use_llm_worker():
        llm_skills = [
            Skill(
                name="question_answering",
                description="Answer questions using advanced language model capabilities",
                parameters={"question": "string", "context": "string"},
                tags=["llm", "qa", "knowledge"]
            ),
            Skill(
                name="text_generation",
                description="Generate creative text content like stories, poems, or explanations",
                parameters={"prompt": "string", "style": "string"},
                tags=["llm", "generation", "creative"]
            ),
            Skill(
                name="text_summarization",
                description="Summarize long text content into concise summaries",
                parameters={"text": "string", "length": "string"},
                tags=["llm", "summarization", "analysis"]
            ),
            Skill(
                name="conversation",
                description="Engage in natural conversation and provide helpful responses",
                parameters={"message": "string"},
                tags=["llm", "conversation", "chat"]
            )
        ]

        skills.extend(llm_skills)

    return skills


class AuthenticatedFastA2A(FastA2A):
    """FastA2A application with authentication support."""

    def __init__(self, auth_manager: SimpleAuthManager | None = None, **kwargs):
        self.auth_manager = auth_manager
        super().__init__(**kwargs)

    async def agent_card_endpoint(self, request):
        """Override agent card endpoint to include authentication info."""
        response = await super().agent_card_endpoint(request)

        # Add authentication information to the agent card
        if self.auth_manager and self.auth_manager.require_auth:
            # Parse the existing response
            if hasattr(response, 'body'):
                import json
                card_data = json.loads(response.body.decode())

                # Add authentication schemes
                card_data['authentication'] = {
                    'schemes': ['Bearer'],
                    'description': 'Bearer token authentication required for agent-to-agent communication'
                }

                # Create new response with updated data
                from starlette.responses import JSONResponse
                return JSONResponse(card_data)

        return response

    async def json_rpc_endpoint(self, request):
        """Override JSON-RPC endpoint to add authentication."""
        if self.auth_manager and self.auth_manager.require_auth:
            auth_header = request.headers.get('Authorization')

            if not self.auth_manager.validate_request(auth_header):
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content=self.auth_manager.get_error_response()
                )

        return await super().json_rpc_endpoint(request)


def create_fastA2A_app(host=DEFAULT_HOST, port=DEFAULT_PORT, require_auth=True):
    """Create and configure the FastA2A application with authentication."""

    # Set up authentication
    auth_manager = SimpleAuthManager(require_auth=require_auth) if require_auth else None

    # Create storage and broker
    storage = InMemoryStorage()
    broker = AuthenticatedBroker(auth_manager)

    # Create workers
    basic_worker = BasicTestWorker(broker=broker, storage=storage)
    broker.add_worker(basic_worker)

    # Add LLM worker if available
    if can_use_llm_worker():
        try:
            llm_worker = LLMTestWorker(broker=broker, storage=storage)
            broker.add_worker(llm_worker)
            print("✅ LLM worker initialized successfully")
        except Exception as e:
            print(f"⚠️  LLM worker failed to initialize: {e}")
            print("📝 Only basic worker will be available")
    else:
        print("📝 LLM worker not available (no API keys or litellm missing)")
        print("📝 Only basic worker will be available")

    # Get skills
    skills = create_agent_skills()

    # Create FastA2A app with authentication
    app = AuthenticatedFastA2A(
        auth_manager=auth_manager,
        storage=storage,
        broker=broker,
        name="FastA2A Test Agent (Authenticated)",
        url=f"http://{host}:{port}",
        version="1.0.0",
        description="A test agent demonstrating FastA2A capabilities with Bearer token authentication",
        provider={
            "organization": "Test Organization",
            "url": "https://example.com"
        },
        skills=skills
    )

    # Print authentication status
    if require_auth:
        print("🔐 Authentication: ENABLED")
        print_auth_info()
    else:
        print("🔓 Authentication: DISABLED")

    return app


async def run_workers(app):
    """Start all workers."""
    broker = app.broker

    if hasattr(broker, 'workers'):
        for worker in broker.workers:
            print(f"🚀 Starting worker: {worker.__class__.__name__}")

    # Start worker tasks
    tasks = []
    if hasattr(broker, 'workers'):
        for worker in broker.workers:
            task = asyncio.create_task(worker.run().__aenter__())
            tasks.append(task)

    return tasks


def main():
    """Main function to run the FastA2A test server."""
    parser = argparse.ArgumentParser(description="FastA2A Test Server with Authentication")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Number of workers (default: {DEFAULT_WORKERS})")
    parser.add_argument("--auth-token", help="Custom authentication token (overrides environment variable)")

    args = parser.parse_args()

    # Set custom auth token if provided
    if args.auth_token:
        from test_auth_setup import set_auth_token
        set_auth_token(args.auth_token)

    print("🚀 FastA2A Test Server with Authentication")
    print("=" * 50)

    # Create the FastA2A application
    require_auth = not args.no_auth
    app = create_fastA2A_app(args.host, args.port, require_auth)

    print(f"🌐 Server URL: http://{args.host}:{args.port}")
    print(f"📋 Agent card: http://{args.host}:{args.port}/.well-known/agent.json")

    if uvicorn is None:
        print("❌ uvicorn not available. Install with: pip install uvicorn")
        return

    # Start the server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
