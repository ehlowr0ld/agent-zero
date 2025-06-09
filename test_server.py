"""
FastA2A Test Server

This server demonstrates how to set up a FastA2A agent with both basic and LLM workers.
Run this file to start the test server, then use test_client.py to interact with it.
"""

import asyncio
import argparse
import os
from typing import Dict, Any

try:
    import uvicorn
except ImportError:
    print("Warning: uvicorn not available. Install with: pip install uvicorn")
    uvicorn = None

try:
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
except ImportError:
    print("Warning: starlette middleware not available. Install with: pip install starlette")
    Middleware = None
    BaseHTTPMiddleware = None

from fasta2a import FastA2A, Skill
from fasta2a.broker import InMemoryBroker
from fasta2a.storage import InMemoryStorage

from test_worker_basic import BasicTestWorker
from test_worker_llm import LLMTestWorker, can_use_llm_worker

# Configuration constants
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_WORKERS = 2

# Authentication configuration
DEFAULT_AUTH_TOKEN = "test-agent-token-123"
REQUIRE_AUTH = True  # Set to False to disable authentication


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for Bearer token validation."""

    def __init__(self, app, auth_token: str = DEFAULT_AUTH_TOKEN, require_auth: bool = REQUIRE_AUTH):
        super().__init__(app)
        self.auth_token = auth_token
        self.require_auth = require_auth
        # Get token from environment variable if available
        env_token = os.getenv('FASTA2A_AUTH_TOKEN')
        if env_token:
            self.auth_token = env_token

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for agent card endpoint (public)
        if request.url.path == "/.well-known/agent.json":
            return await call_next(request)

        # Skip authentication if disabled
        if not self.require_auth:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Missing Authorization header",
                    "message": "Bearer token required for agent-to-agent authentication"
                }
            )

        # Validate Bearer token format
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid Authorization format",
                    "message": "Authorization header must use Bearer token format"
                }
            )

        # Extract and validate token
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != self.auth_token:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Invalid token",
                    "message": "Bearer token is invalid or expired"
                }
            )

        # Token is valid, proceed with request
        return await call_next(request)


class MultiWorkerBroker(InMemoryBroker):
    """A broker that can route tasks to different types of workers."""

    def __init__(self):
        super().__init__()
        self.workers = []
        self.running = False

    def add_worker(self, worker):
        """Add a worker to the broker."""
        self.workers.append(worker)

    async def __aenter__(self):
        await super().__aenter__()
        self.running = True

        # Start all workers
        for worker in self.workers:
            await self._start_worker(worker)

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.running = False
        await super().__aexit__(exc_type, exc_value, traceback)

    async def _start_worker(self, worker):
        """Start a worker in the background."""
        async def worker_loop():
            async with worker.run():
                while self.running:
                    await asyncio.sleep(0.1)

        # Start worker task
        asyncio.create_task(worker_loop())


def create_agent_skills():
    """Create the skills that this agent can perform."""
    skills = []

    # Basic computational skills
    skills.append(Skill(
        id="echo",
        name="Echo/Repeat Text",
        description="Repeats or echoes back the provided text",
        tags=["text", "basic", "echo"],
        examples=["echo hello world", "repeat this message"],
        input_modes=["application/json"],
        output_modes=["application/json"]
    ))

    skills.append(Skill(
        id="math",
        name="Basic Mathematics",
        description="Performs basic mathematical operations like addition, subtraction, multiplication, and division",
        tags=["math", "calculation", "arithmetic"],
        examples=["add 5 and 3", "multiply 4 by 7", "divide 20 by 4"],
        input_modes=["application/json"],
        output_modes=["application/json"]
    ))

    skills.append(Skill(
        id="text_processing",
        name="Text Processing",
        description="Processes text with operations like uppercase, lowercase, reverse, and word counting",
        tags=["text", "processing", "formatting"],
        examples=["uppercase hello world", "reverse this text", "count words in this sentence"],
        input_modes=["application/json"],
        output_modes=["application/json"]
    ))

    skills.append(Skill(
        id="json_processing",
        name="JSON Processing",
        description="Parses and formats JSON data",
        tags=["json", "parsing", "formatting"],
        examples=['parse json {"name": "test"}', 'format json data'],
        input_modes=["application/json"],
        output_modes=["application/json"]
    ))

    # LLM skills (if available)
    if can_use_llm_worker():
        skills.append(Skill(
            id="question_answering",
            name="Question Answering",
            description="Answers questions using language model capabilities",
            tags=["llm", "qa", "knowledge"],
            examples=["What is the capital of France?", "Explain quantum computing"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        ))

        skills.append(Skill(
            id="text_generation",
            name="Text Generation",
            description="Generates creative text content based on prompts",
            tags=["llm", "generation", "creative"],
            examples=["Write a short story about robots", "Create a poem about nature"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        ))

        skills.append(Skill(
            id="summarization",
            name="Text Summarization",
            description="Creates concise summaries of longer text content",
            tags=["llm", "summary", "analysis"],
            examples=["Summarize this article", "Create a TLDR for this document"],
            input_modes=["application/json"],
            output_modes=["application/json"]
        ))

    return skills


def create_fastA2A_app(host=DEFAULT_HOST, port=DEFAULT_PORT, auth_token=DEFAULT_AUTH_TOKEN, require_auth=REQUIRE_AUTH):
    """Create and configure the FastA2A application."""

    # Create storage and broker
    storage = InMemoryStorage()
    broker = MultiWorkerBroker()

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

    # Create middleware for authentication
    middleware = []
    if require_auth and BaseHTTPMiddleware is not None:
        auth_middleware = Middleware(
            BearerTokenAuthMiddleware,
            auth_token=auth_token,
            require_auth=require_auth
        )
        middleware.append(auth_middleware)
        print(f"🔐 Authentication enabled with Bearer token")
    elif require_auth:
        print("⚠️  Authentication requested but starlette middleware not available")
        require_auth = False
    else:
        print("🔓 Authentication disabled")

    # Create FastA2A app
    app = FastA2A(
        storage=storage,
        broker=broker,
        name="FastA2A Test Agent",
        url=f"http://{host}:{port}",
        version="1.0.0",
        description="A test agent demonstrating FastA2A capabilities with both basic and LLM workers",
        provider={
            "organization": "Test Organization",
            "url": "https://example.com"
        },
        skills=skills,
        middleware=middleware if middleware else None
    )

    # Update authentication in agent card if auth is enabled
    if require_auth:
        # This will be reflected in the agent card endpoint
        app.auth_schemes = ["Bearer"]
        app.auth_token = auth_token

    return app


async def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Run the FastA2A server."""
    app = create_fastA2A_app(host, port)

    if uvicorn is None:
        raise ImportError("uvicorn is required to run the server. Install with: pip install uvicorn")

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info"
    )

    server = uvicorn.Server(config)

    print(f"🚀 Starting FastA2A test server on {host}:{port}")
    print(f"📋 Agent card available at: http://{host}:{port}/.well-known/agent.json")
    print(f"🔗 Main endpoint at: http://{host}:{port}/")
    print(f"🛠️  Available skills: {len(create_agent_skills())}")

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    finally:
        await server.shutdown()


async def main():
    """Main function to run the server."""
    parser = argparse.ArgumentParser(description="FastA2A Test Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--test-agent-card", action="store_true", help="Test agent card endpoint and exit")

    args = parser.parse_args()

    if args.test_agent_card:
        # Test the agent card creation
        app = create_fastA2A_app(args.host, args.port)

        # Mock request to get agent card
        from unittest.mock import Mock
        mock_request = Mock()

        response = await app._agent_card_endpoint(mock_request)
        print("🧪 Agent Card Test:")
        print(f"📄 Content-Type: {response.media_type}")
        print(f"📝 Content: {response.body.decode()}")
        return

    # Run the server
    await run_server(args.host, args.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
