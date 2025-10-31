# Tasks: InteractiveResponse + PromptBuilder

Date: 2025-10-30
Branch: 003-interactive-response-promptbuilder
Feature Dir: /home/rafael/Workspace/Repos/rafael/a0-local/specs/003-interactive-response-promptbuilder

## Phase 1: Setup

- [ ] T001 Ensure feature branch active (`003-interactive-response-promptbuilder`)
- [ ] T002 Verify OpenAPI contract exists at specs/003-interactive-response-promptbuilder/contracts/iresponse.yaml (rename if needed from interactive_response.yaml)
- [ ] T003 Create frontend component folder webui/components/iresponse/
- [ ] T004 [P] Create component shell webui/components/iresponse/iresponse.html (inline style+script, Alpine component)
 - [ ] T004A [P] Add default prompt template file at `prompts/iresponse/default.md.jinja` with `{{ variables }}` placeholder and concise explanatory text.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T005 Create backend endpoint skeleton python/api/iresponse_submit.py (ApiHandler with POST, auth+csrf)
- [ ] T006 [P] Create helper python/helpers/prompt_builder.py (Jinja render function with missing-variable policy; register `tojson` filter)
- [ ] T007 [P] Create helper python/helpers/iresponse_schema.py (schema validation, id uniqueness, safe HTML allowlist)
- [ ] T008 Add default setting in python/helpers/settings.py for `iresponse_default_submit_behavior` ("auto"|"prefill")
 - [ ] T008A Add configurable setting `iresponse_default_prompt_template` defaulting to `prompts/iresponse/default.md.jinja`.
- [ ] T009 Wire server idempotency handling in python/api/iresponse_submit.py (UUIDv4 header enforcement)
- [ ] T010 [P] Extend python/tools/response.py to recognize IR payloads from tools and route to UI renderer
- [ ] T006A [P] Optional pre-validation: Extract variables referenced in Jinja template and verify corresponding element IDs exist in IR; log actionable warning to model/tool logs on mismatch; fallback to render-time error remains.
- [ ] T031 [P] Implement synthetic variable generation for `select` (single|multi) and `checklist` per FR-026–FR-028 in submit collection and shaping (client + server), including `<id>_<optionId>` and `<id>_selected`.
- [ ] T032 [P] Enforce uniqueness and collision rules for synthetic variables (no ID clashes within IR scope) in python/helpers/iresponse_schema.py.

## Phase 3: User Story 1 (P1) — Auto-submit rendered prompt

Goal: Configure IR controls → render Jinja → auto-post as user message → freeze IR

- [ ] T011 [US1] Implement IR element rendering (text/select(single)/input_number/checkbox/button) including container layout (horizontal|vertical) and collapsed toggle in webui/components/iresponse/iresponse.html; for horizontal layout use flex row with wrap and gap; fallback to vertical below ~480px.
- [ ] T012 [P] [US1] Implement submit collection + POST to /iresponse/submit in webui/js/messages.js
- [ ] T013 [US1] Implement prompt callback path in python/api/iresponse_submit.py (render, route as user message via history)
 - [ ] T013A [US1] Implement default prompt fallback in python/api/iresponse_submit.py when `callback` is omitted: render `iresponse_default_prompt_template` with `variables` as fenced JSON of IR values and a concise preface; route per submit_behavior.
- [ ] T014 [P] [US1] Add history log entry on submit (PrintStyle) in python/helpers/history.py
- [ ] T015 [US1] Freeze IR bubble on success (read-only view of chosen values) in webui/components/iresponse/iresponse.html
- [ ] T016 [US1] Add idempotency key generation on client (UUIDv4) and include as `X-Idempotency-Key` header in webui/js/messages.js

- [ ] T016A [US1] Implement container collapse/expand UI per `collapsed` flag (default false) with a minimal toggle button (`aria-expanded`, `aria-controls`) and lightweight header; ensure no layout jitter.

Independent Test: Posting a sample IR produces a new user message immediately with rendered text; IR becomes read-only.

## Phase 4: User Story 2 (P2) — Prefill instead of auto-submit

Goal: Render prompt but prefill chat input for review; no auto message

- [ ] T017 [US2] Honor `submit_behavior=prefill` in endpoint response in python/api/iresponse_submit.py
- [ ] T018 [P] [US2] Prefill chat input: append rendered text to existing input (do not delete), focus input, move caret to end (no selection) in webui/index.js
- [ ] T019 [US2] Freeze IR bubble on prefill success in webui/components/iresponse/iresponse.html

Independent Test: Submitting IR in prefill mode places text in input without posting; focus moves to input.

## Phase 5: User Story 3 (P3) — Validation and helpful errors

Goal: Client and server validation; actionable errors without breaking session

- [ ] T020 [US3] Client-side required/min/max/step validation in webui/components/iresponse/iresponse.html
- [ ] T021 [P] [US3] Server-side validation mapping to error payload in python/helpers/iresponse_schema.py
- [ ] T022 [US3] Display inline error messages and block submission in webui/components/iresponse/iresponse.html
- [ ] T023 [US3] Duplicate id / unknown element type detection with user-facing error in python/helpers/iresponse_schema.py

- [ ] T023A [US3] Enforce presence of at least one `button` with `role="submit"` in python/helpers/iresponse_schema.py; actionable error when missing.

Independent Test: Invalid inputs block submit with clear copy; fixing allows submit.

## Phase 6: Cross-Cutting & Tool Callback (from FR-029..FR-034)

- [ ] T024 Implement tool callback branch in python/api/iresponse_submit.py (render args_template → JSON → dispatch tool)
- [ ] T025 [P] Add tool registry validation + error codes in python/api/iresponse_submit.py
- [ ] T026 [P] Frozen summary for dispatched tool in UI (status chip) in webui/components/iresponse/iresponse.html
- [ ] T027 Centralize sanitized tool info logging in python/tools/response.py; also log errors/warnings in python/api/iresponse_submit.py

## Phase 7: Accessibility, Safety, Polish

- [ ] T028 Enforce safe HTML allowlist (tags/attrs) in python/helpers/iresponse_schema.py
- [ ] T029 [P] Bind labels/aria roles; keyboard navigation; submit via Enter where applicable in webui/components/iresponse/iresponse.html
- [ ] T030 [P] Document IR spec and examples in specs/003-interactive-response-promptbuilder/quickstart.md (ensure parity)

- [ ] T043 Refactor iresponse component to minimize inline style attributes; use component-scoped CSS classes for active vs frozen states and collapsed container visuals.
- [ ] T044 Add tests/visual checks to verify CSS-driven states (active/frozen, collapsed/expanded) apply correctly without inline styles.

## Phase 8: Coverage and Spec Parity (FR-018, FR-019, FR-031–FR-034)

- [ ] T033 Add unit tests covering variable shapes and synthetic variables (FR-026–FR-028) for select/checklist in tests/unit/test_iresponse_schema.py.
- [ ] T034 Add API security tests for CSRF header/cookie, loopback restriction, and auth on /iresponse/submit (constitution III, VII) in tests/integration/test_iresponse_submit.py.
- [ ] T035 Apply idempotency key header `X-Idempotency-Key` to tool callback path (FR-033); persist/compare server-side to prevent double execution.
- [ ] T036 Add tests for tool idempotency behavior under retry (same key, same payload → single execution; missing key → allowed retries with server guard).
- [ ] T037 Add optional lightweight client timestamp logging around submit→render→route (non-gating) to observe typical performance (FR-018) without architectural impact.
- [ ] T038 Add a non-gating quality test (skippable) that exercises the flow with mocked render/tool; do not assert strict ≤1.0s, just record metrics.
- [ ] T039 Enforce neutral button exclusion: reject any button whose role ≠ submit in schema validation (FR-019), with unit tests.
- [ ] T040 Define and implement error response schema `{ code, message, details? }` for tool validation/dispatch failures (FR-034); add unit tests for each code (`invalid_args_json`, `unknown_tool`, `validation_error`, `dispatch_failed`).
- [ ] T041 Ensure `submit_behavior` is ignored for `callback.kind = "tool"` (FR-031); add unit/integration tests.
- [ ] T042 Add tests verifying sanitized `tool_args` preview in logs and frozen summary (FR-032) using the secrets system and PrintStyle masking; ensure secret-like values are redacted.

- [ ] T045 Add tests enforcing FR-024 (at least one submit-role button required) in tests/unit/test_iresponse_schema.py and tests/integration/test_iresponse_submit.py.

## Dependencies (story order)

1) US1 → 2) US2 → 3) US3
Foundational (Phase 2) precedes all. Cross-Cutting/Tool Callback can proceed after Phase 2 and US1 (endpoint and core flow).

## Parallelization Examples

- UI vs Backend: T011/T012/T015 can run in parallel with T013/T014 after T005–T007.
- Safety/ARIA: T028–T029 can run in parallel after basic rendering (T011) exists.
- Tool callback: T024–T027 can run after T005/T006/T009 and independent of US2/US3.

## Implementation Strategy

- MVP: Complete Phases 2 + 3 (Foundational + US1).
- Iteration 2: Phase 4 (US2).
- Iteration 3: Phase 5 (US3).
- Iteration 4: Phase 6 + 7 (Tool callback & polish).
