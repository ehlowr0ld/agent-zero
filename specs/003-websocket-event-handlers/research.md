# Research: WebSocket Event Handlers

**Feature**: WebSocket Event Handlers
**Branch**: `003-websocket-event-handlers`
**Date**: 2025-10-16
**Phase**: 0 - Technical Research

## Research Objectives

This research phase explores Flask-SocketIO integration patterns, existing ApiHandler architecture, and frontend WebSocket client patterns to ensure the WebSocket infrastructure mirrors established patterns and integrates seamlessly with the Agent Zero codebase.

## 1. ASGI Integration with python-socketio + uvicorn

### Decision: Use python-socketio.AsyncServer (async_mode='asgi') wrapped in socketio.ASGIApp, served by uvicorn (programmatic from run_ui.py)

**Research Findings**:
- Agent Zero uses Flask 3.0.3; we will keep Flask app for routes and mount it under ASGI.
- python-socketio AsyncServer provides asyncio-native Socket.IO server.
- ASGIApp composes Socket.IO with other ASGI/WSGI apps; Flask is mounted via WSGI-to-ASGI adapter.
- Uvicorn will serve the combined app; access-log disabled, error-only logs preserved.

**Integration Pattern**:
```python
import socketio
from uvicorn import Config, Server
from asgiref.wsgi import WsgiToAsgi

# Flask app created as today
flask_app = create_flask_app()

# ASGI Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    max_http_buffer_size=50 * 1024 * 1024,
)

# Mount Flask (WSGI) under ASGI
wsgi_asgi = WsgiToAsgi(flask_app)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=wsgi_asgi)

# Programmatic uvicorn
server = Server(Config(app=asgi_app, host='0.0.0.0', port=5000, access_log=False))
# await server.serve()
```

**Async Handler Support**:
python-socketio AsyncServer supports async event handlers:
```python
@sio.event
async def event_name(data):
    # Async operations allowed
    await some_async_function()
    return {'status': 'success'}
```

or with explicit names:
```python
@sio.on('query_data')
async def handle_event(data):
    # Async operations allowed
    await some_async_function()
    return {'status': 'success'}
```

**Rationale**:
- ASGI-native; pure asyncio discipline (Principle IV)
- Same-origin (HTTP+WS on one host:port)
- Configurable 50MB buffer cap via engine.io
- Compatible with existing Flask app structure via WSGI-to-ASGI

**Alternatives Considered**:
- **Flask-SocketIO**: legacy integration; replaced by AsyncServer for ASGI-native runtime
- **eventlet/gevent**: introduce monkey-patching; not chosen
- **Separate WS service**: unnecessary; same-origin preferred

**Why Chosen**: Async-native, clear ownership of event loop, programmatic uvicorn control, minimal app-level change.

---

## 2. ApiHandler Architecture Patterns

### Decision: Mirror ApiHandler base class pattern exactly

**Research Findings** (from `python/helpers/api.py`):

**ApiHandler Base Class Structure**:
```python
class ApiHandler:
    def __init__(self, app: Flask, lock: threading.Lock):
        self.app = app
        self.lock = lock

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]  # Default methods

    @classmethod
    def requires_auth(cls) -> bool:
        return True  # Default requires authentication

    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()  # CSRF defaults to auth requirement

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        """Override this method in subclasses"""
        raise NotImplementedError

    async def handle_request(self, request: Request) -> Response:
        """Wrapper that calls process() and handles errors"""
        # Input parsing, error handling, response formatting
        # Not shown in detail - implementation handles the boilerplate
```

**Handler Registration Pattern** (from `run_ui.py`):
```python
# Auto-discover handlers
handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)

# Register each handler
for handler in handlers:
    instance = handler(app, lock)
    # Apply decorators based on class methods
    if handler.requires_auth():
        handler_wrap = requires_auth(handler_wrap)
    if handler.requires_csrf():
        handler_wrap = csrf_protect(handler_wrap)
    # Register route
    app.add_url_rule(f"/{name}", handler_wrap, methods=handler.get_methods())
```

**Mirror Pattern for WebSocket**:
```python
class WebSocketHandler:
    def __init__(self, socketio: SocketIO, lock: threading.Lock):
        self.socketio = socketio
        self.lock = lock
        self.log = None  # Initialized in before_execution()

    @classmethod
    def get_event_types(cls) -> list[str]:
        """Event types this handler subscribes to"""
        raise NotImplementedError

    @classmethod
    def requires_auth(cls) -> bool:
        return True  # Default requires authentication

    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()  # Mirror ApiHandler pattern

    async def process_event(self, event_type: str, data: dict, sid: str) -> dict | None:
        from python.helpers.print_style import PrintStyle
        """Override in subclasses - return dict for response, None for no response"""
        raise NotImplementedError

    async def on_connect(self, sid: str):
        """Called when client connects - override to customize"""
        pass

    async def on_disconnect(self, sid: str):
        """Called when client disconnects - override to customize"""
        pass
```

**Rationale**: Exact mirror of ApiHandler ensures consistency, developer familiarity, and constitutional compliance (Principle VII - Architectural Boundaries)

---

## 3. Existing Authentication and Session Mechanisms

### Decision: Reuse Flask session at connection time

**Research Findings** (from `run_ui.py`):

**Session Configuration**:
```python
webapp.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
webapp.config.update(
    SESSION_COOKIE_NAME="session_" + runtime.get_runtime_id(),
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(days=1)
)
```

**Authentication Decorator**:
```python
def requires_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_enabled = login.is_auth_enabled()
        if not auth_enabled:
            return await f(*args, **kwargs)

        # Check Flask session
        authenticated = session.get("authenticated", False)
        if not authenticated:
            # Redirect or reject
            return redirect(url_for("serve_login"))

        return await f(*args, **kwargs)
    return decorated
```

**CSRF Protection** (from `run_ui.py`):
```python
@webapp.route("/csrf_token", methods=["GET"])
async def get_csrf_token():
    """Generate and return CSRF token bound to runtime"""
    token = secrets.token_hex(32)
    response = Response(json.dumps({"token": token}))
    response.set_cookie(
        f"csrf_token_{runtime.get_runtime_id()}",
        token,
        httponly=True,
        samesite="Strict"
    )
    return response

def csrf_protect(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        # Validate X-CSRF-Token header against cookie
        # Implementation checks header matches cookie value
        ...
        return await f(*args, **kwargs)
    return decorated
```

**WebSocket Authentication Pattern (Preflight)**:
ASGI connect-time auth; CSRF via preflight POST `/csrf_token` that sets a short‑lived session flag (TTL 120s):
```python
@webapp.route('/csrf_token', methods=['POST'])
async def csrf_token_validate_for_ws():
    # Validate header==cookie and set session['ws_csrf_ok_at']=now()
    # TTL enforced at 120 seconds for WS handshake

@sio.event
async def connect(sid, environ, auth):
    # Validate Flask session via WSGI environ (shared cookies)
    # If requires_csrf(): check session['ws_csrf_ok_at'] within 120s
    return True

# Client optimization: on reconnect_attempt, proactively POST /csrf_token
# to refresh session-bound WS flag before handshake
```

**Rationale**:
- Reuse existing session infrastructure (no reinvention)
- Authentication at connection time only (Constitution Principle XIII)
- CSRF validation follows existing pattern
- Seamless integration with existing authentication flow

---

## 4. Frontend Alpine.js Component Patterns

### Decision: Inline JavaScript module with Alpine.js integration

**Research Findings** (from `webui/js/` and `webui/components/`):

**Existing Frontend Architecture**:
- Alpine.js for reactive components
- Modules loaded via `<script type="module">`
- Components use inline styles and scripts
- State management via `createStore()` from `webui/js/AlpineStore.js`
- API calls via `fetchApi()` and `callJsonApi()` from `webui/js/api.js`

**API Client Pattern** (from `webui/js/api.js`):
```javascript
export async function fetchApi(url, options = {}) {
    // Inject CSRF token
    const csrfToken = getCsrfToken();
    options.headers = {
        ...options.headers,
        'X-CSRF-Token': csrfToken
    };

    // Retry on failure
    const response = await fetch(url, options);
    return response;
}

export async function callJsonApi(endpoint, data) {
    return await fetchApi(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}
```

**WebSocket Client Pattern** (mirroring API client):
```javascript
// webui/js/websocket.js
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.subscriptions = new Map(); // event_type -> [callbacks]
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
    }

    async connect() {
        // Lazy connection - only when first needed
        if (this.connected) return;

        // Get CSRF token (mirror API pattern)
        const csrfToken = getCsrfToken();

        // Connect with authentication
        this.socket = io({
            extraHeaders: {
                'X-CSRF-Token': csrfToken
            },
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: this.reconnectDelay,
            reconnectionDelayMax: this.maxReconnectDelay
        });

        this.setupEventHandlers();
    }

    async emit(eventType, data) {
        // Fire-and-forget pattern
        await this.connect();
        this.socket.emit(eventType, data);
    }

    async request(eventType, data, timeout = 30000) {
        // Request-response pattern
        await this.connect();
        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error('Request timeout'));
            }, timeout);

            this.socket.emit(eventType, data, (response) => {
                clearTimeout(timeoutId);
                resolve(response);
            });
        });
    }

    on(eventType, callback) {
        // Subscribe to server events
        if (!this.subscriptions.has(eventType)) {
            this.subscriptions.set(eventType, []);
            this.socket.on(eventType, (data) => {
                const callbacks = this.subscriptions.get(eventType) || [];
                callbacks.forEach(cb => cb(data));
            });
        }
        this.subscriptions.get(eventType).push(callback);
    }

    off(eventType, callback) {
        // Unsubscribe
        const callbacks = this.subscriptions.get(eventType);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) callbacks.splice(index, 1);
        }
    }
}

// Singleton instance
export const websocket = new WebSocketClient();
```

**Alpine.js Integration**:
```javascript
// Component using WebSocket
<div x-data="notificationComponent()">
    <style>
        .notification { /* inline styles */ }
    </style>

    <div class="notification" x-show="hasNotification">
        <span x-text="message"></span>
    </div>

    <script>
    function notificationComponent() {
        return {
            message: '',
            hasNotification: false,

            init() {
                // Subscribe to WebSocket events
                websocket.connect();
                websocket.on('notification', (data) => {
                    this.message = data.message;
                    this.hasNotification = true;
                });
            }
        }
    }
    </script>
</div>
```

**Rationale**:
- Mirrors existing API client patterns (CSRF injection, error handling)
- Lazy connection (Constitution requirement)
- Inline JavaScript modules (Constitution Principle V)
- Seamless Alpine.js integration
- Fire-and-forget vs request-response patterns clearly differentiated

---

## 5. Socket.IO Protocol and Message Serialization

### Decision: Socket.IO with JSON serialization

**Research Findings**:

**Socket.IO Protocol Features**:
- Automatic reconnection with exponential backoff
- Heartbeat/ping-pong for connection health
- Binary and JSON message support
- Namespace support (not needed for single-user app)
- Room support (deliberately not using - simple broadcast model)
- Acknowledgment callbacks for request-response pattern

**Message Serialization**:
- Default: JSON serialization for all messages
- python-socketio handles serialization automatically
- Event structure: `{event_type: str, data: dict}`

**Event Patterns**:
```python
# Fire-and-forget (server → client)
socketio.emit('notification', {'message': 'Hello'})

# Fire-and-forget (client → server)
@socketio.on('user_action')
async def handle_action(data):
    # Process but don't return response
    pass

# Request-response (client → server → client)
@socketio.on('query_data')
async def handle_query(data):
    result = await fetch_data()
    return {'data': result}  # Sent back to client
```

**Buffering Strategy**:
```python
# Server-side buffer for disconnected clients (100 max per sid, drop-oldest)
class EventBuffer:
    def __init__(self, max_size=100):
        self.buffers = {}  # sid -> deque(maxlen=100)

    def add_event(self, sid, event_type, data):
        if sid not in self.buffers:
            self.buffers[sid] = deque(maxlen=100)
        self.buffers[sid].append({'type': event_type, 'data': data})

    def get_buffered_events(self, sid):
        return list(self.buffers.pop(sid, []))
```

**Rationale**:
- Socket.IO protocol handles complexity (reconnection, heartbeat, fallback)
- JSON serialization simple and debuggable
- Automatic message size handling by protocol
- Event buffering straightforward with in-memory deque

---

## 6. Connection Management and Event Routing

### Decision: Centralized WebSocketManager for connection tracking and routing

**Design Pattern**:
```python
class WebSocketManager:
    """Centralized connection and event routing management"""

    def __init__(self, socketio: SocketIO, lock: threading.Lock):
        self.socketio = socketio
        self.lock = lock
        self.connections = {}  # sid -> ConnectionInfo
        self.handlers = {}     # event_type -> list[WebSocketHandler]
        self.event_buffer = EventBuffer(max_size=100)

    def register_handler(self, handler: WebSocketHandler):
        """Register handler for its event types (multi‑handler supported)"""
        for event_type in handler.get_event_types():
            self.handlers.setdefault(event_type, []).append(handler)

    async def handle_connect(self, sid):
        """Track connection (already authenticated by Socket.IO handler)"""
        # Connection already authenticated by @socketio.on('connect') handler
        # Store ConnectionInfo
        self.connections[sid] = ConnectionInfo(sid, authenticated=True)

        # Deliver buffered events
        buffered = self.event_buffer.get_buffered_events(sid)
        for event in buffered:
            self.socketio.emit(event['type'], event['data'], to=sid)

    async def handle_disconnect(self, sid):
        """Clean up connection"""
        self.connections.pop(sid, None)

    async def route_event(self, event_type, data, sid):
        """Route incoming event to appropriate handlers and aggregate results"""
        handlers = self.handlers.get(event_type, [])
        if not handlers:
            return {'error': f'No handler for event type: {event_type}'}

        results = []
        tasks = []
        for h in handlers:
            tasks.append(h.process_event(event_type, data, sid))

        # Gather without failing fast; errors converted to standardized error objects
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for h, resp in zip(handlers, responses):
            if isinstance(resp, Exception):
                results.append({'handlerId': f'{h.__class__.__module__}.{h.__class__.__name__}', 'ok': False, 'error': {'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}})
            elif resp is None:
                results.append({'handlerId': f'{h.__class__.__module__}.{h.__class__.__name__}', 'ok': True, 'data': {}})
            else:
                results.append({'handlerId': f'{h.__class__.__module__}.{h.__class__.__name__}', 'ok': True, 'data': resp})

        return results

    def broadcast(self, event_type, data, exclude_sid=None):
        """Broadcast to all connections"""
        for sid in self.connections:
            if sid != exclude_sid:
                if self.is_connected(sid):
                    self.socketio.emit(event_type, data, to=sid)
                else:
                    # Buffer for disconnected client
                    self.event_buffer.add_event(sid, event_type, data)

    def emit_to(self, sid, event_type, data):
        """Send event to specific connection"""
        if self.is_connected(sid):
            self.socketio.emit(event_type, data, to=sid)
        else:
            # Buffer for disconnected client
            self.event_buffer.add_event(sid, event_type, data)

    def is_connected(self, sid):
        """Check if connection is active"""
        return sid in self.connections
```

**ConnectionInfo Data Structure**:
```python
@dataclass
class ConnectionInfo:
    sid: str
    authenticated: bool
    connected_at: datetime
    user_agent: str = ""
    ip_address: str = ""
```

**Rationale**:
- Centralized tracking simplifies connection management
- Event routing isolated from handlers (separation of concerns)
- Buffering logic encapsulated in one place
- Thread-safe with existing lock mechanism
- Mirrors existing architectural patterns (manager pattern used elsewhere)

---

## 7. Handler Auto-Discovery Mechanism

### Decision: Reuse existing `load_classes_from_folder()` pattern

**Research Findings** (from `python/helpers/extract_tools.py`):
```python
def load_classes_from_folder(folder: str, pattern: str, base_class: type):
    """Load all classes inheriting from base_class in folder matching pattern"""
    classes = []
    folder_path = files.get_abs_path(folder)

    for file in glob.glob(os.path.join(folder_path, pattern)):
        module_name = os.path.splitext(os.path.basename(file))[0]
        spec = importlib.util.spec_from_file_location(module_name, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, base_class) and obj != base_class:
                classes.append(obj)

    return classes
```

**Handler Discovery Pattern**:
```python
# In run_ui.py or websocket initialization
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.websocket import WebSocketHandler

# Auto-discover WebSocket handlers
handlers = load_classes_from_folder(
    "python/websocket_handlers",
    "*.py",
    WebSocketHandler
)

# Register each handler
for handler_class in handlers:
    handler = handler_class(socketio, lock)
    websocket_manager.register_handler(handler)
```

**Rationale**:
- Reuse proven discovery mechanism (DRY principle)
- Automatic handler registration (no manual imports)
- Mirrors ApiHandler discovery pattern
- Simple to add new handlers (just create file in directory)

---

## Research Summary

### Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Backend Framework** | python-socketio AsyncServer + uvicorn | ASGI-native, asyncio, programmatic server |
| **Base Class Pattern** | Mirror ApiHandler exactly | Consistency, familiarity, constitutional compliance |
| **Authentication** | Flask session at connection time | Reuse existing infrastructure, no per-event auth |
| **CSRF Protection** | Connection-time validation | Follow ApiHandler pattern, no per-event checks |
| **Frontend Client** | Inline JavaScript module | Mirror API client patterns, Alpine.js integration |
| **Message Protocol** | Socket.IO with JSON | Automatic reconnection, simple serialization |
| **Connection Management** | Centralized WebSocketManager | Track connections, route events, buffer messages |
| **Handler Discovery** | Reuse `load_classes_from_folder()` | Proven pattern, automatic registration |
| **Event Buffering** | In-memory deque (100 max) | Simple, effective, no persistence needed |
| **Logging** | PrintStyle only | Constitutional requirement (Principle XI) |

### Uvicorn Runtime & Scaling
- Default single worker to preserve in-memory state.
- If multiple workers are configured, document requirement to use a `python-socketio` message queue (e.g., Redis) for cross-worker broadcasts.
- Access log disabled to keep logs at error level only.

### Integration Approach

1. **Backend Integration**:
   - Initialize Flask-SocketIO in `run_ui.py` with eventlet mode
   - Create `python/helpers/websocket.py` (base classes)
   - Create `python/helpers/websocket_manager.py` (connection management)
   - Create `python/websocket_handlers/` directory (handlers auto-discovered)
   - Register handlers using existing discovery mechanism

2. **Frontend Integration**:
   - Create `webui/js/websocket.js` (client library)
   - Export singleton `websocket` instance
   - Mirror `api.js` patterns (CSRF, error handling, lazy connection)
   - Components import and use `websocket.connect()`, `websocket.on()`, etc.

3. **Security Integration**:
   - Reuse Flask session for authentication
   - Reuse CSRF token infrastructure
   - Validate at connection time only
   - No new security systems needed

4. **Testing Integration**:
   - Use pytest with pytest-asyncio for async tests
   - Test handler discovery and registration
   - Test connection authentication and lifecycle
   - Test event routing and buffering
   - Test frontend client library

### No Further Clarifications Needed

All technical unknowns resolved. Ready to proceed to Phase 1 (Design & Contracts).

---

**Phase 0 Complete**: ✅ All research objectives met
**Next Phase**: Phase 1 - Design & Contracts (data-model.md, contracts/, quickstart.md)

---

## Clarifications Consolidation (2025-10-28)

### Decisions
- Server→client deliveries always use envelope `{ handlerId, eventId, ts, data }` (UUIDv4, ISO8601 ms). Application-level payload wrapper; transport unchanged.
- Timeout semantics unified to milliseconds with default `0` (unlimited) for `request`/`requestAll` on both client and server.
- Filtering semantics (frontend→server):
  - `request`: `includeHandlers` only
  - `requestAll`: `excludeHandlers` only
  - `emit`: `includeHandlers` only
  - `broadcast`: `excludeSids` only (no `includeSids`)
- Aggregated `request_all`: include each targeted `sid`; if no handlers or connection error, return standardized error object for that `sid`.
- Session hooks: maintain special `allUsers` bucket; provide `get_sids_for_user(user=null)` (arg ignored for now) and `get_user_for_sid(sid)`.

### Rationale
- Envelope provides provenance and correlation without breaking existing consumers (payload under `data`).
- `0` ms default prevents premature failures during long operations; explicit timeouts remain supported.
- Asymmetric filter options reduce ambiguity and design complexity while covering core use cases.
- Standardized aggregator errors ensure consistent client handling across per‑sid results.
- Session hooks document future multi‑tenant readiness without changing single‑user behavior.
