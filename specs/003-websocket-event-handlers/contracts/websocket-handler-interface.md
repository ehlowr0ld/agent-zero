# WebSocket Handler Interface Contract

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Contract Type**: Backend API Contract

## Purpose

This contract defines the interface that all WebSocket event handlers must implement. It mirrors the ApiHandler pattern to ensure consistency, developer familiarity, and seamless integration with the existing Agent Zero architecture.

---

## Base Class: `WebSocketHandler`

**Location**: `python/helpers/websocket.py`

**Constructor**:
```python
def __init__(self, socketio: SocketIO, lock: threading.RLock):
    """
    Initialize handler with python-socketio.AsyncServer instance and threading lock.

    Args:
        socketio: python-socketio AsyncServer for emitting events
        lock: Thread synchronization reentrant lock (shared with ApiHandler)
    """
    self.socketio = socketio
    self.lock = lock
```

---

## Required Class Methods (Declarative Configuration)

### 1. `get_event_types()`

**Signature**:
```python
@classmethod
@abstractmethod
def get_event_types(cls) -> list[str]:
    """
    Declare event types this handler subscribes to.

    Returns:
        list[str]: Non-empty list of event type identifiers

    Example:
        return ["notification", "data_update", "user_action"]
    """
```

**Contract**:
- MUST return non-empty list
- MUST return unique event types (no duplicates within handler)
- Event types MUST NOT conflict with reserved Socket.IO events (`connect`, `disconnect`, `error`, `ping`, `pong`)
- Event types MUST match pattern: `^[a-z][a-z0-9_]*$`
- Event types MUST be 1-50 characters long
- Event types MAY be registered by multiple handlers (multi‑handler support)

**Behavior**:
- Called once during handler registration at server startup
- Event types registered with WebSocketManager for routing; an event type maps to a list of handlers, invoked concurrently with aggregation for request‑response

---

### 2. `requires_auth()`

**Signature**:
```python
@classmethod
def requires_auth(cls) -> bool:
    """
    Declare if connection requires authentication.

    Returns:
        bool: True if authentication required (default), False otherwise
    """
    return True  # Default implementation
```

**Contract**:
- MUST return boolean
- Default: `True` (authentication required)
- Checked at connection time only (not per-event)
- Authentication uses existing Flask session mechanism

**Behavior**:
- Called during connection handshake (`@socketio.on('connect')`)
- If `True` and user not authenticated → connection rejected
- If `False` → connection accepted without authentication
- Mirrors ApiHandler `requires_auth()` pattern exactly

---

### 3. `requires_csrf()`

**Signature**:
```python
@classmethod
def requires_csrf(cls) -> bool:
    """
    Declare if connection requires CSRF validation.

    Returns:
        bool: True if CSRF required (default: same as requires_auth()), False otherwise
    """
    return cls.requires_auth()  # Default implementation
```

**Contract**:
- MUST return boolean
- Default: Same as `requires_auth()`
- Checked at connection time only (not per-event)
- CSRF validation uses existing `X-CSRF-Token` header and cookie mechanism

**Behavior**:
- Called during connection handshake
- If `True` → validates CSRF token from header against cookie
- If validation fails → connection rejected
- Mirrors ApiHandler `requires_csrf()` pattern exactly

---

## Required Instance Methods (Handler Logic)

### 1. `process_event()`

**Signature**:
```python
@abstractmethod
async def process_event(
    self,
    event_type: str,
    data: dict,
    sid: str
) -> dict | None:
    """
    Process incoming event from client.

    Args:
        event_type: Event type identifier (one of get_event_types())
        data: Event payload from client (JSON-deserialized dict)
        sid: Socket.IO session ID of sender

    Returns:
        dict: Response data (for request-response pattern)
        None: No response (for fire-and-forget pattern)

    Raises:
        Any exception is caught by WebSocketManager and logged
    """
```

**Contract**:
- MUST be async function (`async def`)
- MUST accept three parameters: `event_type`, `data`, `sid`
- MUST return dict (response) or None (no response)
- MUST handle exceptions gracefully (caller catches and logs)
- MUST NOT block event loop (use async operations only)
- MAY access `self.lock` for thread synchronization
- MAY access `self.log` for logging (PrintStyle)
- MAY call `emit_to()` or `broadcast()` to send events to clients

**Behavior**:
- Called by WebSocketManager when event of subscribed type received
- Runs in async context (can use `await`)
- Return value sent back to client if request-response pattern
- Return `None` for fire-and-forget events (no acknowledgment)
- Exceptions logged and generic error returned to client

**Example**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    from python.helpers.print_style import PrintStyle

    PrintStyle.info(f"Processing {event_type} from {sid}")

    if event_type == "notification":
        # Fire-and-forget: no return value
        await self.handle_notification(data)
        return None

    elif event_type == "query_data":
        # Request-response: return data
        result = await self.fetch_data(data["query"])
        return {"data": result, "status": "success"}
```

---

### 2. `on_connect()` (Optional Override)

**Signature**:
```python
async def on_connect(self, sid: str):
    """
    Called when client connects successfully.

    Args:
        sid: Socket.IO session ID of new connection
    """
```

**Contract**:
- MUST be async function if overridden
- Default implementation: empty (no-op)
- Called AFTER authentication and CSRF validation succeed
- MAY perform handler-specific initialization
- MAY emit welcome events to client
- MAY access Flask session for user context
- MUST NOT block event loop

**Behavior**:
- Called once per connection after handshake succeeds
- Optional lifecycle hook for handler-specific setup
- Exceptions logged but do not reject connection
- If handler needs user info, access Flask session directly

---

### 3. `on_disconnect()` (Optional Override)

**Signature**:
```python
async def on_disconnect(self, sid: str):
    """
    Called when client disconnects.

    Args:
        sid: Socket.IO session ID of disconnected client
    """
```

**Contract**:
- MUST be async function if overridden
- Default implementation: empty (no-op)
- Called when connection lost (graceful or abrupt)
- MAY perform handler-specific cleanup
- MUST NOT block event loop
- MUST NOT attempt to send events to disconnected client

**Behavior**:
- Called once per disconnection
- Optional lifecycle hook for handler-specific cleanup
- Exceptions logged but do not affect disconnection

---

## Provided Instance Methods (Base Class)

### 1. `emit_to()`

**Signature**:
```python
def emit_to(self, sid: str, event_type: str, data: dict):
    """
    Send fire-and-forget event to specific connection.

    Args:
        sid: Socket.IO session ID of target connection
        event_type: Event type identifier
        data: Event payload (JSON-serializable dict)
    """
```

**Contract**:
- Sends event to single connection
- Fire-and-forget pattern (no acknowledgment)
- If connection active → event delivered immediately
- If connection inactive → event buffered (up to 100 events)
- Always wraps delivery with envelope `{ handlerId, eventId, correlationId, ts, data }` where `eventId` is UUIDv4 and `ts` is ISO8601 UTC with milliseconds. `correlationId` is reused when supplied or generated automatically when omitted.
- No return value
- Thread-safe

---

### 2. `broadcast()`

**Signature**:
```python
def broadcast(
    self,
    event_type: str,
    data: dict,
    exclude_sids: str | Iterable[str] | None = None,
    *,
    correlation_id: str | None = None,
):
    """
    Send fire-and-forget event to all connections.

    Args:
        event_type: Event type identifier
        data: Event payload (JSON-serializable dict)
        exclude_sids: Optional connection ID or collection of IDs to exclude
    """
```

**Contract**:
- Sends event to all active connections
- Fire-and-forget pattern (no acknowledgment)
- If connection active → event delivered immediately
- If connection inactive → event buffered (up to 100 events per client)
- Optional exclusion of one or more connections (`exclude_sids` only; no include list)
- Always wraps delivery with envelope `{ handlerId, eventId, correlationId, ts, data }`
- No return value
- Thread-safe

---

### 3. `request()` (helper – single sid)

**Signature**:
```python
async def request(
    self,
    sid: str,
    event_type: str,
    data: dict,
    *,
    timeout_ms: int = 0,
    include_handlers: Iterable[str] | None = None,
) -> dict[str, Any]:
    """
    Fan-out to all handlers for event_type, deliver to a single target sid, and
    return payload `{ "correlationId": str, "results": [{ handlerId, ok, data|error }] }`.
    Timeout in milliseconds, default 0 (unlimited).
    """
```

**Contract**:
- Targets exactly one `sid`
- Aggregates per‑handler results (multi‑handler support) while preserving shared `correlationId`
- Timeout values are expressed in milliseconds. The default `timeout_ms` is `0` (unlimited). Positive values apply per-call timeout semantics; exceeded handlers are converted into standardized timeout errors
- Standardized error objects for handler failures/timeouts

---

### 4. `request_all()` (helper – aggregate across sids)

**Signature**:
```python
async def request_all(
    self,
    event_type: str,
    data: dict,
    *,
    timeout_ms: int = 0,
    exclude_handlers: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Fan‑out to all active connections and aggregate per‑sid results.
    Returns: [{ sid: str, correlationId: str, results: [{ handlerId, ok, data|error }] }].
    Include each targeted sid even when no handlers match or connection errors occur, using standardized error entries.
    Timeout in milliseconds, default 0 (unlimited).
    """
```

**Contract**:
- Returns per‑sid arrays of per‑handler results bundled with a `correlationId`
- Always includes each targeted sid with standardized error object if no handlers or connection errors
- Timeout values are expressed in milliseconds. The default `timeout_ms` is `0` (unlimited) with identical semantics to the single-sid helper.

---

### 5. Result Builder Utilities (Developer Ergonomics)

Handlers MUST NOT hand-craft `RequestResultItem` dictionaries. Instead expose convenience builders that return objects recognised by the manager.

**Interface**:
```python
class WebSocketResult:
    @classmethod
    def ok(cls, data: dict[str, Any] | None = None, *, correlation_id: str | None = None,
           duration_ms: float | None = None) -> "WebSocketResult": ...

    @classmethod
    def error(
        cls,
        *,
        code: str,
        message: str,
        details: str | None = None,
        correlation_id: str | None = None,
    ) -> "WebSocketResult": ...
```

**Contract**:
- `WebSocketHandler.process_event` MAY return either a raw `dict` (fire-and-forget ack) or a `WebSocketResult` instance. Returning a `WebSocketResult` MUST produce the standard `{ handlerId, ok, data|error, correlationId?, durationMs? }` structure.
- Manager MUST detect helper instances and serialise them accordingly; manual dicts remain supported for backward compatibility but new code SHOULD use the helpers.
- Helper constructors MUST validate inputs (non-empty error code/message, dict payloads) and raise descriptive exceptions for invalid usage.
- Duration and correlation metadata are optional but preserved when provided.

---

---

## Handler Discovery and Registration

**Discovery Pattern**:
```python
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.websocket import WebSocketHandler

# Auto-discover handlers
handlers = load_classes_from_folder(
    "python/websocket_handlers",
    "*.py",
    WebSocketHandler
)
```

- Filters declared by clients are enforced centrally by the manager: `includeHandlers` lists are honored for inbound `emit`/`request`, `excludeHandlers` lists for inbound `request_all`, and server broadcasts only accept `exclude_sids`. Any other filter shape is rejected at routing time to preserve symmetry with the frontend contract.
- Handlers MUST be placed in `python/websocket_handlers/` directory
- Handlers MUST inherit from `WebSocketHandler`
- Handlers MUST implement all abstract methods
- Handlers MAY share event types with other handlers (multi‑handler). Registration order determines default ordering; actual execution is concurrent with result aggregation for request‑response
- Handler filename influences registration order only (for deterministic ordering in aggregated results)

**Registration Process**:
1. Server startup scans `python/websocket_handlers/` directory
2. Each file loaded as Python module
3. Classes inheriting from `WebSocketHandler` extracted
4. Handler instantiated with `socketio` and `lock`
5. Event types registered with WebSocketManager
6. Lifecycle hooks registered with AsyncServer (`@sio.event` / `.on(...)`)

---

## Example Implementation

**File**: `python/websocket_handlers/notification_handler.py`

```python
from python.helpers.websocket import WebSocketHandler

class NotificationHandler(WebSocketHandler):
    """Handler for notification events"""

    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["notification", "alert"]

    @classmethod
    def requires_auth(cls) -> bool:
        return True  # Require authentication

    @classmethod
    def requires_csrf(cls) -> bool:
        return True  # Require CSRF validation

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Processing {event_type} from {sid}")

        if event_type == "notification":
            # Fire-and-forget: broadcast to all except sender
            self.broadcast("notification_broadcast", {
                "message": data.get("message", ""),
                "level": data.get("level", "info")
            }, exclude_sids=sid)
            return None  # No response for fire-and-forget

        elif event_type == "alert":
            # Request-response: acknowledge receipt
            PrintStyle.warning(f"Alert received: {data}")
            return {"status": "acknowledged", "timestamp": datetime.now().isoformat()}

    async def on_connect(self, sid: str):
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Notification handler: Client {sid} connected")

        # Optional: Access Flask session for user context
        from flask import session
        user_id = session.get("user_id", "unknown")

        # Send welcome notification
        self.emit_to(sid, "notification_broadcast", {
            "message": "Connected to notification service",
            "level": "info"
        })

    async def on_disconnect(self, sid: str):
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Notification handler: Client {sid} disconnected")
```

---

## Error Handling Contract

**Handler Exceptions**:
- All exceptions in `process_event()` caught by WebSocketManager
- Logged via PrintStyle.error()
- Generic error response sent to client: `{"error": "Internal server error"}`
- Connection remains active (exception does not disconnect)

**Invalid Event Type**:
- If handler receives event type not in `get_event_types()`: Should not happen (routing error)
- If no handler registered for event type: Error response sent by WebSocketManager

**Malformed Data**:
- Handler SHOULD validate `data` parameter
- Handler SHOULD return explicit error response: `{"error": "Validation failed", "details": ...}`
- Handler MAY raise exception (caught and logged)

---

## Thread Safety Contract

**Lock Usage**:
- Handler has access to `self.lock` (shared with ApiHandler)
- SHOULD use a reentrant lock for shared state modifications
- SHOULD NOT hold lock during async operations (blocks other requests)

**Pattern**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    # Acquire lock for critical section
    with self.lock:
        # Modify shared state (no async operations here)
        shared_state.update(data)

    # Release lock before async operations
    result = await external_api_call()

    return {"result": result}
```

---

## Testing Contract

**Unit Test Requirements**:
- Handler MUST be testable in isolation
- Handler MUST accept mock `socketio` and `lock` in constructor
- Handler MUST NOT require actual WebSocket connection for unit tests

**Test Template**:
```python
import pytest
from unittest.mock import Mock, AsyncMock
import threading

@pytest.mark.asyncio
async def test_handler_process_event():
    # Arrange
    mock_socketio = Mock()
    mock_lock = threading.Lock()
    handler = MyHandler(mock_socketio, mock_lock)

    # Act
    response = await handler.process_event("test_event", {"key": "value"}, "test-sid")

    # Assert
    assert response == {"status": "success"}
```

---

## Summary

**Contract Guarantees**:
- All handlers inherit from `WebSocketHandler`
- All handlers implement `get_event_types()` and `process_event()`
- Authentication and CSRF checked at connection time only
- Event routing managed by WebSocketManager
- Thread-safe operations with provided lock
- PrintStyle logging for all messages
- Automatic discovery and registration at server startup

**Developer Responsibilities**:
- Implement abstract methods
- Handle exceptions gracefully
- Validate input data
- Use async operations (no blocking)
- Use `PrintStyle` static methods for logging (`PrintStyle.info()`, `PrintStyle.error()`, etc.)
- Return dict for request-response, None for fire-and-forget

**Next Contract**: [Event Schemas](./event-schemas.md)
