# Security Contract

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Contract Type**: Security and Authentication Contract

## Purpose

This contract defines the security mechanisms, authentication requirements, and threat mitigations for the WebSocket infrastructure. It ensures secure communication while maintaining single-user application simplicity and mirroring existing REST API security patterns.

---

## Security Model Overview

### Core Principle

**Single-User Application**: No multi-tenancy, no per-resource authorization, no role-based access control. Security model is **binary authentication**: user is either logged in (full access) or not logged in (no access).

### Security Layers

1. **Connection-Time Authentication**: Flask session validation at WebSocket connection establishment
2. **Connection-Time CSRF Protection**: Optional CSRF token validation per handler configuration
3. **Transport Security**: HTTPS/WSS for production deployments (deployment configuration)
4. **Input Validation**: Application-level data validation in event handlers

---

## Authentication

### Connection-Time Authentication

**Mechanism**: Reuse existing Flask session mechanism

**Flow**:
```
Client                   Server
  │                        │
  │──WebSocket connect──►  │
  │   (session cookie)     │──Check Flask session────►[Flask session store]
  │                        │                                │
  │                        │◄──────authenticated?───────────┘
  │                        │
  │◄──accept/reject───────│
  │                        │
```

**Implementation**:
```python
@sio.event
async def connect(sid, environ, auth):
    """
    Authenticate connection using Flask session.

    Note: Socket.IO allows an 'auth' parameter here, but we don't use it
    because Flask session is automatically available from the session cookie.
    """
    from flask import session

    # Check if handler requires authentication
    if handler_class.requires_auth():
        # Check if authentication is enabled
        if not login.is_auth_enabled():
            return True  # Auth disabled, allow connection

        # Validate Flask session (from session cookie)
        authenticated = session.get("authenticated", False)
        if not authenticated:
            PrintStyle.warning(f"Unauthenticated WebSocket connection attempt")
            return False  # Reject connection

    return True  # Accept connection
```

**Contract**:
- Authentication checked ONCE at connection time
- NO per-event authentication checks (connection already authenticated)
- Uses existing Flask session (no new authentication system)
- Session cookie must be sent by client browser (automatic for same-origin)
- Failed authentication rejects connection immediately

---

### Session Expiration Detection

**Mechanism**: Server-side periodic validation keyed off engine ping/pong or timed checks (avoid app-level custom heartbeat events)

**Pattern**:
```python
@sio.event
async def connect(sid, environ, auth):
    # Normal connection-time auth
    ...

# Infrastructure (timer/task) periodically validates session state
async def _validate_sessions_periodically():
    while True:
        # iterate active sids; if session expired, disconnect
        # implementation detail depends on manager/registry
        await asyncio.sleep(30)
```

**Contract**:
- Server MAY validate session liveness periodically without requiring a custom app event
- Client reconnection triggers new authentication check
- Expired session → graceful disconnection
- No automatic session refresh (client must re-login via HTTP)

---

## CSRF Protection

### Connection-Time CSRF Validation

**Mechanism**: Reuse existing CSRF token infrastructure

**Token Source**:
- CSRF token retrieved from endpoint: `GET /csrf_token`
- Token stored in cookie: `csrf_token_{runtime.id}`
- Token sent in header: `X-CSRF-Token`

**Flow (Preflight)**:
```
Client                          Server
  │                               │
  │──GET /csrf_token────────────► │
  │                               │──Generate token──────►[Set cookie]
  │◄──{token}────────────────────│
  │                               │
  │──POST /csrf_token───────────► │  (X-CSRF-Token header)
  │                               │──Validate header==cookie; set short-lived session flag (for WS connect)
  │◄──{ok:true}──────────────────│
  │                               │
  │──WebSocket connect──────────► │
  │                               │──Check session flag; accept/reject
  │◄──accept/reject──────────────│
  │                               │
```

**Implementation (Preflight)**:
```python
@webapp.route('/csrf_token', methods=['POST'])
async def csrf_token_validate_for_ws():
    # Validate header vs cookie as in ApiHandler
    # On success set session['ws_csrf_ok']=now() (short TTL) and return ok

@sio.event
async def connect(sid, environ, auth):
    # If handler requires CSRF, check session['ws_csrf_ok'] is recent
    # Accept or reject accordingly (no custom headers on handshake)
```

**Contract**:
- CSRF checked ONCE via POST /csrf_token preflight + session flag then connect
- NO per-event CSRF checks (connection already validated)
- Handler declares CSRF requirement via `requires_csrf()` class method
- Default: CSRF required if authentication required
- Failed validation rejects connection immediately

---

### CSRF Token Refresh (TTL 120s)

**Mechanism**: Client retrieves fresh token before reconnection and proactively POSTs `/csrf_token` on `reconnect_attempt` to refresh the short‑lived WS flag (TTL 120 seconds). This TTL remains unchanged by the symmetry enhancements; no additional per‑event CSRF checks are introduced.

**Pattern**:
```javascript
async function connect() {
    // Get fresh CSRF token
    const response = await fetch('/csrf_token');
    const { token } = await response.json();

    // Validate preflight and then connect (WS handshake checks 120s flag)
    websocket.connect();
}
```

**Contract**:
- CSRF token retrieved from existing `/csrf_token` endpoint
- Token automatically included in WebSocket connection headers
- No new CSRF infrastructure needed

---

## Handler Security Configuration

### Declarative Security (Class Methods)

**Pattern** (mirrors ApiHandler):
```python
class MyWebSocketHandler(WebSocketHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        """Require authentication (default: True)"""
        return True

    @classmethod
    def requires_csrf(cls) -> bool:
        """Require CSRF validation (default: same as requires_auth())"""
        return cls.requires_auth()
```

**Security Levels**:

| Configuration | Authentication | CSRF | Use Case |
|--------------|----------------|------|----------|
| `requires_auth=True, requires_csrf=True` | ✅ Required | ✅ Required | Default: authenticated user operations |
| `requires_auth=True, requires_csrf=False` | ✅ Required | ❌ Not required | Read-only authenticated operations (rare) |
| `requires_auth=False, requires_csrf=False` | ❌ Not required | ❌ Not required | Public endpoints (rare for Agent Zero) |
| `requires_auth=False, requires_csrf=True` | ❌ Not required | ✅ Required | Invalid configuration (CSRF requires auth) |

**Default Behavior**:
- **`requires_auth()` default**: `True` (authentication required)
- **`requires_csrf()` default**: `cls.requires_auth()` (CSRF if auth required)

---

## Input Validation

### Handler-Level Validation

**Responsibility**: Each handler MUST validate event data

**Pattern**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    # Validate required fields
    if "message" not in data:
        return {"error": "Missing required field: message"}

    # Validate data types
    if not isinstance(data["message"], str):
        return {"error": "Field 'message' must be a string"}

    # Validate value constraints
    if len(data["message"]) > 1000:
        return {"error": "Message too long (max 1000 characters)"}

    # Process valid event
    ...
```

**Contract**:
- Handlers MUST validate all input data
- Handlers SHOULD return explicit error responses for validation failures
- Handlers MUST NOT trust client-provided data
- Handlers SHOULD use type hints for documentation

---

### JSON Schema Validation (Optional)

**Pattern** (recommended for complex data):
```python
from jsonschema import validate, ValidationError

NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "maxLength": 1000},
        "level": {"type": "string", "enum": ["info", "warning", "error"]},
    },
    "required": ["message", "level"]
}

async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    try:
        validate(instance=data, schema=NOTIFICATION_SCHEMA)
    except ValidationError as e:
        return {"error": "Validation failed", "details": str(e)}

    # Process valid event
    ...
```

---

## Transport Security

### HTTPS/WSS

**Production Requirement**: WebSocket connections MUST use WSS (WebSocket Secure) in production

**Configuration**:
- Development: `ws://localhost:5000` (HTTP/WS acceptable)
- Production: `wss://domain.com` (HTTPS/WSS required)

**Deployment**:
- Reverse proxy (nginx, Apache) handles HTTPS termination
- Flask-SocketIO behind reverse proxy uses WSS automatically

**Contract**:
- Production deployments MUST use HTTPS/WSS
- Development MAY use HTTP/WS for local testing
- Mixed content (HTTPS page + WS connection) blocked by browsers

---

## Threat Mitigation

### 1. Unauthorized Access

**Threat**: Unauthenticated users accessing WebSocket features

**Mitigation**:
- Connection-time authentication (Flask session)
- Failed authentication rejects connection
- No event processing for unauthenticated connections

**Test**:
```python
# Attempt connection without authentication
response = socketio_client.connect('http://localhost:5000', auth={})
assert response is False  # Connection rejected
```

---

### 2. Cross-Site WebSocket Hijacking (CSWSH)

**Threat**: Malicious site establishing WebSocket connection using victim's session

**Mitigation**:
- CSRF token validation at connection time
- Token in header + cookie (not just cookie)
- SameSite=Strict cookie attribute

**Test**:
```python
# Attempt connection without CSRF token
response = socketio_client.connect(
    'http://localhost:5000',
    headers={}  # No X-CSRF-Token header
)
assert response is False  # Connection rejected
```

---

### 3. Session Hijacking

**Threat**: Attacker stealing session cookie to impersonate user

**Mitigation**:
- HTTPS/WSS in production (encrypted transport)
- HttpOnly session cookies (not accessible via JavaScript)
- Secure cookie attribute (HTTPS only)
- Session cookie bound to runtime ID (prevents cross-instance reuse)

**Configuration** (existing Flask session):
```python
webapp.config.update(
    SESSION_COOKIE_NAME="session_" + runtime.get_runtime_id(),
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True  # Production only
)
```

---

### 4. Injection Attacks

**Threat**: Malicious event data executing unintended operations

**Mitigation**:
- Input validation in handlers (required fields, types, constraints)
- JSON serialization prevents code injection
- No eval() or exec() on event data
- PrintStyle logging sanitizes output

**Pattern**:
```python
# ❌ BAD: Direct string formatting
query = f"SELECT * FROM users WHERE id = {data['user_id']}"  # SQL injection risk

# ✅ GOOD: Parameterized queries
query = "SELECT * FROM users WHERE id = ?"
result = db.execute(query, (data['user_id'],))
```

---

### 5. Denial of Service (DoS)

**Threat**: Malicious client flooding server with events

**Mitigation**:
- **Single-user scope**: No per-connection rate limiting needed (authenticated user trusts self)
- **Event buffering**: Limited to 100 events per client (prevents memory exhaustion)
- **Message size**: Socket.IO protocol handles large messages (no hard limit at app level)
- **Connection limit**: No artificial limit (single user, multiple tabs expected)

**Not Implemented** (inappropriate for single-user app):
- ❌ Per-connection rate limiting (single user)
- ❌ Per-event authorization (connection already authenticated)
- ❌ Resource quotas (no multi-tenancy)

---

### 6. Cross-Site Scripting (XSS)

**Threat**: Malicious event data executing JavaScript in client

**Mitigation**:
- Alpine.js automatic escaping: `x-text` directive escapes HTML
- Avoid `x-html` or `innerHTML` with untrusted data
- Content Security Policy (CSP) in production

**Safe Pattern**:
```html
<!-- ✅ SAFE: Alpine.js escapes HTML -->
<div x-text="notificationMessage"></div>

<!-- ❌ UNSAFE: Direct HTML injection -->
<div x-html="notificationMessage"></div>
```

---

## Security Best Practices

### Handler Development

1. **Always validate input**: Never trust client-provided data
2. **Use type hints**: Document expected data structure
3. **Return explicit errors**: Help clients understand validation failures
4. **Log security events**: Use `PrintStyle.warning()` for failed auth attempts
5. **No secrets in events**: Never send credentials or tokens in event data

### Frontend Development

1. **Use Alpine.js escaping**: Prefer `x-text` over `x-html`
2. **Validate responses**: Check server response structure before using
3. **Handle errors gracefully**: Display user-friendly messages for failures
4. **No credentials in data**: Never send passwords or API keys in event payloads
5. **CSRF token automatic**: Use provided `websocket.connect()` (handles CSRF)

### Deployment

1. **HTTPS/WSS required**: Never deploy production with HTTP/WS
2. **Secure cookies**: Enable `SESSION_COOKIE_SECURE=True` in production
3. **Strong secrets**: Use cryptographically random `FLASK_SECRET_KEY`
4. **Reverse proxy**: Use nginx/Apache for SSL termination
5. **Monitor logs**: Watch for authentication failures and CSRF violations

---

## Security Testing

### Authentication Tests

```python
@pytest.mark.asyncio
async def test_connection_requires_authentication():
    """Unauthenticated connection rejected"""
    client = socketio_client.Client()

    # Attempt connection without session
    response = client.connect('http://localhost:5000')

    assert response is False
    assert client.connected is False
```

### CSRF Tests

```python
@pytest.mark.asyncio
async def test_connection_requires_csrf_token():
    """Connection without CSRF token rejected"""
    client = socketio_client.Client()

    # Attempt connection without CSRF header
    response = client.connect(
        'http://localhost:5000',
        headers={}  # No X-CSRF-Token
    )

    assert response is False
```

### Input Validation Tests

```python
@pytest.mark.asyncio
async def test_handler_validates_input():
    """Handler rejects invalid input data"""
    handler = NotificationHandler(mock_socketio, mock_lock)

    # Missing required field
    response = await handler.process_event('notification', {}, 'test-sid')

    assert 'error' in response
    assert 'message' in response['error'].lower()
```

---

## Compliance and Auditing

### Logging

**Security Events Logged** (via PrintStyle):
- Authentication failures (connection rejected)
- CSRF validation failures
- Session expiration disconnections
- Event processing errors
- Invalid event types

**Log Format**:
```python
PrintStyle.warning(f"WebSocket authentication failed: {reason}")
PrintStyle.error(f"WebSocket CSRF validation failed for connection {sid}")
PrintStyle.info(f"WebSocket connection established: {sid}")
PrintStyle.debug(f"Event routed: {event_type} to {handler_class.__name__}")
```

**Contract**:
- All security events logged via PrintStyle
- NO separate security event database (single-user app)
- Logs written to standard application log
- No persistent audit trail (not required for single-user)

---

### No Enterprise Security Theater

**Following Constitution Principle XIII (Project Scope & Simplicity)**:

**❌ NOT Implemented** (inappropriate for single-user app):
- Per-event authentication (connection already authenticated)
- Per-event authorization (no resource-level permissions)
- Rate limiting per connection (single user trusts self)
- Security event database (use application log)
- Audit trail persistence (temporary logs sufficient)
- User roles and permissions (no multi-user access levels)
- Elevated privileges (single user has full access)
- Compliance frameworks (GDPR, SOC2, etc.)

**✅ Implemented** (appropriate for single-user app):
- Connection-time authentication (binary: logged in or not)
- Connection-time CSRF validation (prevent cross-site attacks)
- Input validation (prevent malformed data)
- Transport security (HTTPS/WSS in production)
- General application logging (PrintStyle to application log)

---

## Summary

**Authentication**: Flask session at connection time only (no per-event)
**CSRF**: Token validation at connection time only (no per-event)
**Transport**: HTTPS/WSS required in production
**Input Validation**: Handler-level validation required
**Threat Mitigation**: Unauthorized access, CSWSH, session hijacking, injection, XSS
**Logging**: PrintStyle for all security events (no separate security database)
**Scope**: Single-user application (no multi-tenancy, no per-resource authorization)

**Security Philosophy**: Secure foundation without enterprise-grade over-engineering. Binary authentication model appropriate for single-user scope.

---

**All Contracts Complete**:
- [WebSocket Handler Interface](./websocket-handler-interface.md)
- [Event Schemas](./event-schemas.md)
- [Frontend API](./frontend-api.md)
- [Security Contract](./security-contract.md) ← This document
