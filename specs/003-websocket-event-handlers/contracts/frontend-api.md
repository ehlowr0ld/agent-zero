# Frontend API Contract

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Contract Type**: Frontend Client Library Contract

## Purpose

This contract defines the frontend JavaScript WebSocket client API that Alpine.js components and application code use to communicate with the server. The API mirrors existing REST API patterns (`api.js`) to ensure consistency and developer familiarity.

---

## Module: `webui/js/websocket.js`

**Export**: Singleton WebSocket client instance

```javascript
import { websocket } from '/js/websocket.js';
```

---

## WebSocketClient Class

### Constructor

**Internal** - Use singleton instance `websocket` instead of creating new instances

```javascript
class WebSocketClient {
    constructor() {
        this.socket = null;              // Socket.IO instance
        this.connected = false;          // Connection state
        this.connecting = false;         // Connection in progress
        this.subscriptions = new Map();  // event_type -> [callbacks]
        this.reconnectDelay = 1000;      // Initial reconnect delay (ms)
        this.maxReconnectDelay = 30000;  // Maximum reconnect delay (ms)
    }
}
```

---

## Connection Management

### `connect()`

**Purpose**: Establish WebSocket connection with authentication (lazy initialization)

**Signature**:
```javascript
async connect(): Promise<void>
```

**Behavior**:
- **If already connected**: Returns immediately (no-op)
- **If connecting**: Waits for connection to complete
- **Otherwise**: Initiates connection with CSRF authentication
- **Auto invocation**: The module triggers a connection during DOMContentLoaded and every producer method awaits readiness; manual calls are optional and primarily for diagnostics or gating UI until the socket is ready.

**Authentication & CSRF**:
- Retrieves CSRF token from cookie (mirrors `api.js` pattern)
- Performs HTTP preflight POST to `/csrf_token` with `X-CSRF-Token` header; server sets short‑lived session‑bound flag for WS (TTL 120 seconds)
- WebSocket connect checks that flag; no custom headers on WS handshake
- Uses existing Flask session for authentication

**Reconnect Optimization**:
- On `reconnect_attempt`, proactively POST `/csrf_token` with `X-CSRF-Token` to refresh the short‑lived WS flag (TTL 120s) before retrying the handshake. This avoids a failed attempt due to expired flag.

**Reconnection**:
- Automatic reconnection enabled
- Exponential backoff: 1s → 2s → 4s → 8s → ... → 30s max
- Reconnection continues indefinitely until successful

**Example**:
```javascript
import { websocket } from '/js/websocket.js';

// Optional: await the handshake if you need to block until the socket is ready
await websocket.connect();
console.log('Connected');
```

**Error Handling**:
- Throws `Error` if connection rejected (authentication failure)
- Emits `error` event for connection errors
- Logs connection failures to console

**Contract**:
- MUST retrieve CSRF token from cookie
- MUST send CSRF token in `X-CSRF-Token` header
- MUST enable automatic reconnection
- MUST use exponential backoff for reconnection
- SHOULD surface the same connection promise even when invoked repeatedly; the module auto-invokes it on bootstrap and every producer method awaits it internally.

---

### `disconnect()`

**Purpose**: Manually close WebSocket connection

**Signature**:
```javascript
disconnect(): void
```

**Behavior**:
- Closes Socket.IO connection
- Clears connection state
- Does NOT clear subscriptions (preserved for reconnection)

**Example**:
```javascript
websocket.disconnect();
console.log('Disconnected');
```

**Contract**:
- MUST close Socket.IO connection
- MUST set `connected = false`
- MUST preserve subscriptions for reconnection
- MUST NOT throw if already disconnected

---

### `isConnected()`

**Purpose**: Check connection status

**Signature**:
```javascript
isConnected(): boolean
```

**Returns**: `true` if connected, `false` otherwise

**Example**:
```javascript
if (websocket.isConnected()) {
    console.log('WebSocket is active');
}
```

---

## Event Emission (Client → Server)

### `emit()`

**Purpose**: Send fire-and-forget event to server (no acknowledgment)

**Signature**:
```javascript
emit(
  eventType: string,
  data: object,
  options?: { includeHandlers?: string[], correlationId?: string }
): void
```

**Parameters**:
- `eventType`: Event type identifier (registered with server handler)
- `data`: Event payload (JSON-serializable object)

**Behavior**:
- Sends event immediately if connected
- Throws `Error('Payload too large')` if payload exceeds 50MB (client-side precheck)
- Does NOT wait for acknowledgment
- Does NOT retry on failure
- Optional `includeHandlers` filters delivery to specific server handlers only; omit the option to target all registered handlers. `excludeHandlers` is intentionally unsupported to mirror backend constraints.
- Optional `correlationId` lets the caller track downstream activity; when omitted the server generates one automatically and echoes it in envelopes and acknowledgements.
- Awaits the connection automatically; if the handshake cannot be established (for example, the user is logged out), the promise rejects with `Error('Not connected')`.

**Example**:
```javascript
// Send notification to server
websocket.emit('notification', {
    message: 'User action completed',
    level: 'info'
});
```

**Error Handling**:
- Logs error to console
- Triggers error callback if registered
- Surfaces `Error('Not connected')` only when the handshake cannot be established

**Contract**:
- MUST propagate `Error('Not connected')` only when the connection handshake ultimately fails
- MUST NOT wait for acknowledgment
- MUST serialize data to JSON
- MUST NOT retry on failure (caller's responsibility)

---

### `request()`

**Purpose**: Send request-response event to server (waits for response)

**Signature**:
```javascript
async request(
  eventType: string,
  data: object,
  options?: { includeHandlers?: string[], timeoutMs?: number, correlationId?: string }
): Promise<{ correlationId: string | null, results: Array<RequestResultItem> }>
```

**Parameters**:
- `eventType`: Event type identifier (registered with server handler)
- `data`: Request payload (JSON-serializable object)
- `options.includeHandlers` (optional): Target only these handler identifiers
- `options.timeoutMs` (optional): Max wait in milliseconds (default: 0 → unlimited)
- `options.correlationId` (optional): Provide custom correlation identifier for downstream logging and envelopes

**Behavior**:
- Invokes all server handlers registered for the event in parallel
- Resolves with `{ correlationId, results }` where `results` is an array of per‑handler outcomes `{ handlerId, ok, data|error }`
- Timeout values are expressed in milliseconds. The default `timeoutMs` is `0`, which means unlimited wait. If `timeoutMs > 0`, on expiry marks non‑completed handlers with `ok=false` and `error={ code: 'TIMEOUT', error: 'Request timeout' }` and resolves with the array
- Rejects only for transport/contract failures: payload too large, protocol errors, or the connection handshake failing (`Error('Not connected')`)
- Developer harness exercises both code paths: it issues a delayed request without `timeoutMs` to confirm the default infinite wait succeeds and a second call with `timeoutMs` set to assert timeout errors surface as standardized result items rather than promise rejections.

**Example**:
```javascript
try {
    const { correlationId, results } = await websocket.request(
        'query_data',
        { query: 'active_tasks', limit: 10 },
        { timeoutMs: 5_000 }
    );

    console.log('Correlation:', correlationId);
    console.log('Query results:', results);
} catch (error) {
    console.error('Request failed:', error);
}
```

**Error Handling**:
- Rejects with `Error('Payload too large')` if payload exceeds 50MB (client-side precheck)
- Rejects with `Error('Request timeout')` if no response within timeout
- Rejects with server error if handler returns error response
- Propagates `Error('Not connected')` only when the handshake cannot be established

**Contract**:
- MUST return Promise resolving to `{ correlationId, results }`
- MUST reject only for transport/contract failures (not per‑handler timeouts); handshake failures surface as `Error('Not connected')`
- MUST support configurable timeout; non‑completed handlers become timeout error items
- MUST clean up timeout on success/failure

---

### `requestAll()`

**Purpose**: Broadcast request-response to all active connections and aggregate results

**Signature**:
```javascript
async requestAll(
  eventType: string,
  data: object,
  options?: { excludeHandlers?: string[], timeoutMs?: number, correlationId?: string }
): Promise<Array<{ sid: string, correlationId: string | null, results: Array<RequestResultItem> }>>
```

**Behavior**:
- Server aggregates results per connection with nested per‑handler outcomes
- Returns an array of `{ sid, correlationId, results: RequestResultItem[] }`
- Timeout values are expressed in milliseconds. The default `timeoutMs` is `0`, which means unlimited wait. If a positive value is supplied, non‑completed handlers are marked with timeout error objects in their result arrays
- Rejects only for transport/contract failures (payload too large, handshake failure producing `Error('Not connected')`)

**Filter Semantics (Client → Server)**:

| Operation | Supported Filter Option | Notes |
|-----------|------------------------|-------|
| `emit()` | `includeHandlers` | Deliver only to listed backend handlers; omit for broadcast-to-registered-handlers |
| `request()` | `includeHandlers` | Fan-out only to listed handlers; omit for all |
| `requestAll()` | `excludeHandlers` | Exclude specific handlers from each sid fan-out; omit for all |
| `broadcast()` | `excludeSids` | Exclude specific connection IDs; no include list supported |

Filters outside the permitted column are rejected; this maintains symmetry with backend routing rules.
### `broadcast()`

**Purpose**: Broadcast fire‑and‑forget event to all active connections with optional exclusions

**Signature**:
```javascript
broadcast(
  eventType: string,
  data: object,
  options?: { excludeSids?: string[], correlationId?: string }
): void
```

**Behavior**:
- Delivers event to all connections unless excluded via `excludeSids`
- No `includeSids` option at this time
- Fire‑and‑forget: no acknowledgment, no return value
- Optional `correlationId` lets the caller tie broadcast deliveries back to a triggering action; otherwise the server generates one per delivery.
- Automatic harness coverage validates the envelope fields (`handlerId`, `eventId`, `correlationId`, ISO8601 `ts`) and asserts that specifying `excludeSids` suppresses delivery to the initiating connection.
- Awaits the connection automatically; failure to handshake surfaces as `Error('Not connected')`.

**Contract**:
- MUST honor `excludeSids` only
- MUST surface `Error('Not connected')` only when the underlying handshake cannot be established (for example, unauthenticated session)

---

**Contract**:
- MUST return array of per-connection results `{ sid, correlationId, results }`
- MUST use standardized error objects for failures
- MUST support configurable timeout and correlationId

---

## Event Subscription (Server → Client)

### `on()`

**Purpose**: Subscribe to events from server

**Signature**:
```javascript
on(
  eventType: string,
  callback: (envelope: {
    handlerId: string,
    eventId: string,
    correlationId: string,
    ts: string,
    data: object,
  }) => void
): void
```

**Parameters**:
- `eventType`: Event type identifier to listen for
- `callback`: Function called when event received

**Behavior**:
- Registers callback for specified event type
- Multiple callbacks allowed per event type
- Callbacks invoked in registration order
- Subscription persists across reconnections
- Automatically connects if not connected (lazy init)
- Callback receives the standardized server envelope `{ handlerId, eventId, correlationId, ts, data }` where `eventId` is UUIDv4 and `ts` is ISO8601 UTC with millisecond precision. Existing consumers continue to read their payload from the `data` field.

**Example**:
```javascript
// Subscribe to notifications
websocket.on('notification', ({ data, correlationId }) => {
    console.log('Notification:', data.message, 'Correlation:', correlationId);
    showToast(data.message, data.level);
});

// Subscribe to data updates
websocket.on('data_update', ({ data, correlationId }) => {
    console.log('Data updated:', data.entity, 'Correlation:', correlationId);
    updateUI(data);
});
```

**Alpine.js Integration**:
```javascript
function myComponent() {
    return {
        notifications: [],

        init() {
            // Subscribe in component init
            websocket.on('notification', ({ data, correlationId }) => {
                this.notifications.push({
                    ...data,
                    correlationId,
                });
            });
        }
    }
}
```

**Contract**:
- MUST allow multiple subscriptions per event type
- MUST preserve subscriptions across reconnections
- MUST call callbacks in registration order
- MUST automatically connect if not connected
- SHOULD handle callback exceptions (log, don't break other callbacks)

---

### `off()`

**Purpose**: Unsubscribe from events

**Signature**:
```javascript
off(eventType: string, callback?: (data: object) => void): void
```

**Parameters**:
- `eventType`: Event type to unsubscribe from
- `callback`: Optional specific callback to remove (if omitted, removes all callbacks for event type)

**Behavior**:
- Removes specified callback for event type
- If no callback specified, removes ALL callbacks for event type
- No-op if event type not subscribed or callback not found

**Example**:
```javascript
// Remove specific callback
const handler = (data) => console.log(data);
websocket.on('notification', handler);
websocket.off('notification', handler);  // Remove specific handler

// Remove all callbacks for event type
websocket.off('notification');  // Remove all notification handlers
```

**Alpine.js Component Cleanup**:
```javascript
function myComponent() {
    return {
        notificationHandler: null,

        init() {
            this.notificationHandler = (data) => {
                this.notifications.push(data);
            };
            websocket.on('notification', this.notificationHandler);
        },

        destroy() {
            // Cleanup subscription
            if (this.notificationHandler) {
                websocket.off('notification', this.notificationHandler);
            }
        }
    }
}
```

**Contract**:
- MUST remove specified callback if provided
- MUST remove all callbacks if no callback specified
- MUST NOT throw if event type or callback not found
- MUST NOT affect other event type subscriptions

---

## Event Handlers (Lifecycle Hooks)

### `onConnect()`

**Purpose**: Register callback for connection events

**Signature**:
```javascript
onConnect(callback: () => void): void
```

**Behavior**:
- Callback invoked when connection established
- Invoked on initial connection and reconnections
- Multiple callbacks allowed

**Example**:
```javascript
websocket.onConnect(() => {
    console.log('Connected to WebSocket server');
    showStatus('Connected', 'success');
});
```

---

### `onDisconnect()`

**Purpose**: Register callback for disconnection events

**Signature**:
```javascript
onDisconnect(callback: (reason: string) => void): void
```

**Parameters**:
- `reason`: Disconnection reason (e.g., "transport close", "ping timeout")

**Behavior**:
- Callback invoked when connection lost
- Multiple callbacks allowed

**Example**:
```javascript
websocket.onDisconnect((reason) => {
    console.warn('Disconnected:', reason);
    showStatus('Disconnected', 'warning');
});
```

---

### `onError()`

**Purpose**: Register callback for error events

**Signature**:
```javascript
onError(callback: (error: Error) => void): void
```

**Behavior**:
- Callback invoked on connection errors, send failures, etc.
- Multiple callbacks allowed

**Example**:
```javascript
websocket.onError((error) => {
    console.error('WebSocket error:', error);
    showToast(error.message, 'error');
});
```

---

## Utility Methods

### `getCsrfToken()`

**Purpose**: Internal method to retrieve CSRF token (mirrors `api.js`)

**Signature**:
```javascript
getCsrfToken(): string
```

**Behavior**:
- Reads CSRF token from cookie
- Cookie name: `csrf_token_{runtime.id}`
- Returns empty string if cookie not found

**Contract**:
- MUST read from correct cookie name
- MUST match existing `api.js` implementation

---

## Connection State Events

### Built-in Events

These events are automatically handled by the client:

| Event | Trigger | Callback Signature |
|-------|---------|-------------------|
| `connect` | Connection established | `() => void` |
| `disconnect` | Connection lost | `(reason: string) => void` |
| `error` | Connection or send error | `(error: Error) => void` |
| `reconnect_attempt` | Attempting reconnection | `(attemptNumber: number) => void` |
| `reconnect` | Reconnection successful | `(attemptNumber: number) => void` |
| `reconnect_failed` | Reconnection failed | `() => void` |

**Example**:
```javascript
websocket.socket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Reconnection attempt ${attemptNumber}`);
});
```

---

## Error Handling Patterns

### Connection Errors

```javascript
websocket.onError((error) => {
    if (error.message.includes('authentication')) {
        // Redirect to login
        window.location.href = '/login';
    } else {
        // Show error toast
        showToast(error.message, 'error');
    }
});
```

### Send Errors

```javascript
try {
    websocket.emit('notification', data);
} catch (error) {
    console.error('Failed to send notification:', error);
    // Fall back to HTTP API
    await callJsonApi('/notify', data);
}
```

### Request Timeout

```javascript
try {
    const { results } = await websocket.request(
        'query_data',
        { query },
        { timeoutMs: 5_000 }
    );
    handleResponse(results);
} catch (error) {
    if (error.message === 'Request timeout') {
        showToast('Request timed out, please try again', 'warning');
    } else {
        showToast(error.message, 'error');
    }
}
```

---

## Alpine.js Integration Patterns

### Simple Notification Component

```javascript
// Component subscribing to events
function notificationComponent() {
    return {
        notifications: [],

        init() {
            websocket.on('notification', ({ data, correlationId }) => {
                this.notifications.push({
                    message: data.message,
                    level: data.level,
                    timestamp: new Date(),
                    correlationId,
                });
            });
        }
    }
}
```

### Interactive Data Component

```javascript
// Component sending and receiving events
function dataComponent() {
    return {
        data: [],
        loading: false,

        async init() {
            // Subscribe to updates
            websocket.on('data_update', (update) => {
                this.applyUpdate(update);
            });

            // Load initial data
            await this.loadData();
        },

        async loadData() {
            this.loading = true;
            try {
                const { results } = await websocket.request('query_data', {
                    query: 'all_items',
                    limit: 100
                });
                this.data = results;
            } catch (error) {
                console.error('Failed to load data:', error);
            } finally {
                this.loading = false;
            }
        },

        applyUpdate(update) {
            // Update local data based on server update
            const index = this.data.findIndex(item => item.id === update.data.id);
            if (update.operation === 'update' && index !== -1) {
                this.data[index] = update.data;
            } else if (update.operation === 'create') {
                this.data.push(update.data);
            } else if (update.operation === 'delete' && index !== -1) {
                this.data.splice(index, 1);
            }
        }
    }
}
```

---

## Helper Utilities (Developer Ergonomics)

To prevent hand-crafted envelopes or filter payloads, the module MUST expose helper utilities alongside the `websocket` singleton.

### `createCorrelationId()`

**Signature**:
```javascript
createCorrelationId(prefix?: string): string
```

**Contract**:
- MUST return a cryptographically strong correlation identifier (UUIDv4 or equivalent) when `prefix` omitted.
- MUST allow optional prefixing (e.g., `job-`) while guaranteeing uniqueness by appending a UUID component.

### `normalizeProducerOptions()`

**Signature**:
```javascript
normalizeProducerOptions(options: {
  includeHandlers?: string[] | string,
  excludeHandlers?: string[] | string,
  excludeSids?: string[] | string,
  correlationId?: string,
}): {
  includeHandlers?: string[],
  excludeHandlers?: string[],
  excludeSids?: string[],
  correlationId?: string,
}
```

**Contract**:
- MUST deduplicate, trim, and validate handler/SID identifiers and correlation IDs.
- MUST throw descriptive errors when unsupported combinations are provided (e.g., both include/exclude handlers for a request).
- MUST be reused internally by `emit`, `broadcast`, `request`, and `requestAll` so validation rules stay centralised.

### `validateServerEnvelope()`

**Signature**:
```javascript
validateServerEnvelope(envelope: unknown): ServerDeliveryEnvelope
```

**Contract**:
- MUST verify required fields (`handlerId`, `eventId`, `correlationId`, `ts`, `data`) and throw if missing or malformed.
- MUST be used by `websocket.on()` before invoking subscriber callbacks so downstream code always receives validated envelopes.
- MAY clone/freeze the returned object to discourage accidental mutation.

### Usage Expectations
- Developer harness and documentation examples MUST rely on these helpers instead of constructing envelopes/options manually.
- Helper implementations MUST surface meaningful error messages to speed up debugging for feature authors.
- `websocket.debugLog()` MUST remain silent outside development mode; the CSRF preflight response updates the `runtimeInfo.isDevelopment` flag and the developer harness asserts the gating during its automatic validation sequence.

---

## Complete Example

```javascript
// Import WebSocket client
import { websocket } from '/js/websocket.js';

// Alpine.js component using WebSocket
function chatComponent() {
    return {
        messages: [],
        inputMessage: '',
        connectionStatus: 'connecting',

        async init() {
            // Setup connection callbacks
            websocket.onConnect(() => {
                this.connectionStatus = 'connected';
                console.log('Connected to chat');
            });

            websocket.onDisconnect((reason) => {
                this.connectionStatus = 'disconnected';
                console.warn('Disconnected from chat:', reason);
            });

            websocket.onError((error) => {
                console.error('Chat error:', error);
                showToast(error.message, 'error');
            });

            // Subscribe to chat messages
            websocket.on('chat_message', (data) => {
                this.messages.push({
                    text: data.message,
                    sender: data.sender,
                    timestamp: data.timestamp
                });
            });

            // Subscribe to typing indicators
            websocket.on('user_typing', (data) => {
                this.showTypingIndicator(data.user);
            });

            // Optional: await the handshake before allowing the chat UI to proceed
            try {
                await websocket.connect();
            } catch (error) {
                console.error('Failed to connect:', error);
                showToast('Failed to connect to chat', 'error');
            }
        },

        sendMessage() {
            if (!this.inputMessage.trim()) return;

            try {
                // Send fire-and-forget message
                websocket.emit('send_message', {
                    message: this.inputMessage,
                    timestamp: new Date().toISOString()
                });

                this.inputMessage = '';
            } catch (error) {
                console.error('Failed to send message:', error);
                showToast('Failed to send message', 'error');
            }
        },

        showTypingIndicator(user) {
            // Show "User is typing..." indicator
        }
    }
}
```

---

## Testing Contract

### Unit Test Requirements

**Mock WebSocket**:
```javascript
// Mock Socket.IO for unit tests
const mockSocket = {
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
    connected: true
};

// Inject mock into WebSocketClient
websocket.socket = mockSocket;
```

Note: The repository currently does not define a standard frontend unit test runner. The above examples are illustrative; adapt to the project's chosen JS test tooling or verify via browser/manual tests.

**Test Connection**:
```javascript
test('connect establishes WebSocket connection', async () => {
    await websocket.connect();
    expect(websocket.isConnected()).toBe(true);
});
```

**Test Event Subscription (envelope)**:
```javascript
test('on registers event callback', () => {
    const callback = jest.fn();
    websocket.on('test_event', callback);

    // Simulate event envelope delivery
    websocket.socket.emit('test_event', { handlerId: 'm.C', eventId: 'uuid', ts: '2025-10-28T00:00:00.000Z', data: { foo: 'bar' } });

    expect(callback).toHaveBeenCalledWith({ handlerId: 'm.C', eventId: 'uuid', ts: expect.any(String), data: { foo: 'bar' } });
});
```

---

## Summary

**Connection**: Auto-asserted connection (bootstrap + producer guard), automatic reconnection, CSRF authentication
**Sending**: `emit()` for fire-and-forget, `request()` for request-response
**Receiving**: `on()` to subscribe, `off()` to unsubscribe
**Lifecycle**: `onConnect()`, `onDisconnect()`, `onError()` hooks
**Integration**: Seamless Alpine.js component integration
**Error Handling**: Comprehensive error callbacks and Promise rejection
**Testing**: Mock-friendly design for unit testing

**Next Contract**: [Security Contract](./security-contract.md)
