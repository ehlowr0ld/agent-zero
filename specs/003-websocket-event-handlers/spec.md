# Feature Specification: WebSocket Event Handlers

**Feature Branch**: `003-websocket-event-handlers`
**Created**: 2025-10-09
**Status**: Draft
**Input**: User description: "WebSocket Event Handlers: Implement event handler infrastructure for bidirectional real-time communication following existing REST API handler patterns."

## Terminology

**Event Type**: A string identifier used to route WebSocket events to the appropriate handler (e.g., "notification", "data_update"). This specification uses "event type" consistently throughout.

**Fire-and-Forget Event**: A one-way event notification sent via emit/broadcast methods that requires no acknowledgment or response from the receiver. Used for notifications and state updates. *Note: This specification uses "fire-and-forget" (hyphenated) in prose and documentation. In code, the enum constant is `FIRE_AND_FORGET` (uppercase) with value `"fire_and_forget"` (snake_case), following Python naming conventions.*

**Request-Response Event**: A two-way communication pattern sent via the request() method where the sender awaits a response from the receiver. The receiver can include payload data in the response. Used for queries and synchronous operations.

## Critical Warnings - Lessons from Failed Planning Attempt

**DO NOT REPEAT THESE MISTAKES**:

1. ❌ **NO Room Management** - Don't introduce room concepts, room joining/leaving, or room-based broadcasting. Use simple broadcast-by-default with optional specific-connection targeting. This is not a collaborative multi-user chat system.

2. ❌ **NO Per-Event Authentication** - Authentication happens at connection time ONLY. Don't add per-event auth checks, per-event authorization, or per-event security validation. Follow existing ApiHandler pattern exactly.

3. ❌ **NO Feature-Specific Examples** - This is infrastructure specification. Don't include examples like `agent_output`, `agent_status`, `agent_thinking`, `command_execution`, etc. Use generic examples like `notification`, `data_update`, `status_change`.

4. ❌ **NO Multi-Tenancy Patterns** - This is a single-user application. Don't add user IDs, user-specific rooms, per-user authorization, resource quotas, tenant management, or any enterprise patterns.

5. ❌ **NO Over-Engineering** - KISS principle applies. This is a WebSocket extension of existing app, not a new messaging platform. Reuse existing patterns (ApiHandler security, session management, error handling). Don't reinvent infrastructure.

6. ❌ **NO Authorization Layer** - Authentication is binary (logged in or not). Don't add permissions, roles, access control lists, resource-level authorization, or elevated privileges concepts.

7. ❌ **Infrastructure ONLY** - Specification describes WebSocket infrastructure capabilities (bidirectional events, broadcast patterns, reconnection, buffering). It does NOT prescribe what application features will use it.

**REMEMBER**: Simple broadcast model, connection-time auth, single-user context, infrastructure-level only, follow existing patterns.

## Clarifications

### Session 2025-10-09

- Q: Should the WebSocket infrastructure coexist with the existing polling mechanism, or should it eventually replace it? → A: Both polling and WebSocket will coexist permanently as first-class citizens. Existing features will not be migrated at this time. WebSocket is needed for new future features. Future features will choose between polling and WebSocket based on requirements.
- Q: Are there specific constraints on WebSocket message payload sizes that should be enforced? → A: Yes. Enforce a 50MB single-event hard cap across client and server; recommend chunking at ≥10MB and prefer HTTP for large/binary transfers. Programmatic APIs continue to mirror REST patterns.
- Q: Should WebSocket connections be established eagerly or lazily? → A: Lazy initialization on demand when developers first use WebSocket APIs. Connection should be established transparently when first needed, analogous to REST API infrastructure. Seamless integration without requiring explicit connection management from developers.
- Q: How should WebSocket events be named and routed to handlers? → A: Event names declared by handlers. Handlers implement a standard processing method following existing REST API patterns for consistency.
- Q: How should the infrastructure support bidirectional communication (client→server and server→client)? → A: Bidirectional handlers can both receive events from clients and push events to clients. Single handler can subscribe to multiple incoming event types and emit multiple different event types. Event type is an explicit parameter in both frontend and backend handling. Frontend provides convenience methods to subscribe to events from backend.
- Q: How should the system handle events during connection loss and reconnection? → A: Server-side buffer for server-sent events - server buffers/queues events for disconnected clients and delivers them upon reconnection. For client-sent events, the client API should trigger errors that can be handled in the UI when unable to send to the server, allowing applications to implement appropriate retry or fallback logic.

### Session 2025-10-16

- Q: What does "multiple users" mean in User Story 5 given Agent Zero is a single-user application? → A: Multiple browser tabs/windows of the same authenticated user (single-user, multiple viewports)
- Q: How should rooms be identified for organizing WebSocket connections? → A: Remove room complexity entirely. Simple broadcast model: events delivered to all user's tabs by default, with optional specific-connection targeting when handler needs it. KISS principle - this is WebSocket extension of existing app, not collaborative multi-user system.
- Q: Should CSRF protection for WebSocket be mandatory or optional? → A: Mandatory whenever authentication is required (i.e., when `requires_auth()==True`). No opt‑out. CSRF is validated via HTTP preflight POST to `/csrf_token` (header+cookie), which sets a short‑lived session flag that the WS handshake checks; on `reconnect_attempt`, the client proactively POSTs `/csrf_token` again before retrying the handshake.
- Q: Should event acknowledgments be automatic or explicit? → A: Two communication patterns differentiated by method name: (1) Fire-and-forget events using emit/broadcast methods (no acknowledgment), (2) Request-response pattern using the request() method that returns response payload from receiver. Request pattern implies synchronous delivery where sender awaits response with optional payload from receiver.
- Q: What should the server-side event buffer size limit be per disconnected client? → A: Small fixed limit of 100 events, drop oldest on overflow. Only fire-and-forget emit events are buffered during disconnection. Request-response events return errors immediately since they require synchronous acknowledgment.

### Session 2025-10-28

- Q: What exact lifetime should the short‑lived session flag (set by POST `/csrf_token` and checked during WS connect/reconnect) have? → A: 120 seconds
- Q: Socket.IO transport policy? → A: Use python‑socketio defaults (Engine.IO transports: polling + websocket enabled; pingInterval 25000 ms; pingTimeout 20000 ms). No forced WebSocket‑only mode.
- Q: Access‑log policy under uvicorn? → A: Error‑level only
- Q: Startup behavior for `server_restart` event? → A: Broadcast on startup by default

- Q: Server→client metadata envelope policy? → A: Always wrap with `{ handlerId, eventId, ts, data }` (application-level payload to subscribers; not a transport/frame change)
- Q: Correlation across flows? → A: A `correlationId` is carried in both directions for all flows. If the emitter omits it, the receiver generates one and echoes it back in subsequent related messages.
- Q: Development-only logging policy? → A: Debug logs are emitted only in development mode on both backend (PrintStyle.debug) and frontend (console). Logs should include `eventId` and/or `correlationId` where available, with prudent placement to avoid noise.

- Q: Default timeout + units for `request`/`requestAll` when omitted? → A: `0` ms (unlimited) default on both client and server; all timeout parameters use milliseconds
- Q: Filter parameters per operation (frontend→server)? → A: `request`: `includeHandlers` only; `requestAll`: `excludeHandlers` only; no mixed include+exclude
- Q: `request_all` behavior when a SID has no matching handlers or a connection error? → A: Always include each targeted SID with a standardized error object in results for that SID
- Q: Broadcast SID filters now? → A: Support only `excludeSids` (no `includeSids` yet); document future consideration separately
- Q: Session tracking key and helpers? → A: Single-user bucket `allUsers`; track SIDs internally; provide `get_sids_for_user(user=null)` (argument currently ignored; placeholder for future multi-tenant)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - WebSocket Infrastructure Foundation (Priority: P1)

The system provides a complete, production-ready WebSocket infrastructure that enables developers to build future real-time features. The infrastructure includes secure authentication, bidirectional event handling, automatic reconnection, and seamless integration with the existing application architecture.

**Why this priority**: This is the foundational infrastructure that all future WebSocket-based features will depend on. Without a robust, secure, and well-architected foundation, future features would be built on unstable ground. This establishes the core capability while ensuring security, reliability, and developer productivity from day one.

**Independent Test**: Can be fully tested by creating a simple test handler, establishing WebSocket connections from multiple clients, sending bidirectional events, simulating disconnections, and verifying authentication enforcement. Delivers immediate value by providing production-ready infrastructure for any future real-time feature.

**Acceptance Scenarios**:

1. **Given** the WebSocket infrastructure is deployed, **When** a developer creates a WebSocket event handler, **Then** the handler is automatically discovered, registered, and available for client connections at server startup
2. **Given** a client application attempts to establish a WebSocket connection, **When** the connection request is made, **Then** the system authenticates using existing session credentials and either accepts or rejects the connection based on authentication status
3. **Given** an authenticated WebSocket connection is established, **When** the client sends an event with explicit event type, **Then** the event is securely routed to the appropriate handler based on event type and authentication
4. **Given** a WebSocket event handler processes an incoming event, **When** the handler needs to send data to client(s), **Then** the handler sends events with explicit event type parameters and events are delivered immediately
5. **Given** an active WebSocket connection, **When** the network connection is temporarily lost, **Then** the system automatically attempts reconnection with exponential backoff, buffers server-sent events during disconnection, and delivers buffered events upon successful reconnection
6. **Given** multiple browser tabs are connected via WebSocket, **When** a handler broadcasts an event, **Then** all connected tabs receive the event by default, and handlers can optionally target specific connections when needed
7. **Given** a client needs to query data from the server, **When** the client sends a request-response event using request() method, **Then** the handler(s) process the request and the client receives an array of per‑handler results `{ handlerId, ok, data|error }`, enabling synchronous communication patterns with multi‑handler aggregation

---

### User Story 2 - Secure WebSocket Authentication (Priority: P1)

Users authenticate their WebSocket connections using the same security mechanisms as REST API calls. Unauthorized users cannot establish WebSocket connections or receive events. Sessions remain consistent between HTTP and WebSocket communication.

**Why this priority**: Security is non-negotiable and must be built into the foundation. Without proper authentication from the start, the entire WebSocket infrastructure would be vulnerable. This prevents unauthorized access and ensures data privacy.

**Independent Test**: Can be tested independently by attempting to connect without authentication (should fail), connecting with valid session (should succeed), and verifying that only authorized users receive events. Delivers security value immediately.

**Acceptance Scenarios**:

1. **Given** a user is not authenticated, **When** they attempt to establish a WebSocket connection, **Then** the connection is rejected at connection time (before any event exchange)
2. **Given** a user has logged in via HTTP authentication, **When** they establish a WebSocket connection, **Then** the connection uses the same session credentials as their HTTP session
3. **Given** an authenticated user with an active WebSocket connection, **When** their session expires, **Then** the WebSocket connection is detected as expired and gracefully closed by the server
4. **Given** a WebSocket event handler requires authentication, **When** an unauthenticated user attempts to connect, **Then** the connection is rejected before any events can be transmitted
5. **Given** multiple browser tabs are connected via WebSocket, **When** a handler emits an event to a specific connection, **Then** only that specific connection receives the event

---

### User Story 3 - Developer-Friendly Event Handler Framework (Priority: P2)

Developers create new WebSocket event handlers using the same patterns as REST API handlers. Handlers are automatically discovered and registered. Security policies are declaratively configured. Error handling is consistent across all handlers.

**Why this priority**: Developer productivity directly impacts feature velocity. A well-designed framework reduces bugs, accelerates development, and ensures consistency. This priority follows the foundational infrastructure (P1) and enables rapid feature development.

**Independent Test**: Can be tested by creating a new WebSocket event handler class and verifying it's automatically registered and functional. Delivers value by proving the framework is developer-friendly and productive.

**Acceptance Scenarios**:

1. **Given** a developer creates a new WebSocket event handler class, **When** they create the handler, **Then** the handler is automatically discovered and registered at server startup
2. **Given** a developer declares multiple event types, **When** any of those events are received, **Then** the handler is invoked with event type as a parameter
3. **Given** a developer defines authentication requirements in a handler, **When** the handler is invoked, **Then** authentication is automatically enforced without manual checks
4. **Given** a WebSocket event handler needs to push fire-and-forget events to clients, **When** the handler uses emit/broadcast methods with explicit event type, **Then** the event is sent to appropriate client(s) without acknowledgment
5. **Given** a WebSocket event handler needs to respond to a request, **When** the handler processes a request-response event, **Then** the handler returns a response payload that is delivered to the requesting client synchronously
6. **Given** a WebSocket event handler throws an exception, **When** the exception occurs, **Then** the error is caught, logged, and a standardized error response is sent to the client
7. **Given** a developer needs to access the current user's context, **When** they write a handler method, **Then** they can access context information using the same patterns as REST API handlers

---

### User Story 4 - Seamless Frontend Integration (Priority: P2)

Frontend developers use WebSocket connections through a simple, consistent interface that mirrors the existing REST API client. Connection management, reconnection logic, and event subscription are handled transparently. Alpine.js components can easily emit and listen for WebSocket events.

**Why this priority**: Frontend complexity is a common source of bugs in real-time applications. A clean abstraction layer ensures reliable communication and accelerates UI feature development. This builds on the backend foundation (P1) to complete the full-stack capability.

**Independent Test**: Can be tested by creating a simple Alpine.js component that emits a WebSocket event and displays received events. Demonstrates end-to-end functionality without requiring complex application features.

**Acceptance Scenarios**:

1. **Given** a frontend developer needs to send a fire-and-forget WebSocket event, **When** they use the emit method with explicit event type parameter, **Then** the event is transmitted to the server without waiting for acknowledgment
2. **Given** a frontend developer needs to query data from the server, **When** they use the request() method with explicit event type, **Then** the method returns a promise that resolves with an array of per‑handler results `{ handlerId, ok, data|error }` (see contracts/event-schemas.md §Request Result Schema)
3. **Given** an Alpine.js component needs to react to WebSocket events, **When** the component subscribes to specific event types using convenience methods, **Then** the component's callback is invoked with event type and data whenever matching events are received
4. **Given** a frontend component subscribes to multiple event types, **When** any of those event types are sent from the server, **Then** the appropriate callback handler for each event type is invoked
5. **Given** a WebSocket connection is established, **When** the connection drops unexpectedly, **Then** the client automatically attempts reconnection with exponential backoff
6. **Given** a frontend component emits a fire-and-forget event, **When** the connection is unavailable or an error occurs on the server, **Then** the error is propagated to the component's error callback in a consistent format for UI handling
7. **Given** a frontend component sends a request-response event, **When** the connection is unavailable, **Then** the promise is rejected with a connection error
8. **Given** a user navigates between pages in the application, **When** navigation occurs, **Then** the client automatically reconnects without user action and restores subscriptions
9. **Given** the runtime is not in development mode, **When** a user opens the developer settings tab, **Then** the WebSocket developer harness controls are not displayed and cannot be launched

---

### User Story 5 - Event Broadcasting (Priority: P3)

The system supports broadcasting events to all of the user's connected browser tabs by default, with optional targeting to specific connections when needed. Agents can send updates that synchronize state across all tabs or respond to a specific tab only.

**Why this priority**: While foundational WebSocket communication (P1-P2) is essential, broadcast and targeted delivery patterns enable flexible communication strategies. This is important but not critical for initial WebSocket deployment.

**Independent Test**: Can be tested by opening multiple browser tabs, broadcasting an event from a handler, and verifying all tabs receive it. Can also test specific-connection targeting by sending an event to only one tab and verifying others don't receive it.

**Acceptance Scenarios**:

1. **Given** multiple browser tabs are connected via WebSocket, **When** a handler broadcasts an event without specifying a target connection, **Then** all of the user's connected tabs receive the event simultaneously
2. **Given** a browser tab sends an event to the server, **When** the handler needs to reply only to that specific tab, **Then** the handler can target the event to that specific connection and other tabs do not receive it
3. **Given** multiple browser tabs are connected, **When** a handler sends an event to a specific connection identifier, **Then** only the tab with that connection receives the event
4. **Given** a handler needs to send state updates that should be visible across all tabs, **When** the handler broadcasts the event, **Then** all connected tabs receive and display the update
5. **Given** a tab-specific user action (like clicking a button), **When** the handler processes the action, **Then** the handler can choose to broadcast the result to all tabs or reply only to the requesting tab

---

### Edge Cases

- What happens when a WebSocket event handler takes longer than the connection timeout to process? System maintains connection through automatic heartbeats; handlers should emit progress events during long operations for user feedback
- How does the system handle WebSocket connections when the server is deployed behind a load balancer? Deployment configuration must ensure connections stick to same server instance or use shared message infrastructure
- What happens when a user has WebSocket connections from multiple browser tabs? Each connection is independent; handlers can target specific connections or broadcast to all; handlers should handle duplicate actions idempotently
- How should event replies (responses to specific client-sent events) be handled in multi-tab scenarios? Both single-tab replies and broadcast patterns are valid depending on use case; see Open Questions section for research recommendations
- How are WebSocket connections cleaned up when a user closes their browser without properly disconnecting? Server detects disconnection through heartbeat timeout and automatically cleans up resources
- How does the system handle malformed or malicious WebSocket messages? Messages are validated; invalid messages are rejected with error response
- How do developers choose between WebSocket and HTTP polling for new features? Use WebSocket for real-time push notifications and streaming; use polling for periodic status checks and batch updates
- What happens if the server-side buffer for disconnected clients grows too large during extended disconnection? Server enforces 100 event limit per client; oldest fire-and-forget events are dropped with warning logged when limit is reached; request-response events return errors immediately
- How should UI components handle errors when sending WebSocket events fails? Error callbacks provide failure reasons; UI can show user-friendly messages, retry automatically, or fall back to HTTP polling
- How does a handler differentiate between different event types when subscribed to multiple? Event type is passed as a parameter to handler; handler uses conditional logic based on event type
- What happens when a handler emits an event type that no clients are subscribed to? Event is sent but not delivered; no error occurs; this is normal pub/sub behavior
- What happens if a request-response event takes too long to process or handler doesn't respond? Client-side timeout (e.g., 30 seconds default) rejects the promise with timeout error; handlers should process requests quickly or emit progress events for long operations (see contracts/event-schemas.md §Handler Execution Timeouts)
- Can a handler respond to a fire-and-forget emit event? No, emit events are one-way; handlers should not attempt to send responses; use request-response pattern when reply is needed
- Can handlers programmatically disconnect clients (e.g., for policy violations)? No, only client-initiated disconnection and automatic session expiration trigger disconnects; handlers cannot force-disconnect clients

## Requirements *(mandatory)*

### Functional Requirements

#### WebSocket Infrastructure

- **FR-001**: System MUST provide a base class for WebSocket event handlers that defines the handler lifecycle and security configuration
- **FR-002**: System MUST automatically discover and register WebSocket event handlers at server startup
- **FR-003**: System MUST establish WebSocket connections when clients connect to the application
- **FR-004**: System MUST maintain persistent, bidirectional connections between clients and server for real-time communication
- **FR-005**: System MUST gracefully handle WebSocket connection establishment, maintenance, and teardown
- **FR-033**: System MUST operate alongside the existing HTTP polling mechanism without interference, supporting both as permanent first-class communication channels

#### Authentication and Security

- **FR-006**: System MUST authenticate WebSocket connections at connection time using the same session mechanism as REST API requests
- **FR-007**: System MUST enforce authentication requirements defined by each WebSocket event handler class at connection time only (not per-event)
- **FR-008**: System MUST validate CSRF tokens at connection time whenever authentication is required (no opt‑out). Validation occurs via HTTP preflight POST to `/csrf_token` using header+cookie; WS handshake checks the short‑lived session flag. Client proactively refreshes the flag on `reconnect_attempt`. The short‑lived session flag expires in 120 seconds.
- **FR-009**: System MUST detect when session expires and close the WebSocket connection gracefully
- **FR-010**: System MUST reject connection attempts from unauthenticated users when handler requires authentication
- **FR-011**: System MUST log connection authentication failures with appropriate error detail

#### Event Handling

- **FR-012**: System MUST support bidirectional event communication where clients can send events to the server and servers can push events to clients
- **FR-013**: System MUST route incoming WebSocket events to the appropriate event handler based on declared event types
- **FR-014**: System MUST provide event handlers with access to the current user's context and session information
- **FR-015**: System MUST support two communication patterns: (1) Fire-and-forget events via emit/broadcast methods (no acknowledgment), (2) Request-response pattern via request() where sender awaits responses with optional payload from receiver
- **FR-016**: System MUST handle event handler exceptions gracefully and return standardized error responses to clients
- **FR-017**: System MUST support broadcasting events to all of the user's connected tabs by default, with optional targeting to a specific connection when needed
- **FR-036**: WebSocket event handlers MUST implement a standard processing method for incoming events, following existing REST API handler patterns
- **FR-038**: WebSocket event handlers MUST provide standardized methods for sending events from server to clients
- **FR-039**: System MUST allow a single handler to subscribe to multiple incoming event types
- **FR-040**: System MUST allow handlers to emit multiple different event types using explicit event type parameters
- **FR-041**: System MUST pass event type as an explicit parameter to handler processing methods
 - **FR-047**: System MUST support a broadcast request-response aggregation pattern that fans out a request to all active connections and returns an array of per-connection results with standardized error objects and configurable timeout (frontend `requestAll()`)
 - **FR-048**: System MUST allow multiple handlers to register for the same event type; `request()` MUST return an array of per‑handler results, and `requestAll()` MUST return per‑sid arrays of per‑handler results. Error handling MUST be symmetric and standardized across client and server.

#### Connection Management

- **FR-018**: System MUST detect when WebSocket connections are lost and clean up associated resources
- **FR-019**: System MUST support automatic client reconnection with exponential backoff when connections are dropped
- **FR-020**: System MUST buffer server-sent fire-and-forget emit events (up to 100 events per disconnected client, dropping oldest on overflow) and deliver them automatically upon reconnection; request-response events return errors immediately during disconnection (*Buffers expire after 1 hour without reconnection via lazy cleanup. See contracts/event-schemas.md §Buffer Lifecycle*)
- **FR-021**: System MUST send heartbeat/keepalive messages to prevent connection timeouts during long-running operations (*Implementation: Socket.IO default 25s heartbeat interval. See contracts/event-schemas.md §Operational Clarifications*)
- **FR-022**: System MUST support multiple concurrent WebSocket connections from different browser tabs; each connection is independent and handlers can explicitly target specific connections or broadcast to all connections
- **FR-037**: System MUST provide error callbacks in the client JS API when client-sent events cannot be transmitted to the server, enabling UI-level error handling and retry logic
<!-- FR-044 removed (duplicate of FR-020). See FR-020 for buffering requirements. -->
- **FR-045**: System MUST raise `ConnectionNotFoundError` when handlers attempt to emit events to non-existent connections (never existed or expired), allowing proper error handling while buffering events for recently disconnected connections (*See contracts/event-schemas.md §Event Delivery Error Handling*)
- **FR-046**: System SHOULD broadcast `server_restart` fire-and-forget event to all connected clients on server startup by default (configurable to disable), allowing clients to refresh data or show notifications (*See contracts/event-schemas.md §Server Restart Handling*)

#### Frontend Integration

- **FR-023**: System MUST provide a frontend client library for WebSocket communication that mirrors the existing REST API client patterns
- **FR-024**: System MUST support seamless integration with Alpine.js components for event emission and subscription
- **FR-025**: System MUST handle WebSocket connection initialization transparently and lazily when developers first use WebSocket APIs, without requiring explicit connection management
- **FR-026**: System MUST provide clear error messages when WebSocket connections fail or events cannot be processed
- **FR-027**: System MUST maintain WebSocket connections during single-page navigation without requiring re-establishment
- **FR-035**: System MUST NOT establish WebSocket connections for pages or features that do not use WebSocket APIs, conserving server and client resources
- **FR-042**: Frontend WebSocket client MUST provide convenience methods for subscribing to server-sent events with event type as explicit parameter
- **FR-043**: Frontend WebSocket client MUST support subscribing to multiple different event types with separate callback handlers

#### Developer Experience

- **FR-028**: WebSocket event handler classes MUST follow similar patterns to REST API handler classes for consistency
- **FR-029**: System MUST provide declarative security configuration for WebSocket handlers following ApiHandler pattern (requires_auth(), requires_csrf() class methods)
- **FR-030**: System MUST provide access to the same threading lock and application instance as REST API handlers
- **FR-031**: System MUST support async/await patterns in event handler methods for non-blocking operations
- **FR-032**: System MUST provide comprehensive error logging for debugging WebSocket issues
- **FR-034**: System MUST enforce a maximum single-event payload size of 50MB across client and server, with clear errors when exceeded; recommend chunking above 10MB and prefer HTTP for large file transfers
- **FR-049**: Developer-facing WebSocket harness controls MUST only be available when `runtime.is_development()` is true; production runtimes MUST omit the harness settings section and modal entry point

### Key Entities *(include if feature involves data)*

- **WebSocketConnection**: Represents an active WebSocket connection from a client browser tab, including connection identifier, session state (authenticated or not), and connection timestamp
- **WebSocketEvent**: Represents a message transmitted over a WebSocket connection, including event type, payload data, sender connection identifier, and event pattern (fire-and-forget emit or request-response)
- **EventHandler**: A bidirectional server-side component that both receives events from clients and sends events to clients. Handlers can subscribe to multiple event types and send various event types. Authentication is checked at connection time only (not per-event). Handlers can broadcast to all connections or target specific connection identifiers.
- **EventSubscription**: Represents a client's registration to receive specific event types from the server, including event type identifier, callback handler, and optional filters

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Server-sent events are delivered to clients within 100 milliseconds of generation, providing 10-20x improvement in responsiveness compared to polling-based approaches (1-2 seconds)
- **SC-002**: WebSocket connections remain stable for at least 8 hours of continuous usage without requiring reconnection under normal network conditions
- **SC-003**: System successfully handles at least 100 concurrent WebSocket connections (e.g., from the same user's multiple browser tabs across different devices or browser sessions) without degradation in event delivery latency
- **SC-004**: Developers can create and deploy a new bidirectional WebSocket event handler (with both incoming and outgoing event handling) in under 15 minutes using the provided framework and documentation
- **SC-005**: WebSocket authentication failures are prevented at connection time, with 100% of unauthorized connection attempts being rejected before event exchange
- **SC-006**: Frontend components can subscribe to and receive WebSocket events with fewer than 10 lines of code, demonstrating API simplicity
- **SC-007**: WebSocket connections automatically recover within 5 seconds when network connectivity is restored after a temporary disruption, with server-buffered fire-and-forget events (up to 100 per client) delivered without data loss and both client-sent failures and request-response events during disconnection properly reported via error callbacks
- **SC-008**: Event broadcasting to 50 browser tab connections completes within 200 milliseconds, enabling real-time synchronized state across tabs
- **SC-009**: WebSocket-related errors are logged with sufficient detail for developers to diagnose issues within 5 minutes
- **SC-010**: The WebSocket infrastructure integrates with existing session management without requiring changes to authentication logic

## Assumptions *(if applicable)*

1. **Single-User Application**: Agent Zero is a single-user application (one authenticated user at a time) with no multi-tenancy, user database, roles, or per-resource authorization; authentication is binary (logged in or not) via existing session mechanisms
2. **Network Infrastructure**: The application will be deployed in environments that support WebSocket connections (no aggressive proxies or firewalls that block WebSocket protocols)
3. **Browser Compatibility**: Target browsers support WebSocket protocol (all modern browsers released in the last 5 years)
4. **Server Deployment**: The server will run with WebSocket-compatible infrastructure
5. **Existing Architecture**: The current REST API handler framework and authentication mechanisms are stable and won't undergo major changes during WebSocket implementation; WebSocket will follow existing patterns
6. **Threading Model**: The existing threading model and lock mechanism can accommodate WebSocket connections without significant architectural changes
7. **Message Volume**: Typical WebSocket event rates will be under 100 events per second per connection for interactive features
8. **Session Persistence**: Sessions will remain the primary mechanism for user authentication and can be shared between HTTP and WebSocket contexts
9. **Development Patterns**: Developers are familiar with existing REST API handler patterns and can adopt similar patterns for WebSocket handlers
10. **Coexistence with Polling**: The existing HTTP polling mechanism will remain operational and will not be deprecated or migrated; WebSocket and polling will coexist as independent, first-class communication channels for different feature requirements
11. **Message Size Handling**: A 50MB maximum single-event payload is enforced across client and server; for larger transfers use chunking or HTTP
12. **Lazy Connection Model**: WebSocket connections will be established lazily when first needed (when WebSocket APIs are called), not eagerly on every page load; this conserves resources for pages that don't use WebSocket features
13. **Event Naming Pattern**: Event handlers explicitly declare their event names rather than deriving names automatically; this provides explicit control over event routing
14. **Reconnection Strategy**: Server-side buffering for server-sent events ensures reliable delivery after reconnection; client-sent events that fail trigger error callbacks for application-level handling rather than automatic retry
15. **Bidirectional Handler Architecture**: Event handlers provide both incoming event processing and outgoing event sending capabilities; handlers can subscribe to multiple event types and emit multiple different event types with explicit event type parameters

## Dependencies *(if applicable)*

1. **WebSocket Library**: The feature depends on WebSocket support libraries for both server and client
2. **Web Server Infrastructure**: Deployment requires a server that supports WebSocket connections
3. **Existing Authentication System**: WebSocket security builds upon the current session-based authentication and CSRF protection
4. **Frontend API Infrastructure**: WebSocket client will integrate with existing frontend API patterns and Alpine.js state management
5. **Event Loop Compatibility**: WebSocket async operations must be compatible with existing async patterns in the application

## Open Questions / Clarifications Needed *(if applicable)*

### Requires Research During Implementation

**Event Reply Pattern in Multi-Tab Scenarios** (Identified 2025-10-15):
- **Question**: When a client sends an event and handler replies, should the reply go only to the requesting tab or broadcast to all user tabs?
- **Context**: User with multiple browser tabs open; one tab sends event; handler processes and sends response
- **Ambiguity**: Both patterns might be correct depending on use case:
  - **Specific-tab reply**: Request/response pattern (e.g., "fetch data" → response only to requesting tab)
  - **Broadcast reply**: State synchronization pattern (e.g., "update setting" → all tabs need to know)
- **Research Required**: Investigate consistency and correctness of both approaches; define guidelines for developers choosing reply pattern
- **Recommendation**: Research during Phase 0 or early Phase 2; document patterns in developer guide
- **Impact**: Medium - affects handler API patterns and developer guidance; does not block initial implementation (handlers can use either pattern explicitly)

## ASGI Migration Addendum (2025-10-28) — Flask‑SocketIO → ASGI‑native (python‑socketio.AsyncServer + uvicorn)

### Objective
Migrate runtime from Flask‑SocketIO + threading to an ASGI‑native, asyncio‑driven architecture that preserves existing product behavior (sessions, CSRF, handler API, developer harness, frontend client, and tests) while serving the combined app via uvicorn.

### Scope & Constraints
1. Replace Flask‑SocketIO usage with `python‑socketio.AsyncServer` (`async_mode='asgi'`) wrapped in `socketio.ASGIApp`.
2. Serve combined Flask + Socket.IO ASGI app with uvicorn from within `run_ui.py` (programmatic startup; no access‑log noise beyond current logging expectations).
3. Preserve Flask session and CSRF integration: connection‑time auth/CSRF must behave exactly as today.
4. Maintain existing handler API: async `process_event`, multi‑handler aggregation, buffering; ensure it runs on ASGI/asyncio.
5. Keep developer harness, frontend client, and tests working without behavioral regressions.
6. Confirm multi‑tenancy readiness: document concurrency model, scaling guidance, uvicorn worker settings.
7. Introduce required dependencies and runtime changes (requirements, container run image) with minimal footprint.
8. Provide migration guidance for existing tasks/tests (including Quickstart updates).

### Functional Migration Requirements (ASGI)
- **MIG‑001**: The runtime MUST initialize a `python‑socketio.AsyncServer` with `async_mode='asgi'` and mount it via `socketio.ASGIApp` into a single ASGI application that also serves existing Flask routes.
- **MIG‑002**: The application MUST be served by uvicorn started programmatically from `run_ui.py`, honoring existing logging configuration (no access‑log spam; preserve current log format/verbosity expectations).
- **MIG‑003**: Connection‑time authentication MUST remain session‑based and consistent with HTTP; unauthenticated connections are rejected before any event exchange.
- **MIG‑004**: CSRF MUST be validated on connection when `requires_auth()==True`, using the same `/csrf_token` header/cookie preflight and short‑lived session flag semantics. The short‑lived session flag expires in 120 seconds.
- **MIG‑005**: The existing handler API contract (async `process_event`, multi‑handler aggregation results, standardized errors) MUST be preserved without breaking changes.
- **MIG‑006**: Event buffering semantics (up to 100 fire‑and‑forget events per temporarily disconnected connection, drop oldest on overflow) MUST be preserved.
- **MIG‑007**: Frontend client semantics (emit, request, requestAll, subscribe with explicit event types; automatic reconnection; error callbacks) MUST remain unchanged.
- **MIG‑008**: Developer harness entrypoint MUST remain `python run_ui.py`; internal server switch MUST be transparent to developers.
- **MIG‑009**: Tests covering CSRF, connection auth, handler routing, and buffering MUST continue to pass unchanged; only test helpers may be adjusted for ASGI timing if needed.
- **MIG‑010**: The system MUST run fully asyncio‑driven in the event loop; any blocking operations MUST be offloaded to appropriate executors.
- **MIG‑011**: Uvicorn server configuration MUST be documented (host/port, workers guidance, access‑log disablement, lifespan handling) and default to a single worker for in‑memory state consistency.
- **MIG‑012**: Multi‑worker guidance MUST be documented: if more than one worker is used, a shared message queue (e.g., Redis) is required for cross‑worker Socket.IO; otherwise, stick to single worker.
- **MIG‑013**: Docker/runtime images MUST include new dependencies (uvicorn, python‑socketio async stack) and remain minimal.
- **MIG‑014**: Backward compatibility traps MUST be documented (e.g., WSGI‑only middleware assumptions, thread‑local context usage, per‑thread locks) with mitigation steps.
- **MIG‑015**: Quickstart and developer docs MUST be updated to call out the ASGI runtime while keeping the same `python run_ui.py` UX.
- **MIG‑016**: Transport policy uses python‑socketio defaults (no forced WebSocket‑only or polling bans by default).

### Non‑Functional Acceptance Criteria
- **AC‑ASGI‑01**: Launching `python run_ui.py` starts an ASGI uvicorn server; uvicorn access‑log is disabled and logging is error‑only, matching prior noise levels.
- **AC‑ASGI‑02**: All existing REST endpoints function identically; session cookies and CSRF flows are unchanged from a user perspective.
- **AC‑ASGI‑03**: WebSocket tests (auth, CSRF, routing, buffering, reconnection) pass with no behavior changes to public APIs.
- **AC‑ASGI‑04**: Event delivery and latency targets in Success Criteria remain met or improved under load equal to or greater than pre‑migration.
- **AC‑ASGI‑05**: Frontend client requires no code changes in typical consumer components; developer harness workflows unchanged.

### Architecture & Interfaces Under ASGI
- **Combined App**: A single ASGI app serves Flask routes and Socket.IO endpoints. Flask views continue to operate; Socket.IO runs via AsyncServer/ASGIApp.
- **Server Process**: `run_ui.py` constructs and runs uvicorn programmatically, maintaining current CLI options and logging discipline.
- **Sessions & CSRF**: HTTP session cookie is shared; CSRF handshake semantics remain: short‑lived flag set by `/csrf_token`, validated during WS connect and on reconnect attempts.
- **Handler API**: Same discovery/registration model, async `process_event` signature, explicit event‑type routing, multi‑handler aggregation and standardized error objects.

### Concurrency & Scaling Guidance (Multi‑Tenancy Readiness)
- **Default**: Single uvicorn worker recommended to preserve in‑memory connection state and buffering without external broker.
- **Scaling Up**: For multiple workers or instances, document requirement to configure a `python‑socketio` message queue (e.g., Redis) for cross‑worker events and rooms‑less broadcast equivalence.
- **Backpressure**: Maintain buffering cap (100) with drop‑oldest policy; document application‑level throttling for producer bursts.

### Dependencies & Packaging
- Add runtime deps: `uvicorn`, `python‑socketio` (async), and any minimal ASGI adapters required by the selected integration approach.
- Update Docker build/run layers to include/retain these with no significant image size or boot‑time regressions.

### Developer Harness & Quickstart Impact
- Entry remains `python run_ui.py` (programmatic uvicorn). Quickstart MUST reflect ASGI runtime and how to disable access logs when needed.
- Testing guidance MUST mention event‑loop friendly patterns and avoiding blocking calls in handlers.
- Tasks: update `specs/003-websocket-event-handlers/quickstart.md` to reflect uvicorn runtime, start/stop instructions, and test notes.

### Migration Plan (Phases)
- **Phase 0 – Foundations**: Introduce dependencies; create combined ASGI app wiring behind feature flag; keep behavior parity.
- **Phase 1 – Runtime Switch**: Programmatic uvicorn in `run_ui.py`; disable access logs; preserve REST.
- **Phase 2 – Handlers on asyncio**: Ensure all handlers run async; add shims for legacy synchronous paths where needed (executors).
- **Phase 3 – Validation**: Run and stabilize tests for CSRF, auth, routing, buffering, reconnection; fix timing flakes.
- **Phase 4 – Docs**: Update Quickstart, scaling guidance, and migration notes for developers; enumerate traps and mitigations.
- **Phase 5 – Deployability**: Verify Docker images, single‑worker defaults, and optional multi‑worker instructions.

### Risks & Mitigations
- **Session/CSRF Bridging**: Risk mis‑wiring between WSGI and ASGI contexts → Mitigate with explicit handshake validation and shared cookie/session adapters.
- **Blocking Code**: Legacy sync code blocking event loop → Audit and offload to executors; add lint/checks.
- **Logging Noise**: Uvicorn access logs regressing → Explicitly disable or set to error‑only.
- **Multi‑Worker Semantics**: Broadcast equivalence broken without message queue → Document and gate behind explicit config.
- **Test Flakiness**: Async timing issues → Stabilize with deterministic awaits and idle detection; avoid arbitrary sleeps.

### Backward‑Compatibility Traps
- Thread‑local assumptions in handlers; per‑thread locks; WSGI‑only middleware; global state mutated outside event loop. Each must be audited and adapted to asyncio‑safe patterns.

### Deliverables Recap
- Updated specification sections (this addendum) with requirements, constraints, and risks
- Contracts clarifying server/handler/frontend interfaces under ASGI
- Revised implementation phases (above)
- Quickstart update tasks (startup and testing under uvicorn)
- Scaling guidance and worker recommendations

## Enhancement: WebSocket Client–Server Symmetry & Handler Addressing Enhancements (2025-10-28)

### Objective
Align backend and frontend capabilities for emitting, requesting, and aggregating events, add handler/SID filtering, acknowledgment metadata, and session tracking hooks while preserving existing authentication, CSRF, buffering, and tests.

### Scope
1. API additions for server-side `WebSocketHandler`.
2. Matching enhancements in `webui/js/websocket.js`.
3. Optional metadata envelopes for server → client deliveries.
4. Session tracking utilities to map users ↔ SIDs.
5. Documentation/checklist updates (contracts, Quickstart, data model).

### Functional Requirements — Symmetry & Filtering

- **FR-SYNC-001 (Function Symmetry)**: Expose the same conceptual operations on both ends:
  - Server (`WebSocketHandler`): `emit_to`, `broadcast`, `request`, `request_all`
  - Client (`websocket.js`): `emit`, `broadcast` (new), `request`, `requestAll`
  - Server method names remain snake_case; client methods remain camelCase.

- **FR-SYNC-002 (Server helper: request to one sid)**: Provide `async request(self, sid: str, event_type: str, data: dict, timeout: float) -> list[dict]` that fans out to all handlers for the event type but targets only the specified `sid`. Mirrors client `request` result shape (per‑handler results).

- **FR-SYNC-003 (Server helper: request_all)**: Formalize existing helper to return `[{ sid: str, results: [...] }]` aggregating per‑sid arrays of per‑handler results. For any targeted `sid` with no matching handlers or connection errors, include the `sid` with a standardized error object captured in `results` (see contracts/event-schemas.md §Standardized Errors).

- **FR-SYNC-004 (Client broadcast helper)**: Add `websocket.broadcast(eventType, data, { excludeSids?: string[] })` mirroring server `broadcast` semantics (deliver to all connections unless explicitly excluded). `includeSids` is not supported at this time.

- **FR-SYNC-005 (Timeout semantics)**: Default timeout for `request`/`requestAll` is `0` milliseconds (unlimited) when omitted on both frontend and backend. All timeout parameters are specified in milliseconds.
- **FR-ERG-001 (Developer helper wrappers)**: Provide convenience utilities on both backend and frontend so developers never hand-craft metadata envelopes or request result objects. Backend MUST expose helper(s) on `WebSocketHandler` (or companion module) that build standardized success/error result payloads consumed by `WebSocketManager` (including optional `correlationId`, `durationMs`, and error codes). Frontend MUST expose exported helper(s) for generating correlation IDs, normalising filter options, and validating server delivery envelopes before invoking consumer callbacks. Helpers MUST raise descriptive validation errors when payloads are malformed.
- **FR-ERG-002 (Shared validation reuse)**: The helper abstractions MUST be the single source of truth for filter/envelope validation in production code, documentation examples, and developer tooling (harness). Unit tests MUST cover helper success/error paths to prevent regressions.

- **FR-HANDLER-001 (Handler filtering – client → server)**: `websocket.request` accepts `includeHandlers: string[]` (only). `websocket.requestAll` accepts `excludeHandlers: string[]` (only). Mixed include+exclude is not supported. Omitted filters preserve status quo (all handlers).

- **FR-HANDLER-002 (SID filtering – server → client)**: `emit_to` remains point‑to‑point. `broadcast` supports optional `exclude_sids` only (no `include_sids` at this time). Server `request` helper targets a specific `sid` (see FR‑SYNC‑002) and does not introduce SID include/exclude lists.

- **FR-HANDLER-003 (Client emit handler filter)**: `websocket.emit` may accept `includeHandlers` only. Server enforces handler lookup/filters within `WebSocketManager` so only listed handlers receive data.


 - **FR-HANDLER-004 (Server broadcast handler metadata)**: Always wrap server→client deliveries with envelope `{ handlerId, eventId, ts, data }`. `eventId`: unique per delivery (UUIDv4 string). `ts`: ISO8601 UTC timestamp with millisecond precision. This is an application-level envelope surfaced to subscribers; it does not change Socket.IO transport framing.

 - **FR-ENVELOPE-UNIFORM (Envelope consistency across tiers)**:
   - Client→Server (emit/request/requestAll): messages carry `{ correlationId?, ts, data }` where `ts` is ISO8601 UTC with milliseconds. If `correlationId` is omitted by client, server generates one and echoes it.
   - Server→Client (emit_to/broadcast/replies): messages carry `{ handlerId, eventId, correlationId, ts, data }`. If no originating `correlationId` is present, server generates one.
   - Request/Response acks: responses include `correlationId` alongside existing payloads. Additive where feasible; if shape changes are required, document migration in contracts.

 - **FR-CORRELATION-001 (Correlation propagation)**: `correlationId` MUST be preserved end‑to‑end across all related messages (client emit/request → server processing → server reply/broadcast → client handling). When generated, it MUST be returned/echoed in the first reply and included in any follow‑up server‑initiated deliveries caused by the same action.

 - **FR-HANDLER-005 (Client broadcast metadata)**: Clients MUST expose `handlerId`, `eventId`, and `ts` alongside `data` to event subscribers (see FR‑HANDLER‑004).

- **FR-HANDLER-006 (Client requestAll aggregator)**: Preserve current ack schema `[{ handlerId, ok, data|error }]`. New handler filters must still return results per handler.

### Session Tracking / Multi‑tenancy Hooks

- **FR-SESSION-001**: Maintain mappings between authenticated user identifier ↔ set of SIDs (and reverse). Update connection lifecycle to capture available user identifier (single‑user fallback: all SIDs). Provide helpers such as `get_sids_for_user(user_id)` and `get_user_for_sid(sid)` for future multi‑tenant logic while defaulting to single‑user behavior.

- **FR-SESSION-002**: Document helper usage (e.g., DM all of a user’s tabs vs broadcast) in contracts and Quickstart.

- **FR-SESSION-003 (Future multitenancy mechanics)**: Record the planned implementation once multiple users are supported: `register()` captures a resolved `user_id` from the authentication layer, `get_sids_for_user(user_id)` returns that tenant’s SID bucket, `get_user_for_sid(sid)` reveals the owning tenant, and optional helpers (e.g., `get_users()`) expose all tracked tenants. Maintain backward compatibility by treating `user_id is None` as the single-user `allUsers` bucket and ensuring existing handlers operate unchanged.

### Tests

1. Backend unit tests:
   - `request` returns payloads for a single `sid`.
   - `request_all` with handler filters includes/excludes correctly.
   - Handler filtering honors defaults (all handlers) and combinations (include only, exclude only, include+exclude).
   - Server→client envelope includes `handlerId`, `eventId` (UUIDv4), and `ts` (ISO8601 UTC with milliseconds) for every delivered event.
   - Default timeout behavior: omitting timeout results in unlimited wait (`0` ms) and honors millisecond units when provided.
   - `request_all` includes every targeted `sid` with standardized error entries for SIDs without handlers or with connection errors.

2. Frontend unit tests / harness checks:
   - `websocket.request`/`requestAll` send handler filter metadata; results match contracted shapes.
   - `websocket.broadcast` honors `excludeSids` (only); no `includeSids` parameter.
   - Subscribers receive `{ handlerId, eventId, ts, data }`; `eventId` validates as UUIDv4 and `ts` parses as ISO8601 UTC with milliseconds.
   - Default timeout behavior on client: omitted timeout implies unlimited (`0` ms) and explicit values are in milliseconds.

3. Harness update: Extend automatic suite to validate include/exclude filters and presence of `handlerId` metadata.
   - Validate full envelope presence and field formats (`eventId`, `ts`).
   - Validate filter semantics: `request` supports `includeHandlers` only; `requestAll` supports `excludeHandlers` only; `emit` supports `includeHandlers` only; `broadcast` supports `excludeSids` only.

### Documentation Updates

1. `contracts/frontend-api.md`: Document `broadcast`, handler filter options, metadata envelope, client→server envelope `{ correlationId?, ts, data }`, optional client-provided `correlationId` and server generation/echo semantics.
2. `contracts/websocket-handler-interface.md`: Add server helper signatures (`request`, `request_all`), filtering semantics (request: includeHandlers only; requestAll: excludeHandlers only), metadata contract (including `eventId` UUIDv4, `correlationId`, and `ts` ISO8601 UTC semantics), reply shapes carrying `correlationId`, and timeout units/default (`0` ms unlimited).
3. `data-model.md`: Extend connection model with user ↔ SID mapping concept and helper semantics.
4. `quickstart.md`: Examples for handler filtering and request fan‑out.
5. `checklists/requirements.md`: Log new requirements and migration notes (symmetry, filters, metadata).
6. `contracts/event-schemas.md`: Define standardized error object for per‑sid aggregator results and document millisecond timeout units.

### Non‑Functional Requirements

- Preserve existing behaviors: authentication, CSRF TTL (120s), buffering semantics, reconnection.
- NFR‑LOG‑DEV: Debug logs are development‑only. Backend `PrintStyle.debug` emits output only when runtime is in development mode. Frontend debug utility outputs to console only when a backend‑provided `isDevelopment` flag is true. Logs should include `eventId` and/or `correlationId` where relevant and be placed judiciously to avoid noise.
- Backward compatible: handlers without filters continue to work unchanged; metadata envelope for server→client deliveries is mandatory and non‑breaking for consumers (payload remains under `data`; additional fields are additive and safely ignorable by generic renderers).
- Documentation must stress that handler identifiers are unique and deterministic to make filtering reliable.
- Single‑user behavior remains default; session lookup helpers do not alter current deployment semantics.

### Session Tracking Details

- Special bucket `allUsers` holds all tracked SIDs (single-user deployment). Provide helper `get_sids_for_user(user=null)` which currently ignores `user` (placeholder for future multi-tenant evolution). Internal mappings remain private.
