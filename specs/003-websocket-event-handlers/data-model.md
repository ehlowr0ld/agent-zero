# Data Model: WebSocket Event Handlers

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Phase**: 1 - Data Architecture

## Overview

This document defines the data structures, relationships, and state management patterns for the WebSocket infrastructure. The model follows established Agent Zero patterns while introducing minimal new abstractions for connection tracking, event routing, and message buffering.

---

## Core Entities

### 1. WebSocketConnection

**Purpose**: Represents an active WebSocket connection from a client browser tab

**Attributes**:
```python
@dataclass
class WebSocketConnection:
    sid: str                    # Socket.IO session ID (unique per connection)
    authenticated: bool         # Authentication status (validated at connection time)
    connected_at: datetime      # Timestamp when connection established
    last_activity: datetime     # Timestamp of last event (for timeout detection)
    user_agent: str            # Browser user agent string
    ip_address: str            # Client IP address (for logging/debugging)
```

**Validation Rules**:
- `sid`: Non-empty string, unique per connection
- `authenticated`: Boolean, set during connection handshake
- `connected_at`: Immutable after creation
- `last_activity`: Updated on every incoming/outgoing event
- `user_agent` and `ip_address`: Optional, for logging only

**State Transitions**:
```
[Initial] → connect → [Connected] → disconnect (graceful/abrupt) → [Disconnected]
                          ↓
                     idle timeout / session expired
                          ↓
                    [Disconnected]
```

**Disconnection Types**:
- **Graceful**: User closes tab → flushes buffered events immediately → calls on_disconnect()
- **Abrupt**: Network failure → preserves buffer for reconnection → calls on_disconnect()
- **Session Expired**: Timeout detected → follows graceful flow → calls on_disconnect()

**Relationships**:
- **One connection** → **Many buffered events** (when disconnected)
- **One user session** → **Many connections** (multiple browser tabs)

---

### 2. WebSocketEvent

**Purpose**: Represents a message transmitted over a WebSocket connection

**Attributes**:
```python
@dataclass
class WebSocketEvent:
    event_type: str            # Event type identifier (e.g., "notification", "data_update")
    data: dict                 # Event payload (JSON-serializable)
    sender_sid: str | None     # Source connection ID (None for server-originated events)
    timestamp: datetime        # When event was created
    pattern: EventPattern      # Fire-and-forget or request-response
```

**EventPattern Enum**:
```python
class EventPattern(Enum):
    FIRE_AND_FORGET = "fire_and_forget"  # One-way, no acknowledgment
    REQUEST_RESPONSE = "request_response"  # Two-way, expects response
```

**Validation Rules**:
- `event_type`: Non-empty string, registered with a handler
- `data`: JSON-serializable dict (no binary data)
- `sender_sid`: Valid connection ID or None
- `pattern`: Must be valid EventPattern enum value

**Serialization**:
```python
# Wire format (JSON)
{
    "event_type": "notification",
    "data": {"message": "Hello", "level": "info"},
    "timestamp": "2025-10-16T10:30:00Z"
}
```

**Size Constraints**:
- No hard limit enforced at application level
- Socket.IO protocol handles message size automatically
- Recommendation: Keep messages under 1MB for performance
- Large payloads: Use chunking or references (not implemented in infrastructure)

---

### 3. EventHandler

**Purpose**: Bidirectional server-side component that processes incoming events and sends outgoing events

**Attributes**:
```python
class WebSocketHandler(ABC):
    socketio: socketio.AsyncServer  # python-socketio AsyncServer for sending events
    lock: threading.RLock           # Reentrant lock (shared with ApiHandler)
    log: PrintStyle           # Logging interface (initialized in before_execution())
```

**Singleton Lifecycle**
- Handlers are singletons. Each subclass provides `@classmethod def get_instance(cls) -> "WebSocketHandler"` which lazily creates and caches the instance.
- Calling the subclass constructor directly raises `SingletonInstantiationError(cls.__name__)`. This ensures shared state stays consistent across reconnects and avoids duplicate lifecycle hooks.
- Auto-discovery and manual registration code MUST call `cls.get_instance()` to obtain the handler reference.

**Class Methods** (declarative configuration):
```python
@classmethod
@abstractmethod
def get_event_types(cls) -> list[str]:
    """Event types this handler subscribes to"""

@classmethod
def requires_auth(cls) -> bool:
    """Whether connection requires authentication (default: True)"""
    return True

@classmethod
def requires_csrf(cls) -> bool:
    """Whether connection requires CSRF validation (default: requires_auth())"""
    return cls.requires_auth()
```

**Instance Methods** (handler logic):
```python
@abstractmethod
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    """
    Process incoming event from client.

    Args:
        event_type: The type of event being processed
        data: Event payload from client
        sid: Connection ID of sender

    Returns:
        dict: Response data (for request-response pattern)
        None: No response (for fire-and-forget pattern)
    """

async def on_connect(self, sid: str):
    """
    Called when client connects (optional override).
    Access Flask session if user context needed.
    """

async def on_disconnect(self, sid: str):
    """Called when client disconnects (optional override)"""
```

**Validation Rules**:
- `get_event_types()`: Must return non-empty list of unique event type strings
- `process_event()`: Must be async, must handle exceptions gracefully
- Event types: Must not conflict with reserved Socket.IO events (`connect`, `disconnect`, `error`)

**Lifecycle**:
```
[Registration] → on_connect → [Active] → process_event (many) → on_disconnect → [Inactive]
```

**Sending Events** (instance methods provided by base class):
```python
def emit_to(self, sid: str, event_type: str, data: dict):
    """Send fire-and-forget event to specific connection"""

def broadcast(self, event_type: str, data: dict, exclude_sids: str | Iterable[str] | None = None):
    """Send fire-and-forget event to all connections (optionally excluding selected SIDs)"""
```

**Relationships**:
- **One handler** → **Many event types** (handler subscribes to multiple types)
- **One event type** → **Many handlers** (multi‑handler registration supported)
- **Many handlers** → **One WebSocketManager** (centralized routing)
- **Lifecycle events**: The manager emits standardized reconnect/disconnect events (shared identifiers on frontend/backend) that all handlers can observe. These events use the same envelope schema and fire asynchronously so slow lifecycle handlers cannot block dispatch.

---

### 4. EventSubscription

**Purpose**: Represents a client's registration to receive specific event types from the server

**Attributes** (frontend data structure):
```javascript
class EventSubscription {
    eventType: string           // Event type identifier
    callback: (data) => void    // Callback function to invoke
    component: string | null    // Alpine.js component ID (optional, for cleanup)
}
```

**Frontend Storage**:
```javascript
// Map structure: eventType -> [callbacks]
subscriptions: Map<string, Array<Function>>
```

**Validation Rules**:
- `eventType`: Non-empty string
- `callback`: Valid function reference
- Duplicate subscriptions allowed (multiple callbacks per event type)

**Lifecycle**:
```
subscribe (on) → [Active] → receive events → unsubscribe (off) → [Inactive]
```

**State Transitions**:
- Component initialization → subscribe to events
- Component destruction → unsubscribe from events
- Connection lost → subscriptions persist (reconnect restores)

---

## Supporting Data Structures

### 5. EventBuffer

**Purpose**: Server-side temporary storage for events sent to disconnected clients

**Attributes**:
```python
class EventBuffer:
    buffers: dict[str, deque[BufferedEvent]]  # sid -> circular buffer
    max_size: int = 100                       # Maximum events per client
```

**BufferedEvent**:
```python
@dataclass
class BufferedEvent:
    event_type: str
    data: dict
    timestamp: datetime
```

**Behavior**:
- **Add event**: Append to client's buffer, drop oldest if full (FIFO), check expiration
- **Get events**: Return all buffered events for client, clear buffer
- **Cleanup**: Lazy expiration (1 hour without reconnection), checked on buffer access
- **No Background Task**: Expiration checked during add/get operations, not actively polled

**Validation Rules**:
- Only fire-and-forget events buffered (request-response events fail immediately)
- Buffer per `sid` (connection ID)
- Maximum 100 events per client
- Oldest events dropped on overflow (logged with warning)

**State Transitions**:
```
[Empty] → add_event → [Has Events] → get_buffered_events → [Empty]
           ↑                                   ↓
           └───────── add_event ───────────────┘
```

**Persistence**: In-memory only (no disk persistence)

---

### 6. ConnectionRegistry

**Purpose**: Centralized tracking of all active WebSocket connections

**Attributes**:
```python
class ConnectionRegistry:
    connections: dict[str, WebSocketConnection]  # sid -> connection info
    lock: threading.Lock                         # Thread-safe access
    # Session tracking (single-user default; multi-tenant ready)
    user_to_sids: dict[str, set[str]]            # user identifier -> set of sids
    sid_to_user: dict[str, str]                  # sid -> user identifier
```

**Operations**:
```python
def register(self, connection: WebSocketConnection):
    """Add connection to registry"""

def unregister(self, sid: str):
    """Remove connection from registry"""

def get(self, sid: str) -> WebSocketConnection | None:
    """Retrieve connection by ID"""

def is_connected(self, sid: str) -> bool:
    """Check if connection is active"""

def get_all_sids(self) -> list[str]:
    """Get all active connection IDs"""

def count(self) -> int:
    """Count active connections"""

def get_sids_for_user(self, user: str | None = None) -> list[str]:
    """
    Return all sids for the given user; in the current single-user deployment
    this ignores the user parameter and returns the `allUsers` bucket (all sids).
    """

def get_user_for_sid(self, sid: str) -> str | None:
    """Return user identifier for a sid if tracked, else None"""
```

**Thread Safety**: All operations protected by lock (shared with Flask request handling)

**Usage Notes**:
- The `allUsers` bucket is populated automatically for every authenticated connection. Future multi-tenant support will store additional buckets keyed by user identifier without altering today's callers.
- Helper lookups are used by higher-level helpers (`WebSocketHandler.broadcast`, `request`, `request_all`) to compute target SID lists for fan-out operations while keeping handler implementations oblivious to session wiring.
- **Future Multitenancy Plan**:
  - **Sources of truth**: When multi-user support lands, `register()` will accept a resolved `user_id` from Flask session (or downstream auth provider). Missing identifiers fall back to `allUsers` for backward compatibility.
  - **Helper bodies**: `get_sids_for_user(user_id)` will return a copy of the mapped set when `user_id` is provided; today's behaviour (`allUsers`) becomes the explicit `user_id is None` branch. `get_user_for_sid(sid)` will surface whichever identifier was stored at registration, allowing handlers to rehydrate user context quickly.
  - **Use cases**: Targeting all tabs for a specific account, broadcasting workspace-level notifications, or correlating request responses per tenant. Additional helpers (e.g., `get_users()`, `remove_user(user_id)`) can be layered without breaking callers because the internal map already tracks both directions.
  - **Migration mechanics**: Introduction of multitenant identifiers will not require handler changes. Handlers that currently iterate `get_sids_for_user()` automatically gain tenant scoping once the user argument is passed. Tests will cover single-user (default) and multi-user branches to ensure no regression.

---

### 7. WebSocketManager

**Purpose**: Centralized event routing, buffering, and dispatcher metrics.

**Attributes**:
```python
class WebSocketManager:
    socketio: AsyncServer
    connections: ConnectionRegistry
    handlers: dict[str, list[WebSocketHandler]]
    metrics_enabled: bool = False
```

**Operations**:
```python
def route_event(self, event_type: str, data: dict, sid: str):
    """Route incoming event to appropriate handlers"""

def broadcast(self, event_type: str, data: dict, exclude_sids=None):
    """Broadcast event to all active connections"""

def emit_to(self, sid: str, event_type: str, data: dict):
    """Emit event to specific connection"""

def get_metrics(self) -> dict:
    """
    Return dispatcher latency metrics (if collection enabled via dev settings).
    Returns: {'avg_latency_ms': float, 'p95_latency_ms': float, 'throughput_eps': float} or empty.
    """
```

---

## Relationships and Dependencies

### Entity Relationship Diagram

```
┌─────────────────────┐
│ Flask Session       │ (existing)
│ - authenticated     │
└──────────┬──────────┘
           │ validates
           ↓
┌─────────────────────┐      manages      ┌─────────────────────┐
│ WebSocketManager    │◄─────────────────►│ ConnectionRegistry  │
│ - route_event()     │                   │ - connections{}     │
│ - broadcast()       │                   └─────────────────────┘
└──────────┬──────────┘                              │
           │                                         │ tracks
           │ routes to                               ↓
           ↓                              ┌─────────────────────┐
┌─────────────────────┐                  │ WebSocketConnection │
│ EventHandler        │                  │ - sid               │
│ - process_event()   │                  │ - authenticated     │
│ - emit_to()         │                  └─────────────────────┘
└──────────┬──────────┘                              │
           │                                         │ may have
           │ subscribes to                           ↓
           ↓                              ┌─────────────────────┐
┌─────────────────────┐                  │ EventBuffer         │
│ event_type          │                  │ - buffers{}         │
└─────────────────────┘                  └─────────────────────┘
           │
           │ delivered as
           ↓
┌─────────────────────┐
│ WebSocketEvent      │
│ - event_type        │
│ - data              │
└─────────────────────┘
```

### Key Relationships

1. **Flask Session → WebSocketConnection**: Session validates authentication at connection time
2. **WebSocketManager → EventHandler**: Manager routes events to handlers based on event_type
3. **WebSocketManager → ConnectionRegistry**: Manager tracks all active connections
4. **ConnectionRegistry → WebSocketConnection**: Registry stores connection metadata
5. **WebSocketConnection → EventBuffer**: Disconnected connections have buffered events
6. **EventHandler → event_type**: Handlers subscribe to specific event types (many-to-one)

---

## State Management

### Connection State Machine

```
┌─────────┐
│ Initial │
└────┬────┘
     │ connect (authenticate)
     ↓
┌─────────────┐
│  Connected  │────────────────┐
└────┬────────┘                │
     │                         │ idle timeout
     │ process_event (many)    │ session expired
     │                         │ manual disconnect
     ↓                         │
┌─────────────┐                │
│   Active    │◄───────────────┘
└────┬────────┘
     │ disconnect
     ↓
┌──────────────┐
│ Disconnected │
└──────────────┘
```

**State Definitions**:
- **Initial**: Connection attempt in progress
- **Connected**: Authenticated, idle (no recent activity)
- **Active**: Processing events, sending/receiving messages
- **Disconnected**: Connection lost, resources cleaned up

**State Persistence**: In-memory only (connections not persisted across server restart)

---

### Event Flow (Client → Server → Client)

```
Client                WebSocketManager           EventHandler
  │                          │                         │
  │──emit(event_type, data)─►│                         │
  │                          │──route_event()─────────►│
  │                          │                         │─process_event()
  │                          │                         │
  │                          │◄────return response────┤
  │◄───acknowledgment────────│                         │
  │                          │                         │
```

**Fire-and-Forget Flow**:
```
Client                WebSocketManager           EventHandler
  │                          │                         │
  │──emit(event_type, data)─►│──route_event()─────────►│─process_event()
  │                          │                         │  (no return)
  │                          │                         │
```

**Broadcast Flow**:
```
EventHandler         WebSocketManager           Clients
      │                     │                      │
      │──broadcast()───────►│                      │
      │                     │──emit()─────────────►│ (tab 1)
      │                     │──emit()─────────────►│ (tab 2)
      │                     │──emit()─────────────►│ (tab 3)
      │                     │                      │
```

---

## Validation and Constraints

### Event Type Naming

**Pattern**: lowercase snake_case (e.g., `notification`, `data_update`, `agent_status`) — canonical definition lives in contracts/event-schemas.md §Event Type Naming

**Reserved Names** (Socket.IO built-ins, cannot be used):
- `connect`
- `disconnect`
- `error`
- `ping`
- `pong`

**Validation**:
- Event type must match `^[a-z][a-z0-9_]*$` regex
- Length: 1-50 characters
- No event type can be registered by multiple handlers
- Handlers must explicitly declare event types (no auto-derivation)

---

### Message Size

**Limits**:
- Single-event payload hard cap: 50MB

**Recommendations**:
- Prefer chunking above ~10MB, or use HTTP for large/binary transfers
- Large datasets: Use pagination or streaming (not part of infrastructure)
- Binary data: Not supported (use base64 or HTTP uploads)

**Enforcement**:
- No hard limit at application level
- Socket.IO protocol may fragment large messages
- Underlying TCP/WebSocket limits apply

---

### Connection Limits

**Single-User Scope**:
- Expected: 1-10 connections (typical user with multiple tabs)
- Tested: 100 concurrent connections (success criteria)
- No artificial limit enforced (single-user application)

**Resource Management**:
- Connections cleaned up immediately on disconnect
- Event buffers limited to 100 events per client
- No connection pooling needed (lightweight connections)

**Session Tracking Buckets**:
- Special bucket `allUsers` internally tracks all active SIDs. Helpers:
  - `get_sids_for_user(user=None)` → returns all SIDs (current behavior; placeholder arg for future multi‑tenant evolution)
  - `get_user_for_sid(sid)` → reverse lookup, best‑effort (single user today)

---

## Error Handling

### Connection Errors

**Authentication Failure**:
```python
# Server rejects connection
return False  # Socket.IO connect handler

# Client receives error event
socket.on('connect_error', (error) => {
    console.error('Connection failed:', error);
});
```

**CSRF Validation Failure**:
```python
# Server rejects connection
return False  # Socket.IO connect handler

# Logged server-side with PrintStyle.error()
```

---

### Event Processing Errors

**Handler Exception**:
```python
# Caught by WebSocketManager
try:
    response = await handler.process_event(event_type, data, sid)
except Exception as e:
    PrintStyle.error(f"Error processing event {event_type}: {e}")
    return {'error': 'Internal server error'}
```

**Unknown Event Type**:
```python
# No handler registered
return {'error': f'No handler for event type: {event_type}'}
```

**Malformed Event Data**:
```python
# Handler validates data, returns error response
return {'error': 'Invalid event data', 'details': validation_errors}
```

---

## Data Lifecycle

### Connection Lifecycle

1. **Creation**: Client initiates connection, server authenticates
2. **Active Use**: Events processed, messages exchanged
3. **Disconnection**: Clean up resources, buffer events if temporary
4. **Reconnection**: Restore connection, deliver buffered events
5. **Final Cleanup**: Remove buffer after extended disconnection via lazy expiration after ~1 hour without reconnection (see contracts/event-schemas.md §Buffer Lifecycle)

**Timeline**:
- Connection: < 1 second
- Active use: Hours (8+ hours expected per success criteria)
- Reconnection: < 5 seconds (success criteria)
- Buffer retention: Up to ~1 hour without reconnection (lazy expiration)

---

### Event Lifecycle

1. **Creation**: Handler or client creates event with type and data
2. **Transmission**: Event serialized to JSON, sent via Socket.IO
3. **Processing**: Receiver deserializes, routes to handler or callback
4. **Response** (optional): Request-response pattern returns data
5. **Completion**: Event discarded (no persistence)

**Timeline**:
- Creation to delivery: < 100ms (success criteria)
- Processing: Varies by handler logic
- Total round-trip: < 200ms typical for request-response

---

## Testing Considerations

### Unit Test Data

**Minimal WebSocketConnection**:
```python
connection = WebSocketConnection(
    sid="test-sid-123",
    authenticated=True,
    connected_at=datetime.now(),
    last_activity=datetime.now(),
    user_agent="Test UA",
    ip_address="127.0.0.1"
)
```

**Sample WebSocketEvent**:
```python
event = WebSocketEvent(
    event_type="test_notification",
    data={"message": "Test message", "level": "info"},
    sender_sid="test-sid-123",
    timestamp=datetime.now(),
    pattern=EventPattern.FIRE_AND_FORGET
)
```

**Mock EventHandler**:
```python
class MockHandler(WebSocketHandler):
    @classmethod
    def get_event_types(cls):
        return ["test_event"]

    async def process_event(self, event_type, data, sid):
        return {"status": "success", "echo": data}
```

---

## ASGI Combined App Depiction

Agent Zero serves a combined ASGI application that composes Socket.IO (AsyncServer) with the existing Flask app via a WSGI→ASGI adapter and runs under uvicorn. Relationships among entities defined in this document remain unchanged; this section documents runtime composition only.

```
┌────────────────────────────────────────────────────────────┐
│ Uvicorn (ASGI server)                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ socketio.ASGIApp                                     │  │
│  │  ├─ python‑socketio.AsyncServer (async_mode='asgi')  │  │
│  │  └─ other_asgi_app → WsgiToAsgi(Flask application)   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

Key notes:
- Single‑worker default to preserve in‑memory `ConnectionRegistry` and `EventBuffer` semantics; for multi‑worker, configure a Socket.IO message queue (e.g., Redis) to maintain cross‑worker signaling.
- `max_http_buffer_size = 50MB` remains enforced at the engine level; application guidance prefers chunking ≥10MB or HTTP for large/binary transfers.
- CSRF connection‑time validation (120s WS flag from POST `/csrf_token`) and Flask session cookies behave identically under ASGI.

## Performance Characteristics

### Memory Usage

- **Per connection**: ~1KB (connection metadata)
- **Per buffered event**: ~1KB average (varies by payload)
- **Total for 100 connections**: ~100KB + event buffers (~10MB max with full buffers)

### CPU Usage

- **Connection establishment**: Minimal (< 10ms)
- **Event routing**: O(1) lookup by event type
- **Event serialization**: O(n) where n = payload size
- **Broadcasting**: O(m) where m = number of connections

### Network Usage

- **Heartbeat overhead**: ~100 bytes every 25 seconds (Socket.IO default)
- **Event overhead**: ~50 bytes per event (Socket.IO framing)
- **Typical event**: 500 bytes - 10KB (depends on payload)

---

## Summary

**Core Entities**: 6 (Connection, Event, Handler, Subscription, Buffer, Registry)
**Relationships**: Simple one-to-many and many-to-one patterns
**State Management**: In-memory, no persistence
**Validation**: Explicit rules for event types, message size, connection limits
**Error Handling**: Comprehensive coverage with graceful degradation
**Performance**: Lightweight, scalable to 100+ concurrent connections

**Next Phase**: Phase 1 continues with contract definitions (contracts/) and developer guide (quickstart.md)
