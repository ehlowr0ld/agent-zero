# QuickStart Guide: WebSocket Event Handlers

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Audience**: Developers building real-time features with Agent Zero

## Introduction

This guide provides everything you need to start building real-time features using Agent Zero's WebSocket infrastructure. You'll learn how to create WebSocket event handlers, emit and receive events, and integrate WebSocket communication into Alpine.js components.

**Time to First WebSocket Event**: ~15 minutes

### When to Use WebSocket vs HTTP Polling

Agent Zero supports **both WebSocket and HTTP polling** as permanent first-class communication channels. Choose based on your feature requirements:

| Use WebSocket When... | Use HTTP Polling When... |
|----------------------|-------------------------|
| ✅ Server needs to **push updates** to client immediately | ✅ Client **requests data** on demand |
| ✅ Real-time **bidirectional** communication required | ✅ Simple **request-response** pattern sufficient |
| ✅ **Frequent updates** (multiple per second) | ✅ **Periodic checks** (every few seconds/minutes) |
| ✅ **Low latency** critical (<100ms) | ✅ Latency of 1-2 seconds acceptable |
| ✅ Multiple clients need **synchronized state** | ✅ Independent client operations |

**Examples**:
- **WebSocket**: Live notifications, real-time progress updates, collaborative editing, chat messages, streaming data
- **HTTP Polling**: Status checks, periodic data refresh, user-initiated queries, batch operations

**Note**: You can use both in the same application. Existing features continue using HTTP polling without changes.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [ASGI Runtime (Uvicorn + AsyncServer)](#asgi-runtime-uvicorn--asyncserver)
3. [Quick Start: Your First Handler](#quick-start-your-first-handler)
4. [Backend: Creating WebSocket Handlers](#backend-creating-websocket-handlers)
5. [Frontend: Using WebSocket Client](#frontend-using-websocket-client)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)
9. [Next Steps](#next-steps)

---

## Prerequisites

- Agent Zero development environment set up
- Familiarity with Python async/await
- Basic understanding of Alpine.js components
- `python-socketio` and `uvicorn` installed (listed in `requirements.txt`)

---

## ASGI Runtime (Uvicorn + AsyncServer)

Agent Zero serves a combined ASGI application where Socket.IO (`python-socketio.AsyncServer` with `async_mode='asgi'`) and the Flask app (mounted via WSGI→ASGI adapter) are hosted by `uvicorn`.

- Startup command remains the same:
  - Run: `python run_ui.py`
  - Behavior: starts an ASGI uvicorn server (access‑log disabled; error‑only)
- Security parity:
  - Sessions: Flask session cookie unchanged
  - CSRF: POST `/csrf_token` preflight sets a short‑lived (120s) WS flag checked during connect/reconnect
- Performance:
  - Default single worker to preserve in‑memory connection state and buffering
  - For multiple workers, configure a `python-socketio` message queue (e.g., Redis) to maintain cross‑worker signals

Verification checklist:
- Visit `http://localhost:5000` and confirm pages load as before
- Open the browser devtools Network tab → confirm Socket.IO transport connects
- Ensure server logs show uvicorn running without access‑log spam

---

## Quick Start: Your First Handler

### 1. Create a Handler (Backend)

**File**: `python/websocket_handlers/hello_handler.py`

```python
from python.helpers.websocket import WebSocketHandler

class HelloHandler(WebSocketHandler):
    """Simple hello world handler"""

    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["hello_request"]

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Received hello from {sid}")

        # Return response for request-response pattern
        return self.result_ok(
            {
                "message": f"Hello, {data.get('name', 'stranger')}!",
                "status": "success",
            }
        )
```

### 2. Use the Handler (Frontend)

**In any Alpine.js component**:

```javascript
import { websocket, createCorrelationId, normalizeProducerOptions } from '/js/websocket.js';

function helloComponent() {
    return {
        name: '',
        response: '',

        async init() {
            await websocket.connect(); // optional: await handshake before interacting
        },

        async sendHello() {
            try {
                const options = normalizeProducerOptions({
                    correlationId: createCorrelationId('hello'),
                });
                const { results } = await websocket.request(
                    'hello_request',
                    { name: this.name },
                    options,
                );
                this.response = results[0]?.data?.message || '';
            } catch (error) {
                console.error('Hello failed:', error);
            }
        }
    }
}
```

### 3. Test It

1. Start Agent Zero: `python run_ui.py`
2. Open browser: `http://localhost:5000`
3. Enter name and click "Send Hello"
4. See response: "Hello, [your name]!"

ASGI specific checks:
- Toggle network offline/online to see automatic reconnection
- Observe that reconnect_attempt triggers CSRF preflight (POST `/csrf_token`) before the handshake retry

---

## Backend: Creating WebSocket Handlers

### Handler Structure

**Location**: `python/websocket_handlers/`

**Base Template**:
```python
from python.helpers.websocket import WebSocketHandler

class MyHandler(WebSocketHandler):
    """Handler description"""

    # REQUIRED: Declare event types
    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["event_type_1", "event_type_2"]

    # OPTIONAL: Override default (True)
    @classmethod
    def requires_auth(cls) -> bool:
        return True  # Require authentication

    # OPTIONAL: Override default (requires_auth())
    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()  # Require CSRF validation

    # REQUIRED: Process incoming events
    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        from python.helpers.print_style import PrintStyle

        # Your logic here
        if event_type == "event_type_1":
            # Fire-and-forget: return None
            PrintStyle.info(f"Processed {event_type}")
            return None

        elif event_type == "event_type_2":
            # Request-response: return dict
            return {"status": "success", "data": "result"}

    # OPTIONAL: Aggregated broadcast request handler support (requestAll)
    # Handlers may implement internal fan-out and aggregation when appropriate
```

> **Singleton reminder**: Handlers are now singletons. Always obtain a reference via `MyHandler.get_instance()` (the manager does this automatically during discovery). Instantiating `MyHandler()` directly raises `SingletonInstantiationError`. This keeps shared state (locks, caches) consistent across reconnects.

## Backend: Multiple Handlers per Event

Register two handlers for the same event type; both will execute on request‑response, and results will be aggregated.

```python
class HelloHandlerA(WebSocketHandler):
    @classmethod
    def get_event_types(cls):
        return ["hello_request"]
    async def process_event(self, event_type, data, sid):
        return {"from": "A", "msg": "hello"}

class HelloHandlerB(WebSocketHandler):
    @classmethod
    def get_event_types(cls):
        return ["hello_request"]
    async def process_event(self, event_type, data, sid):
        return {"from": "B", "msg": "hi"}
```

Client `request('hello_request', {...})` resolves to an array of two results (multi‑handler aggregation). `requestAll('hello_request', ...)` resolves to an array of `{ sid, results: [...] }`.

```python
    # OPTIONAL: Connection lifecycle hooks
    async def on_connect(self, sid: str):
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Client {sid} connected")

        # Optional: Access user context from Flask session
        from flask import session
        user_id = session.get("user_id", "unknown")

    async def on_disconnect(self, sid: str):
        from python.helpers.print_style import PrintStyle

        PrintStyle.info(f"Client {sid} disconnected")
```

---

### Event Type Naming

**Pattern**: lowercase_snake_case
**Regex**: `^[a-z][a-z0-9_]*$` (canonical definition in contracts/event-schemas.md)
**Length**: 1-50 characters

**Examples**:
```python
# ✅ GOOD
["notification", "data_update", "query_results", "agent_status"]

# ❌ BAD
["Notification"]          # Uppercase
["data-update"]           # Hyphens
["123_event"]             # Starts with number
["connect"]               # Reserved Socket.IO event
```

---

### Fire-and-Forget Events

**Use Case**: One-way notifications, status updates

**Pattern**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    if event_type == "notification":
        from python.helpers.print_style import PrintStyle

        # Process notification
        PrintStyle.info(f"Notification: {data['message']}")

        # Broadcast to all clients
        self.broadcast("notification_broadcast", {
            "message": data["message"],
            "level": data.get("level", "info"),
            "timestamp": datetime.now().isoformat()
        }, exclude_sids=sid)  # Exclude sender

        # Return None for fire-and-forget
        return None
```

---

### Request-Response Events

**Use Case**: Queries, commands requiring acknowledgment

**Pattern**:
```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    if event_type == "query_data":
        # Fetch data
        results = await self.fetch_data(data["query"])

        # Return response
        return {
            "data": results,
            "count": len(results),
            "status": "success"
        }
```

---

### Sending Events to Clients

#### Send to Specific Client

```python
# Send to specific connection
self.emit_to(sid, "data_update", {
    "entity": "task",
    "operation": "update",
    "data": {"id": "123", "status": "completed"}
})
```

#### Broadcast to All Clients

```python
# Broadcast to all connections
self.broadcast("status_change", {
    "status": "active",
    "reason": "System initialized"
})

# Broadcast to all except sender
self.broadcast("notification", data, exclude_sids=sid)
```

---

### Input Validation

**Always validate event data**:

```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    # Validate required fields
    if "message" not in data:
        return {"error": "Missing required field: message"}

    # Validate data types
    if not isinstance(data["message"], str):
        return {"error": "Field 'message' must be a string"}

    # Validate constraints
    if len(data["message"]) > 1000:
        return {"error": "Message too long (max 1000 characters)"}

    # Process valid event
    from python.helpers.print_style import PrintStyle

    PrintStyle.info(f"Valid notification: {data['message']}")
    return {"status": "acknowledged"}
```

---

### Error Handling

**Handler exceptions caught automatically**:

```python
async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
    try:
        # Your logic
        result = await risky_operation()
        return {"status": "success", "data": result}

    except ValueError as e:
        # Return explicit error
        return {"error": f"Validation error: {e}"}

    except Exception as e:
        from python.helpers.print_style import PrintStyle

        # Log error, generic error returned to client
        PrintStyle.error(f"Error processing {event_type}: {e}")
        raise  # WebSocketManager catches and returns generic error
```

---

## Frontend: Using WebSocket Client

### Import WebSocket Client

```javascript
import { websocket } from '/js/websocket.js';
```

### Connect to WebSocket

**Lazy connection (automatic)**:
```javascript
// Connection is established automatically; await if you must block on readiness
await websocket.connect();
```

**Manual connection**:
```javascript
function myComponent() {
    return {
        async init() {
            try {
                await websocket.connect(); // optional: ensures promise resolves before continuing
                console.log('WebSocket connected');
            } catch (error) {
                console.error('Connection failed:', error);
            }
        }
    }
}
```

---

### Send Fire-and-Forget Events

**Pattern**: Use `emit()` for one-way messages

```javascript
function notificationComponent() {
    return {
        sendNotification(message, level) {
            try {
                websocket.emit('notification', {
                    message: message,
                    level: level
                });
                console.log('Notification sent');
            } catch (error) {
                console.error('Failed to send:', error);
            }
        }
    }
}
```

---

### Send Request-Response Events

**Pattern**: Use `request()` for queries requiring response

```javascript
function dataComponent() {
    return {
        data: [],
        loading: false,

        async loadData() {
            this.loading = true;
            try {
                const { results } = await websocket.request(
                    'query_data',
                    { query: 'active_tasks', limit: 10 },
                    { includeHandlers: ['handlers.tasks.ActiveTaskQuery'], timeoutMs: 5_000 }
                );

                this.data = results[0]?.data?.items ?? results[0]?.data ?? [];
                console.log(`Loaded ${this.data.length} items`);
            } catch (error) {
                console.error('Query failed:', error);
                this.data = [];
            } finally {
                this.loading = false;
            }
        }
    }
}
```

---

### Receive Events from Server

**Pattern**: Use `on()` to subscribe

```javascript
import { websocket, validateServerEnvelope, normalizeProducerOptions } from '/js/websocket.js';

function notificationComponent() {
    return {
        notifications: [],

        init() {
            // Subscribe to server events
            websocket.on('notification_broadcast', (payload) => {
                const { handlerId, eventId, ts, data } = validateServerEnvelope(payload);
                this.notifications.push({
                    handlerId,
                    eventId,
                    message: data.message,
                    level: data.level,
                    timestamp: ts
                });
            });
        }
    }
}
```

### Filtered Requests and Broadcast Exclusions

```javascript
function filteredComponent() {
    return {
        async refreshOnlyAnalytics() {
            // Target specific backend handlers with includeHandlers
            const options = normalizeProducerOptions({
                includeHandlers: ['handlers.analytics.MetricCollector'],
            });
            const { correlationId, results } = await websocket.request('refresh_metrics', {}, options);
            console.log({ correlationId, results });
        },

        async refreshAllButOneHandler() {
            // Exclude selected handlers during requestAll fan-out
            const options = normalizeProducerOptions({
                excludeHandlers: ['handlers.experimental.LegacyView'],
            });
            const aggregate = await websocket.requestAll('refresh_view', { scope: 'team' }, options);
            console.log(aggregate);
        },

        broadcastExceptSelf(payload) {
            // Broadcast to every connection except the caller's SID
            const options = normalizeProducerOptions({
                excludeSids: websocket.socket?.id ? [websocket.socket.id] : undefined,
            });
            websocket.broadcast('dashboard_update', payload, options);
        }
    };
}
```

> ℹ️ Filter options are scoped per method: `emit()` and `request()` accept `includeHandlers`, `requestAll()` accepts `excludeHandlers`, and `broadcast()` supports `excludeSids` only. The lists are mutually exclusive by design; supplying unsupported filters triggers a client-side validation error to preserve symmetry with backend routing rules.

---

### Unsubscribe from Events

**Pattern**: Use `off()` for cleanup

```javascript
function myComponent() {
    return {
        notificationHandler: null,

        init() {
            // Create handler reference
            this.notificationHandler = (data) => {
                console.log('Notification:', data);
            };

            // Subscribe
            websocket.on('notification_broadcast', this.notificationHandler);
        },

        destroy() {
            // Unsubscribe
            if (this.notificationHandler) {
                websocket.off('notification_broadcast', this.notificationHandler);
            }
        }
    }
}
```

---

### Connection Lifecycle Hooks

```javascript
function statusComponent() {
    return {
        connectionStatus: 'connecting',

        init() {
            // Connection established
            websocket.onConnect(() => {
                this.connectionStatus = 'connected';
                console.log('WebSocket connected');
            });

            // Connection lost
            websocket.onDisconnect((reason) => {
                this.connectionStatus = 'disconnected';
                console.warn('Disconnected:', reason);
            });

            // Connection errors
            websocket.onError((error) => {
                console.error('WebSocket error:', error);
            });
        }
    }
}
```

---

## Common Patterns

### Pattern 1: Real-Time Notifications

**Backend** (`notification_handler.py`):
```python
class NotificationHandler(WebSocketHandler):
    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["send_notification"]

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        # Broadcast to all connections
        self.broadcast("notification_broadcast", {
            "message": data["message"],
            "level": data.get("level", "info"),
            "timestamp": datetime.now().isoformat()
        }, exclude_sids=sid)

        return None  # Fire-and-forget
```

**Frontend**:
```javascript
function notificationComponent() {
    return {
        notifications: [],

        init() {
        websocket.on('notification_broadcast', ({ data, correlationId }) => {
            this.notifications.unshift({ ...data, correlationId });
                this.showToast(data.message, data.level);
            });
        },

        showToast(message, level) {
            // Show toast notification
        }
    }
}
```

---

### Pattern 2: Data Synchronization

**Backend** (`data_sync_handler.py`):
```python
class DataSyncHandler(WebSocketHandler):
    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["subscribe_data", "unsubscribe_data"]

    async def on_connect(self, sid: str):
        # Track subscriptions per connection
        if not hasattr(self, 'subscriptions'):
            self.subscriptions = {}
        self.subscriptions[sid] = set()

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        if event_type == "subscribe_data":
            entity = data["entity"]
            self.subscriptions[sid].add(entity)
            return {"status": "subscribed", "entity": entity}

        elif event_type == "unsubscribe_data":
            entity = data["entity"]
            self.subscriptions[sid].discard(entity)
            return {"status": "unsubscribed", "entity": entity}

    async def broadcast_update(self, entity: str, operation: str, data: dict):
        """Call from application code to broadcast updates"""
        self.broadcast("data_update", {
            "entity": entity,
            "operation": operation,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
```

**Frontend**:
```javascript
function dataComponent() {
    return {
        data: [],

        async init() {
            // Subscribe to entity updates
            const { correlationId, results } = await websocket.request('subscribe_data', {
                entity: 'tasks'
            });
            console.log('Subscribed:', { correlationId, results });

            // Listen for updates
            websocket.on('data_update', ({ data }) => {
                if (data.entity === 'tasks') {
                    this.applyUpdate(data);
                }
            });
        },

        applyUpdate(update) {
            const index = this.data.findIndex(item => item.id === update.data.id);

            if (update.operation === 'create') {
                this.data.push(update.data);
            } else if (update.operation === 'update' && index !== -1) {
                this.data[index] = update.data;
            } else if (update.operation === 'delete' && index !== -1) {
                this.data.splice(index, 1);
            }
        }
    }
}
```

---

### Pattern 3: Progress Tracking

**Backend** (`progress_handler.py`):
```python
class ProgressHandler(WebSocketHandler):
    @classmethod
    def get_event_types(cls) -> list[str]:
        return ["start_task"]

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        if event_type == "start_task":
            task_id = data["task_id"]

            # Start async task
            asyncio.create_task(self.run_long_task(task_id, sid))

            return {"status": "started", "task_id": task_id}

    async def run_long_task(self, task_id: str, sid: str):
        """Long-running task with progress updates"""
        for progress in range(0, 101, 10):
            await asyncio.sleep(1)  # Simulate work

            # Send progress update
            self.emit_to(sid, "task_progress", {
                "task_id": task_id,
                "progress": progress,
                "status": "running" if progress < 100 else "completed"
            })
```

**Frontend**:
```javascript
function taskComponent() {
    return {
        taskId: null,
        progress: 0,
        status: 'idle',

        init() {
            websocket.on('task_progress', (data) => {
                if (data.task_id === this.taskId) {
                    this.progress = data.progress;
                    this.status = data.status;
                }
            });
        },

        async startTask() {
            try {
                const { results } = await websocket.request('start_task', {
                    task_id: 'task-123'
                });
                this.taskId = results[0]?.data?.task_id;
                this.status = 'running';
            } catch (error) {
                console.error('Failed to start task:', error);
            }
        }
    }
}
```

---

## Troubleshooting

### Connection Issues

**Problem**: WebSocket not connecting

**Solutions**:
1. Check server is running: `python run_ui.py` (should start uvicorn)
2. Check AsyncServer initialized and wrapped by `socketio.ASGIApp` in runtime
3. Check browser console for errors
4. Verify CSRF token available: `GET /csrf_token` and POST preflight occurs
5. Check authentication (logged in?)

**Debug**:
```javascript
websocket.onError((error) => {
    console.error('Connection error:', error);
});
```

---

### Event Not Received

**Problem**: Event sent but not received

**Solutions**:
1. Verify handler registered (check server logs at startup)
2. Verify event type matches exactly (case-sensitive)
3. Check handler `get_event_types()` includes event type
4. Check subscription: `websocket.on('event_type', callback)`
5. Check connection active: `websocket.isConnected()`

**Debug**:
```python
from python.helpers.print_style import PrintStyle

# In handler
PrintStyle.info(f"Event types: {self.get_event_types()}")
PrintStyle.info(f"Processing {event_type} from {sid}")
```

---

### Events Not Persisted

**Problem**: Events lost after reconnection

**Expected**: Only last 100 events buffered, fire-and-forget only

**Solutions**:
1. Check if fire-and-forget (request-response not buffered)
2. Check buffer size (100 events max per client)
3. Verify reconnection happens (onConnect callback)
4. Use request-response pattern for critical events

---

### Handler Not Found

**Problem**: `No handler for event type: X`

**Solutions**:
1. Verify handler file in `python/websocket_handlers/`
2. Verify handler inherits from `WebSocketHandler`
3. Verify `get_event_types()` returns correct event types
4. Check server startup logs for registration messages
5. Restart server after adding new handler

---

## Best Practices

### Backend

1. **Always validate input**: Never trust client data
2. **Use type hints**: Document expected data structure
3. **Use PrintStyle for logging**: `PrintStyle.info()`, `PrintStyle.error()`, etc. (import from `python.helpers.print_style`)
4. **Return explicit errors**: Help clients understand failures
5. **Use async/await**: Never block event loop
6. **Keep handlers focused**: One responsibility per handler
7. **Log security events**: Authentication failures, CSRF violations

### Frontend

1. **Subscribe in init()**: Set up event listeners early
2. **Unsubscribe in destroy()**: Clean up subscriptions
3. **Handle errors gracefully**: Show user-friendly messages
4. **Use Alpine.js escaping**: `x-text` not `x-html` for untrusted data
5. **Check connection status**: `websocket.isConnected()` before emitting
6. **Use request() for critical operations**: Get acknowledgment
7. **Set reasonable timeouts**: Default 30s, adjust per use case

### General

1. **Choose right pattern**: Fire-and-forget vs request-response
2. **Keep messages small**: < 1MB for performance
3. **Test reconnection**: Simulate network loss
4. **Monitor server logs**: Watch for errors and warnings
5. **Document event schemas**: Help future developers

---

## Next Steps

### Learning Resources

- **Architecture**: Read [`/docs/architecture.md`](../../../docs/architecture.md)
- **Contracts**: Detailed contracts in [`/specs/003-websocket-event-handlers/contracts/`](./contracts/)
- **Data Model**: Entity relationships in [`data-model.md`](./data-model.md)
- **Research**: Technical decisions in [`research.md`](./research.md)

### Example Projects

1. **Real-Time Chat**: Single-user, multi-tab synchronized chat
2. **Live Dashboard**: Real-time metrics and updates
3. **Single-User Editing**: Multi-tab synchronized editing for one user
4. **Progress Tracking**: Long-running task monitoring

### Advanced Topics

- **Custom Serialization**: Handle non-JSON data types
- **Event Filtering**: Server-side subscription filtering
- **Rate Limiting**: Throttle event processing
- **Compression**: Reduce message size for large payloads
- **Multi-Tab Coordination**: Synchronize state across tabs

---

## Summary

**Backend**:
- Create handlers in `python/websocket_handlers/`
- Inherit from `WebSocketHandler`
- Implement `get_event_types()` and `process_event()`
- Use `emit_to()` and `broadcast()` to send events

**Frontend**:
- Import `websocket` singleton
- Call `connect()` for lazy initialization
- Use `emit()` for fire-and-forget, `request()` for request-response
- Use `on()` to subscribe, `off()` to unsubscribe

**Patterns**:
- Notifications: Broadcast to all clients
- Data Sync: Subscribe/unsubscribe with updates
- Progress: Long-running tasks with updates

**Next**: Check out [`contracts/`](./contracts/) for detailed API specifications

---

**Happy coding!** 🚀

## Frontend Client Verification

Use this checklist to validate the WebSocket client implementation in `webui/js/websocket.js` after code changes:

1. **Connection & CSRF preflight**
   - Clear cookies, load the app, and trigger a WebSocket action.
   - Confirm `/csrf_token` POST succeeds in network tab before the socket connects.
   - Force a reconnect by toggling network offline/online; observe `reconnect_attempt` preflight repeating successfully and the socket reconnecting without errors.

2. **Emit payload size guard**
   - Open the browser console and run:
     ```javascript
     websocket.emit("test_event", { data: "x".repeat(51 * 1024 * 1024) });
     ```
   - Verify an exception `Payload too large` is thrown client-side before the request is sent.

3. **Request timeout handling**
   - With the backend test handler that intentionally delays responses, call:
     ```javascript
     await websocket.request("delayed_response", {}, { timeoutMs: 1_000 });
     ```
   - Confirm the promise rejects with `Request timeout` and no stale handlers remain (subsequent fast requests succeed).

4. **Subscription persistence across reconnect**
   - Subscribe to an event (`websocket.on("heartbeat", console.log)`), then simulate network loss for >10 seconds.
   - When the connection restores, publish a `heartbeat` event from the server and ensure the callback still fires without re-registering.

5. **requestAll aggregation**
   - Trigger a `requestAll` call while two browser tabs are connected.
   - Verify the returned array includes both SIDs with per-handler results, and stalled handlers are marked with `{ code: "TIMEOUT" }` rather than rejecting the promise.

Document results in the issue tracker or commit log before marking related tasks as complete.

## Developer Harness

A WebSocket validation harness is available under **Settings → Developer → WebSocket Test Harness**. It opens a modal with:

- **Automatic Validation Suite**: Runs emit, request/response, timeout, subscription persistence, and requestAll aggregation checks sequentially. Progress logs appear in the harness with 5-second toasts summarising success/failure.
- **Manual Tests**: Buttons trigger individual scenarios (fire-and-forget emit, request/response, timeout, persistence, requestAll, broadcast demo). Each surface results via 5-second toasts and append to the log.
- **Log Output & Aggregated Results**: Text area records every step; JSON view shows last aggregated `requestAll` response; recent broadcast payloads listed for inspection.

**Recommended workflow**

1. Open the harness from Settings → Developer → Testing → WebSocket Test Harness.
2. Click **Run Full Suite**. Ensure the log shows each stage (emit, request, timeout, persistence, requestAll) and the toast reports success.
3. For manual buttons:
   - Trigger each scenario individually and observe the toast plus log entry.
   - Before running **requestAll** or **Broadcast demo**, open a second browser tab so you can confirm multi-connection behaviour.
   - Use the **Clear** button to reset the log between runs if desired.
4. Review the **Last Aggregated Results** and **Recent Broadcast Payloads** panels after tests to inspect raw data.

To observe multi-tab behaviour, open a second browser tab before running the broadcast or requestAll tests. When finished, use the **Clear** button to reset the log.

### New Diagnostics (Development Mode Only)
- **Uvicorn Access Log Toggle**: Settings → Developer now exposes a toggle that temporarily turns uvicorn access logs on/off. Leave it off for normal work; enable only when investigating transport-level issues. The toggle persists per developer profile and has no effect outside development mode.
- **WebSocket Event Console**: A companion modal captures inbound/outbound envelopes (with handlerId/eventId/correlationId metadata) while open. Opening the modal triggers a `ws_event_console_subscribe` request so the manager streams `ws_dev_console_event` diagnostics; closing it (or navigating away) emits `ws_event_console_unsubscribe`, ensuring there is zero overhead when the console is closed. Use the checkbox to switch between “all events” and “only events with registered handlers”.
