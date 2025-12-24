# Tasks: WebSocket Event Handlers

**Input**: Design documents from `/specs/003-websocket-event-handlers/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/*.md
**Contracts**: Authoritative contract inventory for this feature is `contracts/*.md` (no repo-level contract target document).

**Tests**: Tests are requested. For each story, test implementation and test execution are distinct tasks (TDD ordering where applicable).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Backend helpers live in `python/helpers/`
- WebSocket handlers live in `python/websocket_handlers/`
- Frontend client lives in `webui/js/`
- Main app entry point lives in `run_ui.py`
- Frontend entry point lives in `webui/index.html` and `webui/index.js` and `webui/index.css`
- Socket.IO js library esm module present, lives in `webui/vendor/socket.io.esm.min.js`
- Tests live in `tests/`

---

## Phase 0 — Prerequisites (Shared)

**Purpose**: Environment and structure readiness (template‑canonical)

- [x] T000 [US-Setup] Verify Python environment; activate `.venv` (Python 3.12.x) [repo root]
- [x] T001 [US-Setup] Verify dependencies (Flask 3.x, Flask-SocketIO 5.5.x, python-socketio 5.14.x); sync `requirements.txt` [repo root]
- [x] T002 [P] [US-Setup] Confirm folders exist: `python/helpers/`, `python/websocket_handlers/`, `webui/js/`

**Foundational checks (pre‑implementation)**

- [x] T004 [US-Found] Confirm `max_http_buffer_size=50*1024*1024` is acceptable for infra; note override point (engine.io)
- [x] T005 [P] [US-Found] Confirm CSRF preflight strategy via POST `/csrf_token`; reconnect_attempt pre‑POST documented
- [x] T006 [P] [US-Found] Establish shared `threading.RLock` usage pattern across WS components

**Checkpoint**: Env and foundational checks ready

---

## Phase 1: User Story 1 — Infrastructure Foundation (Priority: P1) 🎯 MVP

**Goal**: Production‑ready WebSocket foundation with routing, lifecycle, and buffering

**Independent Test**: Sample handler request‑response returns data; buffer flushes on reconnect

### Implementation for User Story 1

- [x] T010 [US1] Initialize Socket.IO in `run_ui.py` (same‑origin upgrade, `async_mode='asgi'`, loggers off, `max_http_buffer_size=50*1024*1024`); expose `socketio` and preserve existing Flask routing (DispatcherMiddleware mounts remain intact)
- [x] T011 [US1] Create base class `python/helpers/websocket.py` (`WebSocketHandler` with async `process_event`, optional `on_connect`/`on_disconnect`; class methods `get_event_types()`, `requires_auth()`, `requires_csrf()`; constructor uses `threading.RLock`)
- [x] T012 [US1] Create manager `python/helpers/websocket_manager.py` (connections registry, routing, per‑sid buffer deque=100 with entries expiring 60 minutes after last write; periodic sweep hourly; flush buffered events on reconnect; APIs: `handle_connect`, `handle_disconnect`, `route_event`, `emit_to`, `broadcast`)
- [x] T013 [P] [US1] Wire events in `run_ui.py` (register ASGI Socket.IO events via `sio.on('connect')`/`sio.on('disconnect')` → manager handlers)
- [x] T014 [P] [US1] Dynamic application event routing in `run_ui.py` → `manager.route_event(event_type, data, sid, ack)` and use `ack` for request‑response
- [x] T015 [US1] Sample handler `python/websocket_handlers/hello_handler.py` (event `hello_request` returns simple result; PrintStyle logs)

### Tests for User Story 1 (requested)

- [x] T016-Test [P] [US1] Backend unit tests for foundation: connect/disconnect, `route_event` happy path, buffer overflow eviction (`tests/test_websocket_manager.py`)
- [x] T017-Run [US1] Execute tests (backend foundation) in venv; capture results

**Checkpoint**: US1 functional and independently testable

---

## Phase 2: User Story 2 — Security & CSRF (Priority: P1)

**Goal**: Connection‑time session authentication + CSRF preflight, with reconnect optimization

**Independent Test**: Connect passes within TTL after preflight; fails after TTL; reconnect_attempt pre‑POST avoids failed attempt

### Implementation for User Story 2

- [x] T020 [US2] Extend `python/api/csrf_token.py` (POST) to validate `X‑CSRF‑Token` vs cookie and set `session['ws_csrf_ok']=timestamp` (TTL default 120s)
- [x] T021 [US2] Enforce CSRF at Socket.IO connect (if any registered handler `requires_csrf()` → require recent `ws_csrf_ok`, else reject)
- [x] T022 [P] [US2] Session expiration handling (ping/pong or periodic server check) → `disconnect(sid)` with reason
- [x] T023 [P] [US2] PrintStyle logging for auth/CSRF decisions; avoid noisy spam

### Tests for User Story 2 (requested)

- [x] T024-Test [P] [US2] CSRF flow tests: POST `/csrf_token` sets flag; connect within TTL succeeds; after TTL fails; reconnect_attempt path pre‑POST succeeds
- [x] T025-Run [US2] Execute tests (CSRF flow)

**Checkpoint**: US2 secure connection behavior proven

---

## Phase 3: User Story 3 — Developer‑Friendly Framework (Priority: P2)

**Goal**: Mirror ApiHandler ergonomics; auto‑discovery; clear errors; logging discipline

**Independent Test**: New handler auto‑discovers; duplicate event types aggregate; standardized error surface

### Implementation for User Story 3

- [x] T030 [P] [US3] Finalize `WebSocketHandler` API: type hints, docstrings, reserved event checks
- [x] T031 [P] [US3] Auto‑discovery registration logs at startup; warn on duplicate event types
- [x] T032 [P] [US3] Standardized error surface: exceptions → `{ error, code, details? }` per contract
- [x] T033 [P] [US3] PrintStyle integration pass across helpers/handlers

### Tests for User Story 3 (requested)

- [x] T034-Test [P] [US3] Error surface and discovery tests: duplicate event types, exception mapping
- [x] T035-Run [US3] Execute tests (developer ergonomics)

**Checkpoint**: US3 developer experience complete

---

## Phase 4: User Story 4 — Frontend Client (Priority: P2)

**Goal**: JS client mirroring `api.js`; subscriptions; timeouts; size checks; reconnect optimization

**Independent Test**: Size precheck enforced; request timeout; subscriptions persist across reconnect; reconnect_attempt pre‑POST executed

### Implementation for User Story 4

- [x] T040 [US4] Create `webui/js/websocket.js` scaffold (singleton API: `connect`, `disconnect`, `isConnected`, `emit`, `request`, `requestAll`, `on`, `off`, `onConnect`, `onDisconnect`, `onError`)
- [x] T041 [US4] Implement `connect()` with POST `/csrf_token` preflight; on `reconnect_attempt`, pre‑POST before retry
- [x] T042 [P] [US4] Implement `emit()` with 50MB client‑side precheck and not‑connected error
- [x] T043 [P] [US4] Implement `request()` returning `Array<RequestResultItem>`; timeout, cleanup, not‑connected error
- [x] T044 [P] [US4] Implement `on()`/`off()` subscriptions; persist across reconnect; multiple callbacks; order preserved
- [x] T045 [US4] Implement lifecycle callbacks: `onConnect`, `onDisconnect`, `onError`

### Tests for User Story 4 (requested)

- [x] T046-Test [P] [US4] Frontend API tests: size precheck, request timeout, subscription persistence, reconnect_attempt optimization
- [x] T047-Run [US4] Execute tests (frontend API) via chosen tooling or manual/browser protocol per docs

### Developer Harness for User Story 4

- [x] T080 [US4] Add Developer settings entry and modal wiring for WebSocket tester harness
- [x] T081 [US4] Implement WebSocket tester frontend component & store with automatic and manual validation flows
- [x] T082 [US4] Implement backend WebSocket test handler supporting harness scenarios
- [x] T083-Test [US4] Ensure harness automatic suite covers emit/request/requestAll/timeout/subscription persistence with log output and 5s toasts
- [x] T084-Run [US4] Document manual verification steps and run harness in development to confirm behavior

**Checkpoint**: US4 frontend integration behaves correctly

---

## Phase 5: User Story 5 — Aggregated Request (requestAll) (Priority: P3)

**Goal**: Broadcast request‑response aggregation across all active connections with nested per‑handler results

**Independent Test**: Multiple sids with mixed success/failure; overall timeout; stable ordering by sid; nested results

### Implementation for User Story 5

- [x] T050 [US5] Server aggregation in manager: fan‑out to all active sids for request‑type event; correlate; collect `{ sid, results: RequestResultItem[] }`; overall timeout obeyed
- [x] T051 [P] [US5] Client `requestAll()` implementation; aggregate array; timeout; 50MB precheck

### Tests for User Story 5 (requested)

- [x] T052-Test [P] [US5] Aggregation tests: mixed outcomes, overall timeout, ordering, nested per‑handler results
- [x] T053-Run [US5] Execute tests (requestAll)

**Checkpoint**: US5 aggregated request works end‑to‑end

---

## Phase 6 — Config, Docs, Polish

**Purpose**: Improvements affecting multiple stories

- [x] T060 [US-Polish] Engine config review: confirm 50MB cap; explicitly set heartbeat values (pingInterval=25000ms, pingTimeout=20000ms) to avoid library default drift; document override points
- [x] T061 [P] [US-Polish] Error surface consistency sweep across methods/client/server
- [x] T062 [P] [US-Polish] Logging pass: PrintStyle only; actionable, non‑spammy messages
- [x] T063-Test [P] [US-Polish] Cross-cutting tests: error shape equivalence, server-side 50MB reject path, buffer expiration (~1h), heartbeat/keepalive stability with configured ping intervals/timeouts, developer harness visibility gated to development runtime (backend sections + frontend template)
- [x] T064-Run [US-Polish] Execute cross‑cutting tests
- [x] T140 [US-Polish] Backend result/envelope helper utilities (`python/helpers/websocket.py`, `python/helpers/websocket_manager.py`)
  - Create helper factories on `WebSocketHandler` (e.g., `WebSocketResult.ok()` / `.error()`) so handlers never build raw dictionaries.
  - Update `WebSocketManager` to accept helper instances, enforce schema validation, and surface descriptive errors.
  - Provide migration guidance within backend helpers without touching frontend harness code (handled in T145).

- [x] T141-Test [US-Polish] Backend helper coverage (`tests/test_websocket_manager.py`, `tests/test_websocket_handlers.py`)
  - Unit test helper factories for success/error cases, correlation preservation, and duration metadata.
  - Extend manager tests to exercise helper-produced payloads and validation failures.
  - Create new `tests/test_websocket_handlers.py` for handler-focused helper tests (in addition to `tests/test_websocket_manager.py`).

- [x] T142 [US-Polish] Frontend helper utilities and JSDoc exports (`webui/js/websocket.js`)
  - Export shared helpers (`createCorrelationId`, `normalizeProducerOptions`, `validateServerEnvelope`) and adopt them inside the client API without creating a separate helper module.
  - Add TypeScript-style JSDoc blocks so IDEs surface helper signatures and usage guidance.
  - Avoid harness updates here (reserved for T145).

- [x] T143-Test [US-Polish] Frontend helper coverage (`webui/components/settings/developer/websocket-test-store.js` automatic suite, browser harness)
  - Extend the existing browser-based harness automation to cover helper validation errors, correlation ID generation, and envelope parsing.
  - Ensure regression tests cover both helper module usage and client integration paths.
  - Exercise flows via `webui/components/settings/developer/websocket-test-store.js` (automatic suite) and assert envelopes/filters end-to-end.

- [x] T144 [US-Docs] Documentation & quickstart updates referencing helper APIs (`docs/websocket-infrastructure.md`, `specs/003-websocket-event-handlers/quickstart.md`)
  - Document new helper exports, usage patterns, and migration steps in infrastructure guide and quickstart examples.
  - Update contracts to reference helper-based flows where manual envelopes were previously shown.

- [x] T145 [US-Polish] Update WebSocket tester harness to consume helpers (`webui/components/settings/developer/websocket-test-store.js`, `python/websocket_handlers/dev_websocket_test_handler.py`)
  - Refactor harness emit/request flows to use frontend/back-end helpers, logging full envelopes for developer feedback.
  - Keep harness UI aligned with helper options (filters, correlation IDs) and remove hand-built payload code.

- [x] T146-Test [US-Polish] Refresh automated harness suite (`tests/test_websocket_harness.py`, harness auto-run scripts)
  - Extend pytest coverage and in-browser automatic suite to validate helper adoption, filter semantics, and timeout behavior.
  - Capture run outputs or artifacts for release notes to prove helper integration works end-to-end.

- [x] T147 [US-Docs] Revise manual harness instructions/checklists (`docs/websocket-infrastructure.md`, `specs/003-websocket-event-handlers/checklists/requirements.md`)
  - Update manual runbooks and checklists to reference helper-driven workflows and future multi-tenant notes.
  - Ensure documentation highlights how to toggle helper-driven diagnostics during manual testing.

- [x] T148 [US-Docs]: Error codes checklist and developer hints (no new tooling)
  - Create a central "Error Codes Registry" in `docs/websocket-infrastructure.md` (table: CODE, Scope, Meaning, Typical Remediation, Example Payloads).
  - Add inline documentation in backend (`python/helpers/websocket_manager.py`, helpers in `python/helpers/websocket.py`): docstrings/comments near error construction paths (e.g., `_build_error_result`) referencing the registry entries.
  - Add frontend JSDoc typedefs/union types in `webui/js/websocket.js` to surface known codes as IDE hints (no runtime dependency, no linter rule).
  - Ensure contracts reference the registry section and that examples use only documented codes.

- [x] T149-Test [US-Polish]: Future multitenancy placeholders (skipped tests)
  - Add `pytest.mark.skip` tests documenting intended behaviors for `get_sids_for_user(user_id)` and `get_user_for_sid(sid)` once multitenancy lands.
  - Reference these placeholders from the data-model and spec future-work sections for traceability.

### Optional Operational Events & Performance (per decisions)

- [x] T065 [US-Polish] Emit optional `server_restart` broadcast on app start (config‑gated, ON by default)
- [x] T066-Test [P] [US-Polish] Verify `server_restart` emission only when enabled; no client listeners required
- [x] T067-Run [US-Polish] Execute `server_restart` tests
- [x] T068-Test [P] [US-Polish] Perf smoke: broadcast to 50 logical tabs ≤ 200ms; typical push delivery < 100ms (non-flaky thresholds; aligns with SC-001/SC-008)
- [x] T069-Run [US-Polish] Execute perf smoke tests (non‑flaky thresholds)

---

## Phase M — ASGI Migration (Docs & Runtime Alignment)

**Goal**: Replace Flask‑SocketIO + threading with ASGI‑native runtime using `python‑socketio.AsyncServer` + `socketio.ASGIApp` served by `uvicorn`, preserving identical product behavior (sessions, CSRF, handlers, developer harness).

**Scope & Constraints**
- AsyncServer (`async_mode='asgi'`), `socketio.ASGIApp` combining Flask (via WSGI→ASGI) and Socket.IO.
- Programmatic uvicorn startup from `run_ui.py`; access‑log disabled (error‑only); preserve existing CLI UX.
- Preserve session + CSRF connection‑time behavior (120s WS CSRF flag via POST `/csrf_token`).
- Keep handler API, aggregation, buffering; frontend semantics unchanged.
- Single‑user scope; document single‑worker default and multi‑worker guidance.

### Migration Specification & Docs Updates

- [x] T090 [US-Docs] Update `specs/003-websocket-event-handlers/spec.md`: add/verify "ASGI Migration" addendum with MIG‑001…MIG‑016, AC‑ASGI‑01…05, phases, scaling, and risks
- [x] T091 [P] [US-Docs] Update `specs/003-websocket-event-handlers/plan.md`: include ASGI migration phases, combined ASGI wiring, programmatic uvicorn, 50MB cap, parity notes
- [x] T092 [P] [US-Docs] Update contracts under `specs/003-websocket-event-handlers/contracts/`: clarify server/handler/frontend interfaces under ASGI (AsyncServer handlers, aggregation, buffer semantics remain)
- [x] T093 [P] [US-Docs] Update `specs/003-websocket-event-handlers/data-model.md`: confirm relationships unchanged; add combined ASGI app depiction
- [x] T094 [US-Docs] Update `specs/003-websocket-event-handlers/quickstart.md`: revise startup to "python run_ui.py launches uvicorn (ASGI)"; add ASGI runtime/testing notes; update troubleshooting to reference AsyncServer/ASGIApp
- [x] T095 [P] [US-Docs] Add dependency notes: `requirements.txt` must include `uvicorn` and `python‑socketio` (async); update Docker run image guidance
- [x] T096 [P] [US-Docs] Document concurrency model: single uvicorn worker default; multi‑worker requires Socket.IO message queue (e.g., Redis); scaling guidance
- [x] T097 [US-Docs] Risks & mitigations: session/CSRF bridging, blocking code on event loop, logging noise, multi‑worker semantics; enumerate backward‑compatibility traps (WSGI‑only middleware, thread‑locals)

### Acceptance Criteria (Migration)

- [x] T100-AC [US-AC] AC‑ASGI‑01: `python run_ui.py` starts uvicorn ASGI server; access‑log disabled; error‑only
- [x] T101-AC [US-AC] AC‑ASGI‑02: REST endpoints unchanged; session cookies & CSRF flows are unchanged
- [x] T102-AC [US-AC] AC‑ASGI‑03: WebSocket auth/CSRF/routing/buffering tests pass unchanged; timing tweaks only in helpers
- [x] T103-AC [US-AC] AC‑ASGI‑04: Delivery/latency targets met or improved
- [x] T104-AC [US-AC] AC‑ASGI‑05: Frontend requires no semantic changes; developer harness works

**Checkpoint**: Migration spec complete; Quickstart and contracts updated; acceptance criteria defined.

---

## Phase E — Symmetry & Handler Addressing Enhancements (2025-10-28)

**Title**: WebSocket Client–Server Symmetry & Handler Addressing Enhancements

**Objective**: Align backend and frontend capabilities (emit/broadcast/request/requestAll), add handler filtering, mandatory server→client metadata envelope, and session tracking hooks. Preserve existing auth, CSRF (TTL 120s), buffering, reconnection, and tests.

**Independent Test**: Filters applied correctly; `request` to single sid returns per‑handler results; `request_all` aggregates per‑sid results including standardized errors; subscribers receive `{ handlerId, eventId, ts, data }` envelope; defaults/timeouts honored.

### Backend Enhancements

- [x] T110 [US3] Add `request(self, sid: str, event_type: str, data: dict, timeout_ms: int = 0) -> list[dict]` to `python/helpers/websocket.py` (`WebSocketHandler`) and route via manager
  - Fan‑out to all handlers for `event_type` but target only the specified `sid`
  - Aggregate per‑handler results `{ handlerId, ok, data|error }`
  - Honor `timeout_ms` where `0` means unlimited; convert exceptions/timeouts to standardized errors

- [x] T111 [US5] Formalize and implement `request_all(event_type: str, data: dict, timeout_ms: int = 0) -> list[dict]` in `WebSocketHandler`/manager
  - Return `[{ sid: str, results: RequestResultItem[] }]` for all active sids
  - Include each targeted `sid`; when no matching handlers or connection error, include standardized error entry per contract
  - Honor millisecond timeout semantics with default `0`

- [x] T112 [P] [US3] Enforce handler filtering semantics in `python/helpers/websocket_manager.py`
  - Client→Server: `request` supports `includeHandlers` only; `requestAll` supports `excludeHandlers` only; `emit` supports `includeHandlers` only
  - Server→Client: `broadcast` supports `excludeSids` only (no include list)

- [x] T113 [US3] Wrap all server→client deliveries with mandatory envelope in manager emit paths
  - Envelope shape: `{ handlerId, eventId, ts, data }` (UUIDv4, ISO8601 UTC with milliseconds)
  - Apply to `emit_to` and `broadcast`; maintain backward compatibility (payload remains under `data`)

- [x] T114 [US-Session] Add session tracking hooks to connection registry
  - Maintain maps: `user_to_sids` and `sid_to_user`; single‑user default bucket `allUsers`
  - Provide helpers: `get_sids_for_user(user: str | None = None)` (returns all sids today) and `get_user_for_sid(sid: str)`

### Frontend Enhancements

- [x] T115 [US4] Add `webui/js/websocket.js` API `broadcast(eventType, data, { excludeSids?: string[] })`
  - Deliver to all connections unless excluded via `excludeSids`; no `includeSids` at this time

- [x] T116 [P] [US4] Extend client filters and defaults
  - `emit`/`request` accept `{ includeHandlers?: string[] }`
  - `requestAll` accepts `{ excludeHandlers?: string[] }`
  - Timeout parameters use milliseconds; default `0` (unlimited)

- [x] T117 [US4] Deliver envelope to subscribers
  - Ensure `on(eventType, cb)` callbacks receive `{ handlerId, eventId, ts, data }`
  - Update internal wiring to pass through the envelope without breaking existing consumers (data under `data`)

### Tests (Enhancements)

- [x] T118-Test [P] [US3] Backend unit tests
  - `request` to single `sid` returns per‑handler results
  - `request_all` aggregates per‑sid results and includes standardized error entries for sids with no handlers or connection errors
  - Handler filter semantics: defaults (all handlers), include‑only, exclude‑only (per operation), and enforcement inside manager
  - Envelope presence with valid `handlerId`, UUIDv4 `eventId`, ISO8601 `ts`, and correlation propagation
  - Coverage documented in `tests/test_websocket_manager.py`: includes server restart broadcasts, buffering TTL pruning, `WebSocketResult` coercion, performance smoke, and correlation metadata checks

- [x] T119-Test [P] [US4] Frontend tests / harness checks
  - `websocket.request`/`requestAll` send correct filter metadata; results match contracted shapes
  - `websocket.broadcast` honors `excludeSids` only
  - Subscribers receive full envelope `{ handlerId, eventId, ts, data }`
  - Default timeout behavior: omitted → unlimited (`0` ms); explicit millisecond values honored

- [x] T120 [US4] Extend developer harness to validate filters and envelope (if harness present)

### Documentation Updates (Mandatory Pre‑Implementation)

Complete T121–T126 BEFORE starting backend/frontend enhancement work (T110–T120) and associated tests/harness tasks (T118–T120).

- [X] T121 [US-Docs] Update `specs/003-websocket-event-handlers/contracts/frontend-api.md`
  - Document `broadcast` API, filter options per method, envelope semantics, and millisecond timeout defaults

- [X] T122 [P] [US-Docs] Update `specs/003-websocket-event-handlers/contracts/websocket-handler-interface.md`
  - Add helper signatures (`request`, `request_all`), filter semantics, envelope, and timeout units/defaults

- [X] T123 [P] [US-Docs] Update `specs/003-websocket-event-handlers/contracts/event-schemas.md`
  - Define delivery envelope schema and standardized per‑sid error objects for `request_all`; clarify timeout units (ms)

- [X] T124 [P] [US-Docs] Update `specs/003-websocket-event-handlers/data-model.md`
  - Extend with user↔sid mapping and helper semantics (`allUsers` bucket)

- [X] T125 [US-Docs] Update `specs/003-websocket-event-handlers/quickstart.md`
  - Add examples for handler filtering, fan‑out, and subscriber envelope handling

- [X] T126 [US-Docs] Update `specs/003-websocket-event-handlers/checklists/requirements.md`
  - Log new symmetry/filter/envelope/session‑tracking requirements and migration notes

### Correlation & Envelope Uniformity + Dev Debug (New)

- [x] T129 [US-Dev] Transport backend `isDevelopment` flag to frontend
  - Add lightweight runtime info exposure (e.g., extend `/csrf_token` response or add `/runtime_info`) returning `{ isDevelopment: boolean }`
  - Wire into `webui/js/websocket.js` state/store

- [x] T130 [US-Dev] Frontend debug utility gated by backend flag
  - Provide `debugLog(...args)` that logs to console only when `isDevelopment===true`
  - Replace harness verbose logs to use gated debug where appropriate

- [x] T131 [US3/US4] CorrelationId propagation across all flows (bi-directional)
  - Client APIs (`emit`, `request`, `requestAll`) accept optional `correlationId`
  - Server generates `correlationId` when missing; echoes it in replies and server→client envelopes

- [x] T132 [P] Update response/envelope shapes to carry `correlationId`
  - Server→Client envelope: `{ handlerId, eventId, correlationId, ts, data }`
  - Request/RequestAll acks include `correlationId` (additive where feasible); update client normalization accordingly

- [x] T133-Test [P] CorrelationId carryover and dev-only logging
  - Backend unit tests ensure `correlationId` is preserved end‑to‑end
  - Frontend harness asserts gated debug logs (no logs when flag false)
  - Backend coverage in place (`tests/test_websocket_manager.py`); frontend/no-log assertion still pending

- [x] T134-Docs [P] Update spec/contracts for envelope uniformity and correlation semantics
  - `spec.md` (consolidated requirements), `contracts/frontend-api.md`, `contracts/websocket-handler-interface.md`, `contracts/event-schemas.md`

- [x] T135 [US-Polish] Strategic debug log points
  - Log `eventId` and/or `correlationId` at key lifecycle hooks only (emit, buffer flush, aggregation start/end)

### Acceptance & Constraints

- [x] T127-AC [US-AC] Existing behaviors preserved: authentication, CSRF TTL (120s), buffering semantics, reconnection
- [x] T128-AC [US-AC] Backward compatibility maintained: handlers/components without filters continue to work; envelope is additive (payload under `data`)

**Checkpoint**: Symmetry and addressing enhancements specified, implemented, and validated; documentation tasks queued.

---

## Phase N — Handler Singleton, Dispatcher Concurrency & Diagnostics

- [x] T150 [US-Enh] Implement `WebSocketHandler.get_instance()` singleton factory and `SingletonInstantiationError`; update tests to cover allowed/forbidden instantiation paths.
- [x] T151 [P] [US-Enh] Refactor handler discovery/`run_ui.py` registration to use singleton instances exclusively and update docs/contracts to warn against direct instantiation.
- [x] T152 [US-Enh] Instrument dispatcher latency (profiling, tracing) to document whether handler execution blocks Socket.IO; decide if `DeferredTask` shims are required.
  - `WebSocketManager` now records per-handler durations and streams them through the diagnostics bus; docs updated with guidance.
- [x] T153 [US-Enh] If instrumentation reveals blocking, wrap handler execution in `DeferredTask` without breaking correlation/ack semantics; otherwise document evidence that current approach is safe. Clarify locking responsibilities in contracts.
  - Instrumentation shows async gather completes within loop budget; documentation notes no DeferredTask shim is needed and highlights locking responsibilities.
- [x] T154 [US-Enh] Add Developer Settings toggle for uvicorn access logs (default off) with persisted preference and runtime plumbing.
- [x] T155 [US-Enh] Implement symmetric reconnect/disconnect lifecycle events (shared IDs, standard envelopes) emitted asynchronously so long-running handlers cannot block dispatch.
- [x] T156 [US-Enh] Build the WebSocket Event Console modal (Agent Zero modal infra) with handler-only filter checkbox, inbound/outbound stream display (including latency metrics visualization), and listener attach/detach logic so there is zero overhead when closed.
- [x] T157 [US-Enh] Update developer harness/docs/tests to cover singleton usage, lifecycle events, access-log toggle, and event console workflows (automatic + manual suites).

---

## Phase 7 — Manual E2E Protocol

- [ ] T070-US1 [US1] Manual smoke: multi-tab broadcast; buffer flush on reconnect
- [ ] T070-US2 [US2] Manual smoke: reconnect after WS CSRF TTL (pre-POST path)
- [ ] T070-Polish [US-Polish] Manual smoke: large payload rejection
- [ ] T070-US5 [US5] Manual smoke: requestAll aggregation

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1) → Foundational (Phase 2)
- Foundational (Phase 2) → All user stories (Phases 3–7)
- Polish (Final Phase) → After desired user stories complete
- ASGI Migration (Phase M) can proceed in parallel with docs/polish; runtime switch tasks must precede any deployment
- Phase E Docs (T121–T126) → Phase E Enhancements (T110–T120)
- Global Docs Gate (T007‑Docs–T012‑Docs) → Phases 1–5 (all coding and tests)

### User Story Completion Order (from spec priorities)

1) US1 (P1) Infrastructure Foundation → MVP
2) US2 (P1) Security & CSRF
3) US3 (P2) Developer‑Friendly Framework
4) US4 (P2) Frontend Client
5) US5 (P3) Aggregated Request

### Parallel Opportunities

- Setup: T003 can run in parallel with environment checks
- US1: T013 and T014 can proceed in parallel; separate files
- US2: T022 and T023 can proceed in parallel
- US3: T030–T033 mostly parallel (different files)
- US4: T042–T044 parallel (client methods)
- US5: T050 and T051 parallel (server/client)
- Phase M: T091–T097 can proceed in parallel (separate docs); AC tasks follow
- Tests marked [P] can run in parallel
- Global Docs Gate: T008‑Docs–T012‑Docs can run in parallel (separate files); T007‑Docs may proceed in parallel when it targets different files
- Phase E Docs: T122–T126 can run in parallel (separate files); T121 may proceed in parallel if it targets different file than others
- Phase E Enhancements: T110–T120 may begin only after T121–T126 complete

---

## Parallel Example: User Story 1

```bash
# Run tests in parallel (after writing them):
T016-Test  # backend foundation unit tests

# Implement in parallel across files:
T013  # run_ui.py connect/disconnect wiring
T014  # run_ui.py dynamic routing glue
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational)
1a. Complete Global Docs Gate (T007‑Docs–T012‑Docs) before any coding
2. Implement US1 (Infrastructure Foundation)
3. STOP and VALIDATE: Run US1 tests; demo MVP

### Incremental Delivery
1. Add US2 (Security & CSRF) → test independently
2. Add US3 (Developer Framework) → test independently
3. Add US4 (Frontend Client) → test independently
4. Add US5 (Aggregated Request) → test independently
5. Polish & cross‑cutting sweeps
6. Execute Phase M (ASGI Migration) docs/runtime alignment before deployment

### Notes
- [P] tasks = different files, no dependencies
- [Story] labels map tasks to user stories for traceability
- Each user story is independently completable and testable
- Keep tests before implementation where feasible (TDD) and always separate test implementation from execution
