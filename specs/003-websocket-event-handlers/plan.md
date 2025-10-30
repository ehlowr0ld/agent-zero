# Implementation Plan: WebSocket Event Handlers

**Branch**: `003-websocket-event-handlers` | **Date**: 2025-10-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-websocket-event-handlers/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement WebSocket infrastructure for bidirectional real-time communication following existing REST API handler patterns, and migrate runtime to an ASGI-native architecture using python-socketio.AsyncServer + uvicorn. Preserve identical product behavior (sessions, CSRF, handler API, developer harness) while serving a combined Flask + Socket.IO ASGI app. Ensure secure authentication, automatic reconnection, server-side event buffering, and seamless integration with the existing application.

## Technical Context

**Language/Version**: Python 3.12.x (project venv standard)
**Primary Dependencies**: Flask 3.0.3, python-socketio (AsyncServer) 5.x, uvicorn 0.30+, Alpine.js (frontend)
**Storage**: File-based session management (existing), no database required
**Testing**: pytest 8.4.2, pytest-asyncio 1.2.0, pytest-mock 3.15.1
**Target Platform**: Linux server (containerized), browser clients (modern browsers with WebSocket support)
**Project Type**: Web application (backend + frontend integration)
**Runtime**: ASGI (uvicorn, programmatic startup from `run_ui.py`, access-log disabled by default)
**Performance Goals**: <100ms event delivery latency, 100+ concurrent connections, 8+ hour connection stability
**Constraints**: Single-user application scope, no multi-tenancy, connection-time authentication only, simple broadcast model
**Scale/Scope**: Single authenticated user, multiple browser tabs/windows, infrastructure-level feature (no specific application features)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Exploration-First Development ✅ PASS

**Status**: Compliant
**Verification**: This planning phase explicitly includes Phase 0 research to explore Flask-SocketIO, python-socketio patterns, and existing ApiHandler architecture before implementation. Research phase will verify:
- Flask-SocketIO integration patterns with Flask async
- Existing authentication mechanisms (session, CSRF)
- ApiHandler base class structure and security decorators
- Frontend Alpine.js component patterns
- Message serialization and WebSocket protocol handling

### II. Transparency Over Magic ✅ PASS

**Status**: Compliant
**Design Alignment**:
- WebSocket event routing will be explicit (handlers declare event types)
- Connection lifecycle visible (connect/disconnect handlers)
- Event flow traceable (client → handler → client)
- No hidden abstractions or auto-magic behavior
- Clear separation between fire-and-forget and request-response patterns

### III. Security-First Design ✅ PASS

**Status**: Compliant
**Security Measures**:
- Authentication at connection time using existing Flask session mechanism
- CSRF protection at connection time is mandatory whenever authentication is required (no opt‑out); validated via POST `/csrf_token` preflight (header+cookie) and checked at WS handshake; client proactively POSTs on `reconnect_attempt`
- No per-event authentication (connection already authenticated)
- Server-side only authentication checking
- Reuse existing security infrastructure (`requires_auth()`, `requires_csrf()`, session validation)
- No credentials exposed to frontend
- Session expiration detection and connection closure

### IV. Non-Blocking Async ✅ PASS

**Status**: Compliant
**Async Strategy**:
- ASGI-native runtime with python-socketio.AsyncServer
- All event handlers use `async def` patterns
- Event buffering uses async queue mechanisms
- No blocking operations in event loop
- Background tasks for connection management use async patterns
- Compatible with uvicorn event loop

### V. Self-Contained Components ✅ PASS

**Status**: Compliant
**Frontend Design**:
- WebSocket client will be implemented as inline JavaScript module
- Frontend components using WebSocket will include inline styles
- No global WebSocket state pollution
- Component-scoped WebSocket subscriptions
- Follows existing Alpine.js component patterns with inline CSS/JS

### VI. Infrastructure Invisibility ✅ PASS

**Status**: Compliant
**User Experience**:
- WebSocket infrastructure hidden from end users
- Connection management automatic and transparent
- Reconnection happens silently in background
- Error handling provides user-friendly messages
- Infrastructure events (connect/disconnect) not exposed to users
- Only application-level events visible

### VII. Architectural Boundaries ✅ PASS

**Status**: Compliant
**Pattern Adherence**:
- Mirror ApiHandler pattern exactly (base class, auto-discovery, security decorators)
- Handler registration similar to API handlers (`python/helpers/websocket.py` or similar)
- Filename-based handler discovery from `python/websocket_handlers/` or similar
- No parallel systems - extends existing Flask application architecture
- Integration with existing session, CSRF, and authentication systems
- No modifications to `job_loop.py` (WebSocket is not system maintenance)

### VIII. Environment Separation ✅ PASS

**Status**: Compliant
**Environment Handling**:
- Combined ASGI app (Flask WSGI app mounted under python-socketio.ASGIApp)
- Development mode: Programmatic uvicorn from `python run_ui.py`
- Production mode: Containerized uvicorn serves combined app
- No RFC calls needed (WebSocket is runtime-independent application logic)

### IX. RFC Discipline ✅ PASS

**Status**: Compliant
**RFC Usage**: Not applicable - WebSocket infrastructure is application-level logic (not OS-dependent resources), runs in Flask process regardless of environment

### X. Shell Connection Discipline ✅ PASS

**Status**: Compliant
**Shell Usage**: Not applicable - WebSocket infrastructure does not require shell operations

### XI. PrintStyle Logging Only ✅ PASS

**Status**: Compliant
**Logging Strategy**:
- All WebSocket logging uses PrintStyle exclusively
- Connection events logged via `PrintStyle.info()`
- Errors logged via `PrintStyle.error()`
- Debug messages via `PrintStyle.debug()`
- Uvicorn access-log disabled; error-level only
- No other logging frameworks introduced
- Handlers use `PrintStyle` static methods for logging: `PrintStyle.info()`, `PrintStyle.error()`, etc.

### XII. Dual Communication Channels ✅ PASS

**Status**: Compliant
**Channel Coexistence**:
- WebSocket infrastructure coexists with existing HTTP polling (explicitly stated in spec FR-033)
- Existing features remain on polling (no migration required)
- WebSocket available for new features requiring real-time bidirectional communication
- Both mechanisms permanent first-class citizens
- Developers choose appropriate channel per feature requirements

### XIII. Project Scope & Simplicity ✅ PASS

**Status**: Compliant
**Scope Alignment**:
- **Single-User Context**: No multi-tenancy, no user isolation, no resource quotas
- **Authentication Simplicity**: Connection-time auth only (binary: logged in or not), no per-event authorization
- **No Enterprise Patterns**: No rate limiting per connection, no per-event auth checks, no security event database
- **No Room Complexity**: Simple broadcast model (all tabs by default), optional specific-connection targeting
- **No Unnecessary Persistence**: Events buffered in memory (100 max), no audit log database
- **Mirror ApiHandler**: Reuse existing session authentication, CSRF patterns, no reinvention
- **Infrastructure Only**: Provides WebSocket capability, not specific application features

**Anti-Patterns Avoided**:
- ❌ NO per-event authentication (connection already authenticated)
- ❌ NO room management (simple broadcast model)
- ❌ NO rate limiting per connection (single user)
- ❌ NO security event logging to database (use PrintStyle to application log)
- ❌ NO elevated permissions (single user has full access)
- ❌ NO multi-user patterns (rooms, user-specific channels, tenant isolation)

### Constitution Check Summary

**Overall Status**: ✅ ALL GATES PASS - CONFIRMED (asyncio same-origin WS + CSRF preflight, 50MB cap)

All 13 constitutional principles are satisfied. The WebSocket infrastructure design:
- Mirrors existing ApiHandler patterns exactly (VII)
- Maintains single-user simplicity (XIII)
- Implements security at connection time only (III)
- Uses async discipline throughout (IV)
- Coexists with HTTP polling permanently (XII)
- Requires no architectural changes to existing systems

**Pre-Implementation Approval**: ✅ GRANTED - Proceed to Phase 0 Research

---

## Constitution Check Re-Evaluation (Post-Design)

**Date**: 2025-10-16
**Phase**: Post-Phase 1 Design Review

### Design Artifacts Review

**Generated Documents**:
- ✅ `research.md` - Technical research and decisions
- ✅ `data-model.md` - Entity definitions and relationships
- ✅ `contracts/websocket-handler-interface.md` - Handler base class contract
- ✅ `contracts/event-schemas.md` - Message format specifications
- ✅ `contracts/frontend-api.md` - Client library API contract
- ✅ `contracts/security-contract.md` - Authentication and security patterns
- ✅ `quickstart.md` - Developer guide with examples

### Constitution Compliance Verification

**Re-evaluation against all 13 principles after completing design phase**:

#### I. Exploration-First Development ✅ PASS (CONFIRMED)

**Design Evidence**:
- Phase 0 research completed: Flask-SocketIO integration patterns documented
- Existing ApiHandler architecture analyzed and mirrored
- Frontend patterns from `api.js` and Alpine.js components studied
- All integration points verified before design decisions

**Status**: Design phase confirms exploration-first approach successful

---

#### II. Transparency Over Magic ✅ PASS (CONFIRMED)

**Design Evidence**:
- `websocket-handler-interface.md`: Explicit handler registration and discovery
- `event-schemas.md`: Clear event routing rules and naming conventions
- `data-model.md`: Visible state transitions and relationships
- `frontend-api.md`: No hidden connection management - explicit `connect()` call
- `quickstart.md`: Traceable examples showing full event flow

**Status**: Design maintains transparency throughout

---

#### III. Security-First Design ✅ PASS (CONFIRMED)

**Design Evidence**:
- `security-contract.md`: Comprehensive security model documented
- Connection-time authentication using existing Flask session (reuse existing security)
- Connection-time CSRF validation using existing token infrastructure
- No per-event authentication (connection already validated)
- HTTPS/WSS required in production
- Input validation required in all handlers

**Status**: Security architecture mirrors existing REST API patterns exactly

---

#### IV. Non-Blocking Async ✅ PASS (CONFIRMED)

**Design Evidence**:
- `websocket-handler-interface.md`: All handler methods use `async def`
- `research.md`: Flask-SocketIO in asyncio mode (same-origin upgrade)
- Event buffering uses async queue mechanisms
- Background tasks use asyncio patterns
- No blocking operations in handler contracts

**Status**: Design enforces async discipline throughout

---

#### V. Self-Contained Components ✅ PASS (CONFIRMED)

**Design Evidence**:
- `frontend-api.md`: WebSocket client as inline JavaScript module
- `quickstart.md`: Examples show inline styles in Alpine.js components
- No global WebSocket state pollution
- Component-scoped subscriptions with `on()` and `off()`

**Status**: Frontend design follows self-contained component pattern

---

#### VI. Infrastructure Invisibility ✅ PASS (CONFIRMED)

**Design Evidence**:
- `frontend-api.md`: Connection management automatic via lazy initialization
- `data-model.md`: Reconnection happens silently in background
- `event-schemas.md`: Infrastructure events (connect/disconnect) not exposed to users
- `quickstart.md`: Developer-focused documentation (infrastructure visible to devs, not users)

**Status**: User-facing features hide infrastructure complexity

---

#### VII. Architectural Boundaries ✅ PASS (CONFIRMED)

**Design Evidence**:
- `websocket-handler-interface.md`: Mirrors ApiHandler pattern exactly (same security decorators, same auto-discovery)
- `research.md`: Handler registration uses existing `load_classes_from_folder()` mechanism
- `data-model.md`: No parallel systems - extends existing Flask architecture
- `contracts/`: Integration with existing session, CSRF, authentication systems
- No modifications to `job_loop.py` (WebSocket is application logic, not system maintenance)

**Status**: Design respects all architectural boundaries

---

#### VIII. Environment Separation ✅ PASS (CONFIRMED)

**Design Evidence**:
- `research.md`: WebSocket server runs in same Flask process (no separate service)
- `security-contract.md`: Development and production modes handled identically
- No container-specific WebSocket routing needed
- No RFC calls required (WebSocket is application logic)

**Status**: Design respects environment separation

---

#### IX. RFC Discipline ✅ PASS (CONFIRMED)

**Design Evidence**:
- `data-model.md`: WebSocket infrastructure is application-level logic (not OS-dependent)
- `research.md`: Runs in Flask process regardless of environment
- No RFC usage in any design artifacts

**Status**: RFC not needed or used (appropriate)

---

#### X. Shell Connection Discipline ✅ PASS (CONFIRMED)

**Design Evidence**:
- WebSocket infrastructure does not require shell operations
- Not applicable to this feature

**Status**: No shell operations required (appropriate)

---

#### XI. PrintStyle Logging Only ✅ PASS (CONFIRMED)

**Design Evidence**:
- `websocket-handler-interface.md`: Use `PrintStyle` static methods directly (no `get_log_object()` - that's Tool-specific for GUI logs)
- `security-contract.md`: All security events logged via PrintStyle static methods
- `quickstart.md`: Examples show `PrintStyle.info()`, `PrintStyle.error()` direct usage pattern
- No other logging frameworks introduced

**Status**: Design enforces PrintStyle-only logging

---

#### XII. Dual Communication Channels ✅ PASS (CONFIRMED)

**Design Evidence**:
- `research.md`: Explicit confirmation that HTTP polling and WebSocket coexist permanently
- `data-model.md`: WebSocket infrastructure separate from existing polling
- `quickstart.md`: Developers choose appropriate channel per feature
- No migration of existing features required

**Status**: Design preserves dual-channel architecture

---

#### XIII. Project Scope & Simplicity ✅ PASS (CONFIRMED)

**Design Evidence - Single-User Simplicity**:
- `security-contract.md`: "Binary authentication model: logged in or not"
- `security-contract.md`: Section titled "No Enterprise Security Theater" explicitly lists rejected patterns
- `data-model.md`: "No multi-tenancy, no user isolation, no resource quotas"
- `event-schemas.md`: Simple broadcast model (all tabs by default)
- `websocket-handler-interface.md`: No per-event authentication, no authorization layer

**Rejected Enterprise Patterns** (documented in security-contract.md):
- ❌ Per-event authentication
- ❌ Room management
- ❌ Rate limiting per connection
- ❌ Security event database
- ❌ Elevated permissions
- ❌ Multi-user patterns

**Design Evidence - Appropriate Complexity**:
- `research.md`: Reuse existing infrastructure (Flask session, CSRF tokens)
- `data-model.md`: In-memory event buffering (no persistence layer)
- `security-contract.md`: Use general application logging (no audit trail database)
- `frontend-api.md`: Simple client library (mirrors existing api.js)

**Status**: Design maintains single-user simplicity throughout

---

### Post-Design Constitution Summary

**Overall Status**: ✅ ALL 13 PRINCIPLES SATISFIED AFTER DESIGN PHASE

**Key Design Decisions Aligned with Constitution**:
1. **Mirror ApiHandler** - Respects Principle VII (Architectural Boundaries)
2. **Flask session auth** - Respects Principle III (Security-First) and XIII (Simplicity)
3. **Connection-time validation only** - Respects Principle XIII (Project Scope)
4. **PrintStyle logging** - Respects Principle XI (Logging Standard)
5. **Async handlers** - Respects Principle IV (Non-Blocking Async)
6. **Inline components** - Respects Principle V (Self-Contained Components)
7. **Simple broadcast model** - Respects Principle XIII (No Enterprise Patterns)
8. **In-memory buffering** - Respects Principle XIII (No Unnecessary Persistence)

**No Constitutional Violations Introduced**: Design phase maintained full compliance

**Post-Implementation Approval**: ✅ RECONFIRMED - Proceed to Phase 2 (Tasks Generation)

## Project Structure

### Documentation (this feature)

```
specs/003-websocket-event-handlers/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── websocket-handler-interface.md
│   ├── event-schemas.md
│   ├── frontend-api.md
│   └── security-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure Decision**: Web application structure with backend helpers and frontend integration

```
python/
├── helpers/
│   ├── websocket.py           # NEW: WebSocket infrastructure, handler base class
│   └── websocket_manager.py   # NEW: Connection management, event routing, buffering
├── websocket_handlers/        # NEW: WebSocket event handlers (mirroring python/api/)
│   └── (handlers auto-discovered and registered)
└── api/                       # EXISTING: REST API handlers (unchanged)

webui/
├── js/
│   └── websocket.js           # NEW: Frontend WebSocket client library
└── components/                # EXISTING: Alpine.js components (may use WebSocket)

tests/
├── test_websocket_handlers.py     # NEW: WebSocket handler tests
├── test_websocket_manager.py      # NEW: Connection management tests
└── test_websocket_integration.py  # NEW: End-to-end integration tests
```

**Key Directories**:
- `python/helpers/websocket.py`: Base classes and infrastructure (WebSocketHandler base class, security decorators)
- `python/helpers/websocket_manager.py`: Connection tracking, event routing, buffering logic
- `python/websocket_handlers/`: Handler implementations (auto-discovered like ApiHandler)
- `webui/js/websocket.js`: Frontend client library with Alpine.js integration
- `tests/`: Comprehensive test coverage for all WebSocket components

**Integration Points**:
- `run_ui.py`: Build combined ASGI app (python-socketio.AsyncServer wrapped by `socketio.ASGIApp`, Flask WSGI mounted via WSGI→ASGI adapter) and start uvicorn programmatically (access-log disabled)
- `python/helpers/api.py`: Reference for mirroring ApiHandler patterns
- `webui/js/api.js`: Reference for frontend API patterns
- Flask session management (existing): Reused for WebSocket authentication
- CSRF infrastructure (existing): Reused for WebSocket connection validation

---

## ASGI Migration Plan (Addendum)

### Objectives
- Replace Flask-SocketIO + threading with ASGI-native stack: python-socketio.AsyncServer (`async_mode='asgi'`) + `socketio.ASGIApp` served by uvicorn.
- Preserve product behavior: sessions, CSRF (120s WS flag), handler API, buffering, developer harness, and tests.

### Functional Requirements Mapping
- MIG-001: Initialize AsyncServer and mount via ASGIApp into a single ASGI app alongside Flask.
- MIG-002: Start uvicorn programmatically from `run_ui.py`; disable access-log noise (error-only).
- MIG-003–MIG-005: Preserve session auth and CSRF at connection time; keep handler API (async `process_event`, multi‑handler aggregation).
- MIG-006–MIG-007: Preserve buffering semantics and frontend client behavior.
- MIG-008: Entry remains `python run_ui.py`.
- MIG-009–MIG-010: Tests remain stable; ensure full asyncio compliance.
- MIG-011–MIG-016: Document uvicorn config (single worker default), scaling guidance (Redis manager for multi‑worker), transport defaults.

### Acceptance Criteria (ASGI)
- AC‑ASGI‑01: `python run_ui.py` launches uvicorn; access‑log disabled; error‑level only.
- AC‑ASGI‑02: REST endpoints unchanged; sessions/CSRF flows identical from user perspective.
- AC‑ASGI‑03: WebSocket auth/CSRF/routing/buffering tests pass unchanged (timing tweaks allowed in helpers only).
- AC‑ASGI‑04: Delivery/latency targets met or improved.
- AC‑ASGI‑05: Frontend client requires no changes in typical consumers.

### Implementation Phases
1. Phase 0 – Foundations
   - Add dependencies: `uvicorn`, `python-socketio` (async). Ensure 50MB max buffer config.
   - Introduce combined ASGI wiring behind feature flag (no behavior change).
2. Phase 1 – Runtime Switch
   - Update `run_ui.py` to construct AsyncServer and ASGIApp; mount Flask via WSGI→ASGI adapter.
   - Start uvicorn programmatically; disable access-log.
3. Phase 2 – Handlers on asyncio
   - Verify all WS handlers run async without blocking; offload any sync work.
4. Phase 3 – Validation
   - Stabilize tests: CSRF 120s preflight flag, auth, routing, buffering, reconnection.
5. Phase 4 – Docs
   - Update Quickstart (startup via uvicorn, testing under ASGI), scaling guidance, traps.
6. Phase 5 – Deployability
   - Verify Docker images, single‑worker default; document Redis manager for multi‑worker.

### Backward‑Compatibility Traps
- WSGI‑only middleware assumptions; thread‑local usage; per‑thread locks in async code; reliance on Flask request context in background tasks.

### Plan Tasks (Documentation Updates)
- Update `quickstart.md` to reflect uvicorn runtime (python run_ui.py → uvicorn), error‑only access‑log, and test notes. [Track as doc task; file will be edited in its dedicated update step.]

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No violations - this section intentionally left empty.

All constitutional principles are satisfied. No complexity justification required.

---

## Plan Addendum (2025-10-28): WebSocket Client–Server Symmetry & Handler Addressing Enhancements

### Objective
Align backend and frontend so both expose matching capabilities for emitting, requesting, and aggregating events, adding handler filtering, acknowledgment metadata envelope, and session tracking hooks. Preserve existing auth, CSRF, buffering, and tests.

### Scope Mapping → Deliverables
- Backend helpers:
  - Add `request(sid, event_type, data, timeout_ms)` (single sid, per‑handler aggregation)
  - Formalize `request_all(event_type, data, timeout_ms)` → returns `[{ sid, results: [...] }]`, include standardized error objects for sids with no handlers/connection errors
  - `broadcast(event_type, data, exclude_sids=[])` (exclude only)
  - Always wrap server→client deliveries: `{ handlerId, eventId, ts, data }` (UUIDv4, ISO8601 ms)
- Frontend APIs (`webui/js/websocket.js`):
  - `emit(eventType, data, { includeHandlers? })`
  - `broadcast(eventType, data, { excludeSids? })`
  - `request(eventType, data, { includeHandlers? , timeoutMs=0 })`
  - `requestAll(eventType, data, { excludeHandlers? , timeoutMs=0 })`
  - Subscribers receive envelope `{ handlerId, eventId, ts, data }`
- Session hooks: expose `get_sids_for_user(user=null)` (placeholder arg, single‑user now), maintain special bucket `allUsers` for all SIDs

### Contracts To Update (this plan)
- `contracts/frontend-api.md`: Add `broadcast`, handler filter options, timeout units (ms) with default `0`, subscriber envelope
- `contracts/websocket-handler-interface.md`: Document server helpers (`request`, `request_all`), broadcast exclude‑only, envelope, and filter semantics handling
- `contracts/event-schemas.md`: Define delivery envelope schema, standardized error objects for aggregated results, timeout units/default
- `contracts/security-contract.md`: Reference CSRF TTL 120s unchanged (already documented)
- `data-model.md`: Add user↔SID mappings (`allUsers` bucket) and helper `get_sids_for_user(user=null)`
- `research.md`: Record clarifications (2025‑10‑28) and rationale

### Testing Plan Alignment
- Backend: verify envelope presence; `request` single‑sid; `request_all` includes every targeted sid with standardized error when applicable; handler filters semantics
- Frontend: verify `broadcast` excludeSids only; `emit/request/requestAll` filter options; timeout `0` means unlimited; subscriptions receive envelope
- Developer tooling: verify developer settings suppress the WebSocket harness outside development runtime and template gating matches runtime flag

### Risks & Mitigations (No Behavioral Regression)
- Risk: Breaking existing consumers expecting raw payloads → Mitigation: envelope is additive; payload remains under `data`
- Risk: Filter misuse → Mitigation: enforce request includeHandlers only; requestAll excludeHandlers only; broadcast excludeSids only; document clearly
- Risk: Timeout confusion → Mitigation: unify to milliseconds, default `0` unlimited across client/server

---

## Plan Addendum (2025-10-31): Developer Ergonomics Helper Utilities

### Objective
Reduce friction for backend and frontend developers by centralising construction and validation of WebSocket envelopes, correlation metadata, and request-result payloads.

### Scope Mapping → Deliverables
- Backend helper module updates:
  - Introduce `WebSocketResult` (or equivalent) factory methods on `WebSocketHandler` for success/error payloads consumed by `WebSocketManager`.
  - Ensure manager recognises helper instances and preserves optional metadata (`correlationId`, `durationMs`).
- Frontend helper exposure:
  - Export reusable utilities from `webui/js/websocket.js` (or sibling module) to generate correlation IDs, normalise handler/SID filters, and validate server delivery envelopes before callbacks execute.
  - Provide optional TypeScript-style JSDoc for IDE assistance.
- Documentation & harness alignment:
  - Update developer harness and documentation examples to consume the helpers instead of hand-rolled objects.
- Testing additions covering helper success/error paths and harness adoption.

### Dependencies
- Built on top of Phase E symmetry work (helpers assume envelopes + correlation pipeline already in place).
- Requires coordination with documentation tasks (Quickstart, contracts) to reference the new helper APIs once implemented.

### Risks & Mitigations
- Risk: Divergence between helper validation and manager expectations → Mitigation: share schema constants/tests across modules.
- Risk: Breaking existing manual code paths → Mitigation: provide transitional shims; document migration guidance.
