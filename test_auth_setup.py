"""
Authentication Setup for FastA2A Testing

This module provides utilities for setting up and managing authentication
for FastA2A agent-to-agent communication using Bearer tokens.
"""

import os
from typing import Dict, Any

# Default authentication configuration
DEFAULT_AUTH_TOKEN = "test-agent-token-123"
AUTH_TOKEN_ENV_VAR = "FASTA2A_AUTH_TOKEN"


def get_auth_token() -> str:
    """Get the authentication token from environment or use default."""
    return os.getenv(AUTH_TOKEN_ENV_VAR, DEFAULT_AUTH_TOKEN)


def set_auth_token(token: str) -> None:
    """Set the authentication token in environment."""
    os.environ[AUTH_TOKEN_ENV_VAR] = token


def create_auth_headers(token: str | None = None) -> Dict[str, str]:
    """Create HTTP headers with Bearer token authentication."""
    if token is None:
        token = get_auth_token()

    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def validate_bearer_token(auth_header: str | None, expected_token: str | None = None) -> bool:
    """Validate a Bearer token from Authorization header."""
    if not auth_header:
        return False

    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[7:]  # Remove "Bearer " prefix

    if expected_token is None:
        expected_token = get_auth_token()

    return token == expected_token


def create_auth_error_response(message: str = "Authentication required") -> Dict[str, Any]:
    """Create a standard authentication error response."""
    return {
        "error": "Authentication failed",
        "message": message,
        "required_auth": "Bearer token"
    }


def print_auth_info(token: str | None = None) -> None:
    """Print authentication information for debugging."""
    if token is None:
        token = get_auth_token()

    print("🔐 FastA2A Authentication Configuration:")
    print(f"   Token: {token}")
    print(f"   Environment Variable: {AUTH_TOKEN_ENV_VAR}")
    print(f"   Header Format: Authorization: Bearer {token}")


class SimpleAuthManager:
    """Simple authentication manager for FastA2A testing."""

    def __init__(self, token: str | None = None, require_auth: bool = True):
        self.token = token or get_auth_token()
        self.require_auth = require_auth

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        if self.require_auth:
            return create_auth_headers(self.token)
        else:
            return {'Content-Type': 'application/json'}

    def validate_request(self, auth_header: str | None) -> bool:
        """Validate an incoming request."""
        if not self.require_auth:
            return True

        return validate_bearer_token(auth_header, self.token)

    def get_error_response(self) -> Dict[str, Any]:
        """Get error response for failed authentication."""
        return create_auth_error_response(
            "Bearer token authentication required for agent-to-agent communication"
        )


# Convenience functions for quick setup
def setup_client_auth(token: str | None = None) -> Dict[str, str]:
    """Set up authentication headers for a client."""
    return create_auth_headers(token)


def setup_server_auth(token: str | None = None) -> SimpleAuthManager:
    """Set up authentication manager for a server."""
    return SimpleAuthManager(token, require_auth=True)


if __name__ == "__main__":
    # Demo the authentication setup
    print("FastA2A Authentication Setup Demo")
    print("=" * 40)

    # Show current configuration
    print_auth_info()

    print("\n📝 Example Usage:")
    print("Client headers:", create_auth_headers())
    print("Server validation:", validate_bearer_token(f"Bearer {get_auth_token()}"))

    print("\n🔧 Environment Setup:")
    print(f"export {AUTH_TOKEN_ENV_VAR}=your-custom-token")
    print("python test_client.py --auth-token your-custom-token")
    print("python test_server.py")
