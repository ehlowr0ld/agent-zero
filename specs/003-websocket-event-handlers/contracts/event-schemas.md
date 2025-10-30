# Event Schemas Contract

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Contract Type**: Message Format Contract

## Purpose

This contract defines the message format, serialization rules, and validation requirements for WebSocket events transmitted between client and server. It ensures consistent, type-safe, and JSON-compatible event exchange.

---

## Event Structure

### Wire Format

All events transmitted over WebSocket follow this structure:

```json
{
  "event_type": "string",
  "data": { },
  "timestamp": "ISO8601"
}
```

**Socket.IO Envelope**:
Socket.IO wraps events in its own protocol envelope (handled automatically by python-socketio AsyncServer):
```json
["event_type", {"data": {...}, "timestamp": "..."}]
```

**Application Code**:
Developers work with the unwrapped structure - Socket.IO handles serialization/deserialization.

---

## Server→Client Delivery Envelope (Mandatory)

All server→client deliveries (including `emit_to` and `broadcast`) MUST wrap payloads in an application-level envelope to expose origin metadata to subscribers.

```typescript
interface ServerDeliveryEnvelope {
  handlerId: string; // Unique handler identifier (e.g., module.Class)
  eventId: string;   // UUIDv4 per delivery
  correlationId: string; // Correlates delivery with originating action
  ts: string;        // ISO8601 UTC with millisecond precision
  data: object;      // Original payload
}
```

Notes:
- This is not a Socket.IO transport change; it’s an application payload wrapper.
- Existing consumers remain compatible by reading `data`.
- Frontend `on(eventType, callback)` MUST deliver this envelope to callbacks.

---

## Event Type Naming

### Pattern

**Format**: lowercase snake_case
**Regex**: `^[a-z][a-z0-9_]*$`
**Length**: 1-50 characters

**Examples**:
```
✅ Valid:
- notification
- data_update
- agent_status
- user_action_completed
- query_results

❌ Invalid:
- Notification        (uppercase)
- data-update         (hyphens)
- 123_event           (starts with number)
- data__update        (double underscore - technically valid but discouraged)
- very_long_event_name_that_exceeds_the_fifty_character_limit  (too long)
```

### Reserved Event Types

These event types are reserved by Socket.IO and MUST NOT be used by application handlers:

- `connect`
- `disconnect`
- `error`
- `ping`
- `pong`
- `connect_error`
- `reconnect`
- `reconnect_attempt`
- `reconnect_error`
- `reconnect_failed`

**Validation**: Attempting to register handler for reserved event type results in registration error at server startup.

---

## Event Data Schema

### General Rules

**Format**: JSON object (JavaScript object / Python dict)

**Constraints**:
- MUST be JSON-serializable
- MUST NOT contain binary data (use base64 encoding if needed)
- SHOULD be under 1MB for optimal performance
- MAY be nested (objects within objects)
- MAY contain arrays
- MAY be empty (`{}`)

**Supported Types**:
- String
- Number (integer, float)
- Boolean
- Null
- Object (nested dict)
- Array (list)

**Unsupported Types**:
- Binary data (Buffer, Blob)
- Functions
- Circular references
- undefined (use null instead)

---

### Schema Definition

Handlers MAY document expected data schema (recommended for maintainability):

**Example** (`notification` event):
```typescript
interface NotificationData {
  message: string;           // Required: notification message
  level: "info" | "warning" | "error";  // Required: severity level
  timestamp?: string;        // Optional: ISO8601 timestamp
  metadata?: object;         // Optional: additional context
}
```

**Python Equivalent**:
```python
from typing import TypedDict, Literal, Optional

class NotificationData(TypedDict):
    message: str
    level: Literal["info", "warning", "error"]
    timestamp: Optional[str]
    metadata: Optional[dict]
```

**Validation**: Handlers SHOULD validate data against schema in `process_event()`:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    # Validate required fields
    if "message" not in data or "level" not in data:
        return {"error": "Missing required fields", "required": ["message", "level"]}

    if data["level"] not in ["info", "warning", "error"]:
        return {"error": "Invalid level", "valid": ["info", "warning", "error"]}

    # Process valid event
    ...
```

---

## Event Patterns

### 1. Fire-and-Forget Pattern

**Direction**: Client → Server or Server → Client

**Characteristics**:
- One-way communication
- No acknowledgment
- No response data
- Sender does not wait

**Client Sending** (JavaScript):
```javascript
// Emit event without waiting for response
websocket.emit('notification', {
  message: 'User action completed',
  level: 'info'
});
// Execution continues immediately
```

**Server Processing** (Python):
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    if event_type == "notification":
        # Process notification
        self.log.info(f"Notification: {data['message']}")
        # Return None for fire-and-forget
        return None
```

**Server Sending** (Python):
```python
# Emit to specific connection
self.emit_to(sid, 'data_update', {
  'timestamp': datetime.now().isoformat(),
  'data': updated_data
})

# Broadcast to all connections
self.broadcast('status_change', {
  'status': 'active',
  'reason': 'System initialized'
})

# Broadcast excluding specific participants
self.broadcast('status_change', {
  'status': 'active',
  'reason': 'System initialized'
}, exclude_sids={'sid-123'})
```

**Client Receiving** (JavaScript):
```javascript
// Subscribe to server events
websocket.on('data_update', ({ data, correlationId, handlerId }) => {
  console.log('Received update:', data, 'from', handlerId, 'correlation', correlationId);
  // No response sent
});
```

---

### 2. Request-Response Pattern

**Direction**: Client → Server → Client (or vice versa)

**Characteristics**:
- Two-way communication
- Sender waits for response
- Response contains data
- Timeout on failure

**Client Sending** (JavaScript):
```javascript
try {
  // Request with optional handler filter and millisecond timeout
  const { correlationId, results } = await websocket.request(
    'query_data',
    { query: 'SELECT * FROM users', limit: 10 },
    { includeHandlers: ['handlers.analytics.QueryHandler'], timeoutMs: 30_000 }
  );

  console.log('Correlation:', correlationId);
  console.log('Query result:', results[0]?.data);
} catch (error) {
  console.error('Request failed:', error);
}
```

**Server Processing** (Python):
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    if event_type == "query_data":
        # Process query
        results = await database.execute(data["query"], limit=data.get("limit", 10))
        # Return response data
        return {
            "data": results,
            "count": len(results),
            "status": "success"
        }
```

**Server Initiating Request** (still future work):
Server→Client request-response remains a future enhancement (not implemented now). Current release supports Server→Client fire-and-forget only.

---

## Request Result Schema (Multi‑Handler)

When an event type is registered by multiple server handlers, request‑response calls aggregate per‑handler outcomes.

```typescript
interface RequestResultItem {
  handlerId: string;      // e.g., "module.ClassName"
  ok: boolean;            // true if handler returned success
  data?: object;          // present when ok === true
  error?: ErrorResponse;  // present when ok === false
  durationMs?: number;    // optional per‑handler processing time
  correlationId?: string; // propagated when helper supplied it (optional)
}
```

Client `request(eventType, data)` returns `{ correlationId: string | null, results: RequestResultItem[] }`.

> **Developer Ergonomics**: Backend code SHOULD return `WebSocketResult.ok()` / `.error()` helper instances so the manager can populate this schema without manual dict assembly. Clients MAY use `validateServerEnvelope()` helper to ensure envelopes conform before consuming them.

---

### 2.1 Aggregated Request-Response (requestAll)

**Direction**: Client → Server → Clients → Server → Client

**Purpose**: Fan out a request to all active connections and aggregate per-connection results.

**Response Aggregate Schema**:
```typescript
interface AggregatedResultsPerSid {
  sid: string;                    // Connection id
  correlationId: string | null;   // Correlates per-sid execution
  results: RequestResultItem[];   // Per‑handler outcomes for this connection
  durationMs?: number;            // Optional total time for this sid
}

type AggregatedResponse = AggregatedResultsPerSid[];
```

**Timeout Handling (ms units)**:
- Timeout parameters are specified in milliseconds. Default is `0` (unlimited wait). If `timeoutMs>0`, handlers that do not complete are recorded as `ok=false` with `error={ code: "TIMEOUT", error: "Request timeout" }` in their respective `RequestResultItem`.
- `request()` uses the same per‑handler timeout marking; only transport/contract failures reject the Promise.
- Correlation id used internally for fan‑out/collection.

**Standardized Aggregation Errors**:
- For `request_all`, the server MUST include every targeted `sid` in the aggregate. If a `sid` has no matching handlers or a connection error occurs, include that `sid` with a `results` array containing a single standardized error item:
```typescript
// Example per-sid error entry when no handlers/connection error
{
  sid: string,
  correlationId: string | null,
  results: [{ handlerId: "__none__", ok: false, error: { code: "NO_HANDLERS" | "CONNECTION_NOT_FOUND", error: string } }]
}
```

**Example (Client)**:
```javascript
const aggregated = await websocket.requestAll('refresh_view', { scope: 'all' }, { timeoutMs: 30_000 });
aggregated.forEach(({ sid, correlationId, results }) => {
  console.log('Correlation:', correlationId);
  results.forEach(result => {
    if (result.ok) console.log(sid, result.data);
    else console.warn(sid, result.error);
  });
});
```

---

### Filter Metadata (Client → Server)

- `emit` and `request` MAY include `includeHandlers: string[]` to target specific backend handlers. When omitted, all registered handlers receive the payload.
- `requestAll` MAY include `excludeHandlers: string[]` to omit handlers from each sid fan-out. Mixed include/exclude lists are disallowed; providing unsupported filters MUST raise a validation error.
- Frontend clients MUST express timeouts via `timeoutMs` (milliseconds). A missing value defaults to `0` (unlimited) and is mirrored in the backend helper semantics.

Filter metadata is transported alongside the `data` payload inside the Socket.IO frame and interpreted exclusively by the WebSocketManager; handlers receive only the filtered workload.

---

## Common Event Schemas

### Infrastructure Events (Handled by WebSocketManager)

These events are managed by infrastructure and not routed to application handlers:

#### `connect`

**Direction**: Client → Server
**Purpose**: Establish WebSocket connection with authentication
**Data**: None (authentication via Flask session cookie)

**Client**:
```javascript
const websocket = new WebSocketClient();
await websocket.connect();  // Triggers 'connect' event internally
```

**Server**:
```python
@sio.event
async def connect(sid, environ, auth):
    """
    Authenticate connection using Flask session.

    Note: Socket.IO allows an optional 'auth' parameter, but we don't use it.
    Authentication comes from Flask session cookie automatically sent by browser.
    """
    # Authentication and CSRF validation managed by WebSocketManager
```

---

#### `disconnect`

**Direction**: Client ↔ Server
**Purpose**: Clean up resources when connection lost
**Data**: None

**Client**:
```javascript
websocket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
});
```

**Server**:
```python
@sio.event
async def disconnect(sid):
    # Cleanup managed by WebSocketManager
```

---

#### `error`

**Direction**: Server → Client
**Purpose**: Report connection or processing errors
**Data**:
```json
{
  "error": "string",        // Error message
  "details": "string",      // Optional error details
  "code": "string"          // Optional error code
}
```

**Client**:
```javascript
websocket.on('error', (error) => {
  console.error('WebSocket error:', error);
});
```

---

### Application Event Examples

These are example schemas for application-level events. Actual events defined by handlers.

#### `notification` (Example)

**Direction**: Server → Client
**Purpose**: Push notification to user
**Pattern**: Fire-and-forget

**Schema**:
```typescript
interface NotificationEvent {
  message: string;
  level: "info" | "warning" | "error";
  timestamp?: string;
  action?: {
    label: string;
    event_type: string;
    data: object;
  };
}
```

**Example**:
```json
{
  "message": "Task completed successfully",
  "level": "info",
  "timestamp": "2025-10-16T10:30:00Z",
  "action": {
    "label": "View Results",
    "event_type": "view_results",
    "data": {"task_id": "123"}
  }
}
```

---

#### `data_update` (Example)

**Direction**: Server → Client
**Purpose**: Push data changes to client
**Pattern**: Fire-and-forget

**Schema**:
```typescript
interface DataUpdateEvent {
  entity: string;           // Entity type (e.g., "user", "task")
  operation: "create" | "update" | "delete";
  data: object;             // Updated entity data
  timestamp: string;
}
```

**Example**:
```json
{
  "entity": "task",
  "operation": "update",
  "data": {
    "id": "123",
    "status": "completed",
    "progress": 100
  },
  "timestamp": "2025-10-16T10:30:00Z"
}
```

---

#### `query_data` (Example)

**Direction**: Client → Server
**Purpose**: Query data from server
**Pattern**: Request-response

**Request Schema**:
```typescript
interface QueryDataRequest {
  query: string;            // Query string
  filters?: object;         // Optional filters
  limit?: number;           // Optional result limit
}
```

**Response Schema**:
```typescript
interface QueryDataResponse {
  data: array;              // Query results
  count: number;            // Number of results
  status: "success" | "error";
  error?: string;           // Error message if status is "error"
}
```

**Example Request**:
```json
{
  "query": "active_tasks",
  "filters": {"user_id": "456"},
  "limit": 10
}
```

**Example Response**:
```json
{
  "data": [
    {"id": "1", "title": "Task 1"},
    {"id": "2", "title": "Task 2"}
  ],
  "count": 2,
  "status": "success"
}
```

---

## Error Response Schema

### Standard Error Format

All error responses SHOULD follow this format:

```typescript
interface ErrorResponse {
  error: string;            // Human-readable error message
  details?: string;         // Additional error details
  code?: string;            // Error code for programmatic handling
  field?: string;           // Field name if validation error
  timestamp?: string;       // Error timestamp
}
```

**Example**:
```json
{
  "error": "Validation failed",
  "details": "Missing required field 'message'",
  "code": "VALIDATION_ERROR",
  "field": "message",
  "timestamp": "2025-10-16T10:30:00Z"
}
```

### Common Error Codes

| Code | Meaning | Typical Response |
|------|---------|------------------|
| `VALIDATION_ERROR` | Invalid event data | `{"error": "...", "field": "..."}` |
| `NOT_FOUND` | Resource not found | `{"error": "Resource not found", "code": "NOT_FOUND"}` |
| `INTERNAL_ERROR` | Server error | `{"error": "Internal server error", "code": "INTERNAL_ERROR"}` |
| `TIMEOUT` | Request timeout | `{"error": "Request timeout", "code": "TIMEOUT"}` |
| `UNAUTHORIZED` | Auth failure | `{"error": "Unauthorized", "code": "UNAUTHORIZED"}` |

---

## Message Size Considerations

### Size Guidelines

**Enforced**:
- Single event maximum: 50MB (hard cap)

**Recommended**:
- Typical event: 500 bytes - 10KB
- Frequent events: < 1KB

**Protocol Overhead**:
- Socket.IO framing: ~50 bytes
- JSON overhead: ~10-20% of payload

**Large Payloads**:
- Prefer HTTP API for large/binary transfers
- Or use chunking: 1–4MB chunks with `sequence`, `total`, `checksum`, `correlationId`
- Finalization event confirms completion or triggers reassembly error

**Example - Paginated Results**:
```json
{
  "data": [...],  // First page
  "page": 1,
  "page_size": 10,
  "total": 150,
  "has_more": true,
  "next_page_token": "abc123"
}
```

---

## Timestamp Format

**Standard**: ISO 8601 in UTC

**Format**: `YYYY-MM-DDTHH:MM:SS.sssZ`

**Examples**:
```
✅ Valid:
- 2025-10-16T10:30:00Z
- 2025-10-16T10:30:00.123Z
- 2025-10-16T10:30:00.123456Z

❌ Invalid:
- 2025-10-16 10:30:00           (missing 'T')
- 2025-10-16T10:30:00           (missing 'Z')
- 10/16/2025 10:30 AM           (wrong format)
```

**Python**:
```python
from datetime import datetime
timestamp = datetime.utcnow().isoformat() + 'Z'
```

**JavaScript**:
```javascript
const timestamp = new Date().toISOString();
```

---

## Versioning

**Current Version**: v1 (implicit - no version field)

**Future Versioning** (if needed):
```json
{
  "version": "2",
  "event_type": "...",
  "data": {...}
}
```

**Backward Compatibility**:
- v1 events (no version field) remain supported indefinitely
- New versions add optional fields (never remove or rename)
- Breaking changes require new event type (e.g., `notification_v2`)

---

## Validation Rules Summary

| Aspect | Rule | Enforcement |
|--------|------|-------------|
| **Event Type** | `^[a-z][a-z0-9_]*$`, 1-50 chars | Server registration |
| **Reserved Types** | No Socket.IO built-ins | Server registration |
| **Data Format** | JSON object | Automatic (serialization) |
| **Binary Data** | Not allowed | Application (use base64) |
| **Message Size** | < 1MB recommended | Advisory (protocol handles) |
| **Timestamps** | ISO 8601 UTC | Application |
| **Response Format** | Dict or None | Handler contract |

---

## Testing Schemas

### Valid Event Examples

```javascript
// Fire-and-forget
{
  event_type: "notification",
  data: {
    message: "Test notification",
    level: "info"
  }
}

// Request-response
{
  event_type: "query_data",
  data: {
    query: "test_query",
    limit: 5
  }
}
```

### Invalid Event Examples

```javascript
// Missing event_type
{
  data: {...}
}

// Invalid event_type (uppercase)
{
  event_type: "Notification",
  data: {...}
}

// Binary data (not JSON-serializable)
{
  event_type: "upload_file",
  data: {
    file: new Blob([...])  // ❌ Not allowed
  }
}

// Circular reference
const data = {a: 1};
data.self = data;  // ❌ Not JSON-serializable
```

---

## Operational Clarifications

### Heartbeat Configuration

**Interval**: Socket.IO default heartbeat interval is **25 seconds** (ping/pong mechanism)

**Behavior**:
- Server sends `ping` frames every 25 seconds
- Client responds with `pong` frames
- Connection considered dead if no pong received within timeout
- Automatic and transparent (no handler code required)

**Rationale**: Socket.IO default interval is sufficient for single-user application with typical network conditions. No custom configuration needed.

**Override**: If custom interval required, configure in SocketIO initialization:
```python
sio = socketio.AsyncServer(
    async_mode='asgi',
    ping_interval=25,    # Ping interval in seconds (default: 25)
    ping_timeout=120,    # Timeout in seconds (default: 60)
)
```

---

### Buffer Lifecycle

**Cleanup Policy**: Event buffers are checked for expiration on buffer access (lazy cleanup):
- **Expiration**: Buffers older than **1 hour** without reconnection are cleared
- **Check Trigger**: Expiration checked when:
  - New event added to any buffer (`add_event()`)
  - Buffered events retrieved for delivery (`get_buffered_events()`)
  - Handler emits event to potentially disconnected client
- **No Background Task**: Expiration is lazy (checked on access), not active polling
- **Server Restart**: All in-memory buffers cleared on restart

**Rationale**: Lazy expiration prevents memory leaks from abandoned connections without requiring background cleanup tasks. One-hour window allows for temporary network issues while preventing indefinite memory growth.

---

### Disconnection Behaviors

**Graceful User Disconnection** (user closes browser tab):
- Browser sends `disconnect` event to server
- Server flushes any pending buffered events immediately (delivers if possible)
- Server calls handler `on_disconnect(sid)` for cleanup
- Connection removed from registry
- Buffer cleared after flush

**Abrupt Network Disconnection** (network failure, timeout):
- No disconnect notification from client
- Server detects timeout via heartbeat failure
- Server calls handler `on_disconnect(sid)` for cleanup
- Connection removed from registry
- Buffer preserved for potential reconnection (subject to 1-hour expiration)

**Session Expiration** (authentication timeout):
- Server detects expired session via heartbeat check or event processing
- Server calls `disconnect(sid)` internally
- Follows same cleanup flow as graceful disconnection
- Connection closed with reason: "session expired"

**Difference**: Graceful disconnection flushes buffers immediately; abrupt preserves buffers for reconnection.

---

### Server Restart Handling

**Buffer Persistence**:
- Buffers are **in-memory only** (not persisted to disk)
- All buffers **cleared on server restart** (standard web application behavior)

**Client Notification**:
- Server MAY broadcast `server_restart` event on startup to all connected clients
- Event is **fire-and-forget** (no error if client doesn't listen)
- Clients can register handler to refresh data or show notification:
  ```javascript
  websocket.on('server_restart', () => {
      console.log('Server restarted, refreshing data...');
      reloadData();
  });
  ```

**Rationale**: In-memory buffers are standard for WebSocket applications. Single-user scope makes disk persistence unnecessary complexity. Server restart event allows clients to react appropriately.

---

### Event Delivery Error Handling

**Targeted Event to Non-Existent Connection**:

When handler calls `emit_to(sid, event_type, data)` where `sid` does not exist (never existed or expired long ago):

**Behavior**:
- Check connection registry
- If `sid` not found AND not in buffer registry (never existed):
  - Raise `ConnectionNotFoundError` with descriptive message
  - Log warning: `PrintStyle.warning(f"Attempted to emit to non-existent connection: {sid}")`
  - Error propagates to calling handler for handling
- If `sid` not currently connected but has buffer (recently disconnected):
  - Buffer event normally (standard disconnected client behavior)

**Error Details**:
```python
class ConnectionNotFoundError(Exception):
    """Raised when attempting to emit to non-existent connection"""
    def __init__(self, sid: str):
        self.sid = sid
        super().__init__(f"Connection not found: {sid}")
```

**Handler Example**:
```python
try:
    self.emit_to(sid, 'notification', data)
except ConnectionNotFoundError as e:
    self.log.warning(f"Failed to emit: {e}")
    # Handler decides: retry, log, return error to client, etc.
```

**Rationale**: Proper error handling allows handlers to detect and respond to invalid connection attempts. Distinguishes between "recently disconnected" (buffer) and "never existed" (error).

---

### Handler Execution Timeouts

**Server-Side Timeout Policy**:
- **No global default timeout** on server-side handler execution
- **Rationale**: Handlers may perform legitimately long operations (e.g., file processing, model inference)
- **Handler Responsibility**: Handlers implement their own timeouts for async operations

**Frontend Request Timeout**:
- Client-side `request()`/`requestAll()` timeouts are specified in milliseconds; **default: 0 (unlimited)**.
- If a `timeoutMs>0` is provided and expires, non‑completed handlers are recorded with standardized timeout errors; the Promise resolves with aggregated results (rejects only for transport/contract failures).

**Best Practice for Long Operations**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    if event_type == "long_operation":
        # For operations > 30s, send progress updates
        async def long_task():
            for progress in range(0, 101, 10):
                await asyncio.sleep(5)  # Simulate work
                self.emit_to(sid, 'progress_update', {'progress': progress})

        asyncio.create_task(long_task())
        return {"status": "started"}  # Immediate response
```

**Handler Timeout Implementation** (optional):
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    try:
        # Handler-specific timeout (e.g., 60 seconds)
        result = await asyncio.wait_for(
            self.expensive_operation(data),
            timeout=60.0
        )
        return {"result": result}
    except asyncio.TimeoutError:
        return {"error": "Operation timed out", "timeout": 60}
```

**Rationale**: No default global timeout prevents false positives on legitimate long-running operations. Handlers control their own timeout policies. Frontend timeout protects client from hanging indefinitely.

---

## Summary

**Event Structure**: `{event_type: string, data: dict, timestamp: ISO8601}`
**Event Types**: lowercase_snake_case, no reserved types
**Data Format**: JSON-serializable dict; 50MB hard cap; typical payloads <10KB
**Patterns**: Fire-and-forget (no response) or request-response (with response)
**Error Format**: Standardized `{error, details, code, field}` structure
**Timestamps**: ISO 8601 UTC format
**Validation**: Schema-based validation in handler `process_event()`

**Next Contract**: [Frontend API](./frontend-api.md)
