# Feature Specification: InteractiveResponse + PromptBuilder

**Feature Branch**: `003-interactive-response-promptbuilder`
**Created**: 2025-10-30
**Status**: Draft
**Input**: User description: "InteractiveResponse + PromptBuilder integration for Agent Zero"

## Clarifications

### Session 2025-10-30
- Q: What shape should select element variables take, especially for multi-select?
  → A: See FR-026–FR-028 for the authoritative contract on select/checklist value shapes and synthetic variables. Briefly: single-select returns a scalar; multi-select returns an array; per-option booleans and `<elementId>_selected` mappings are provided for both; IDs must remain unique within the IR bubble.

- Q: Should the IR submit callback support a tool invocation instead of (or in addition to) a prompt?
  → A: Yes. Add a callback union allowing either a prompt (Jinja template) or a tool (tool name + Jinja args template rendering to JSON). Tool execution is routed through the Agent tool system server-side and logged in history.

## User Scenarios & Testing (mandatory)

### User Story 1 - Submit IR to auto-send rendered prompt (Priority: P1)

A developer agent emits an InteractiveResponse (IR) bubble with simple controls (e.g., select, checkbox, number input) and a Jinja template. The user configures options and clicks a submit button. The system renders a prompt via PromptBuilder and automatically posts it as a user message.

**Why this priority**: Delivers core value in one action: agent-guided configuration → generated prompt → conversation continues.

**Independent Test**: From an agent tool call, render an IR with tone/length/checkbox controls. On submit, verify a new user message appears with rendered text matching selected options.

**Acceptance Scenarios**:

1. Given an IR bubble with valid controls and a submit-role button, When the user clicks submit, Then a user message is appended with the Jinja-rendered text using current control values.
2. Given an IR bubble with valid defaults, When the user hits submit without changing values, Then the prompt renders and is auto-submitted as a user message.
3. Given a successful submit, When the message is posted, Then the originating IR bubble becomes read-only and submit controls are removed.

---

### User Story 2 - Prefill IR output into input box (Priority: P2)

An agent emits an IR that requests user review before sending. The user configures options and submits. The rendered prompt is placed into the chat input for editing; the user may modify and send.

**Why this priority**: Supports review-and-edit workflows for sensitive prompts or longer text.

**Independent Test**: Render an IR with submit_behavior=prefill. On submit, confirm chat input is prefilled with the rendered text and no user message is auto-posted.

**Acceptance Scenarios**:

1. Given an IR with submit_behavior=prefill, When the user submits, Then the chat input is populated with the rendered string, focus moves to the input, and the IR bubble is frozen.
2. Given a prefilled input, When the user presses send, Then a standard user message is sent and the conversation continues normally.

---

### User Story 3 - Validation and helpful errors (Priority: P3)

Required fields and numeric ranges are enforced. Invalid submissions are blocked with clear inline messages. Schema errors (e.g., duplicate IDs, unknown element types) surface actionable errors without breaking the session.

**Why this priority**: Prevents bad prompts and improves trust.

**Independent Test**: Provide an IR with a required empty input; verify submit is blocked and error copy is shown; fix input and resubmit successfully.

**Acceptance Scenarios**:

1. Given a required field is empty, When the user clicks submit, Then the UI highlights the field and shows a validation message; no submission occurs.
2. Given a numeric control outside min/max, When the user clicks submit, Then the UI indicates the constraint and prevents submission.
3. Given a schema violation (duplicate element ids or unknown type), When the IR is processed, Then an actionable error is shown and the bubble is not interactive.

---

### Edge Cases

- Duplicate element ids within a single IR bubble must be detected and rejected with a clear error.
- Unknown element types or malformed schemas must be rejected with an actionable error message; bubbles remain non-interactive.
- Jinja rendering errors (e.g., missing variable under current policy) must surface a friendly error; the IR remains interactive to allow corrections and resubmission; no user message is posted.
- Submit without any submit-role button is invalid IR; show actionable error.
- Submissions during connectivity hiccups must not double-post; retries must be idempotent.
- Network interruption between submit and render must not lose state; resume or present retry without duplicating messages.
- Large templates or long text outputs must not freeze the UI; maintain responsiveness and show progress where applicable.
- User switches chat/context before submit completes; ensure result is routed to the originating thread or canceled with a notice.
- Unsafe HTML provided in text elements must be sanitized; no JavaScript or event handlers may execute.

### Error Messages (guidance)
- Missing submit button (FR-024): "This interactive response is invalid: it has no submit button."
- Missing template variables (FR-013): "Missing variables: {list}. Please update fields and try again."
- Unknown tool (FR-034): "Cannot dispatch: tool '{name}' not found."
- Synthetic variable ID collision (FR-028/FR-005): "ID collision: synthetic variable '{id}' conflicts with an element ID."

## Requirements (mandatory)

### Functional Requirements

- FR-001: Allow agents to return an InteractiveResponse (IR) JSON payload that renders an interactive chat bubble containing an ordered list of elements and an optional top-level submit_behavior ("auto" | "prefill"). The IR may omit an explicit callback; if omitted, the system must use a default prompt template (see FR-035).
- FR-002: Support element types at minimum: text, container, button (role=submit), checkbox, checklist, select (single|multi), input_text, input_number (min/max/step), toggle, slider, divider. Preserve element order.
- FR-003: Containers must support layout=vertical|horizontal (default vertical), collapsed (default false), and children[]; containers affect only child layout, not ordering. Collapsible containers MUST render a toggle affordance (header/label) that expands/collapses their children without reflow glitches.
- FR-004: Submission must be triggered by a button with role=submit. On submit, collect all leaf control values (including false/empty) and include the triggering submit_action_id if provided.
- FR-005: Only leaf controls produce variables. Element id values must be unique within a single IR bubble and map 1:1 to PromptBuilder variable IDs (identical names).
- FR-006: Invoke PromptBuilder with the provided template and collected variables {id, value}; return the rendered string.
- FR-007: Support per-IR submit_behavior with values auto (default) and prefill.
  - auto: immediately inject rendered text as a new user message.
  - prefill: place rendered text into the input box without sending.
- FR-008: After a successful submit (render + route/prefill success), freeze the originating IR bubble to a read-only representation; remove submit buttons.
- FR-009: Validate IR schema: reject unknown element types, missing required fields, or duplicate ids; present actionable errors without breaking the conversation.
- FR-010: Validate user inputs client-side when feasible (required, numeric ranges, step) and server-side for integrity; block submission on failure and show inline error messages.
- FR-011: text elements may allow a safe HTML subset; block inline JavaScript, event handlers, and unsafe attributes.
- FR-012: PromptBuilder must support standard Jinja features as provided by installed packages (control flow, filters, tests, macros, includes, inheritance). No filesystem includes or external file access at runtime.
- FR-013: Configure missing-variable policy in PromptBuilder; v1 default is error with an informative message naming the missing variable(s).
- FR-014: Log (session-scoped) submission events and schema/validation errors, including submit_action_id; avoid leaking secrets to the UI.
- FR-015: Provide a global default submit_behavior in settings; honor per-IR overrides. The settings key is `iresponse_default_submit_behavior`.
- FR-016: Complete the IR → submit → render → route flow in a single user action (one click/tap) for the auto path.
- FR-017: Provide basic accessibility with labels bound to controls and proper ARIA roles where applicable; ensure keyboard navigation through controls and submit.
- FR-018: Rendering performance must remain responsive for ≤10 elements per IR; target end-to-end submit → render → route latency under 1.0s in typical conditions. Provide instrumentation hooks to measure client-perceived latency during tests.
- FR-019: Exclude non-submit (neutral) buttons in v1. The schema validator must reject any `button` element whose `role` is not `submit`.
- FR-020: Enforce allowed HTML whitelist for text.html=true:
  - Allowed tags: a, p, br, strong, em, code, pre, ul, ol, li, blockquote.
  - Allowed attributes: href (http/https only), target=_blank, rel=noopener noreferrer on links.
  - Disallowed: style attributes, inline event handlers, script, iframe, img, form, audio/video, data: URLs.
- FR-021: Ensure idempotent submission via a client-provided idempotency key to prevent double-posting on retries. The key MUST be provided in the `X-Idempotency-Key` header and apply uniformly to both prompt and tool callback paths.
- FR-022: In prefill mode, after successful render, append the rendered text to any existing input content, focus the chat input, and move the caret to the end (no selection).
- FR-023: If render fails (e.g., Jinja error or policy violation), show an inline error and keep the IR interactive for correction and retry; do not freeze or post/prefill.
- FR-024: Reject IRs lacking at least one role=submit button with an actionable error; do not render as interactive.
- FR-025: For checklist elements, each option produces a distinct variable using its option id; for select elements, variables reflect selected options’ values.

- FR-026: Select variable shapes and synthetic variables
  - If `multi=false`: variable `<id>` is the selected option’s value (scalar).
  - If `multi=true`: variable `<id>` is an array of selected option values.
  - Additionally for both single- and multi-select, generate synthetic boolean variables `<id>_<option.id>` indicating selection per option, and a compound mapping variable `<id>_selected` = `{ [option.id]: true|false }`.

- FR-027: Checklist compound mapping for parity with select
  - In addition to per-option variables (FR-025), also provide compound mapping `<id>_selected` = `{ [option.id]: true|false }`.

- FR-028: Synthetic variable semantics
  - Synthetic variables use boolean values (`true|false`) and must not collide with other element IDs (uniqueness enforced at IR scope).
  - Synthetic variables are optional to consume; the primary `<id>` variable remains the canonical value (scalar/array) per FR-026.

- FR-029: IR submit callback union (prompt | tool)
  - The IR may specify zero or one callback via a `callback` object with `kind` field:
    - `kind: "prompt"` → `{ kind: "prompt", template: string }`
    - `kind: "tool"` → `{ kind: "tool", tool_name: string, args_template: string }`
  - If `callback` is omitted, the system must render a default prompt template per FR-035.
  - `args_template` is a Jinja template rendered with IR variables; the rendered string MUST be valid JSON and parse to an object used as `tool_args`.

- FR-030: Tool callback execution routing
  - On submit with `callback.kind = "tool"`, the backend renders `args_template`, validates/parses JSON, and enqueues execution through the Agent tool system (not from the browser). The tool result is added to history via standard tool lifecycle hooks.
  - If the tool is not found or JSON parsing fails, show an actionable error inline and keep the IR interactive.

- FR-031: Prompt callback submit_behavior scope
  - `submit_behavior` applies only to `callback.kind = "prompt"` (auto | prefill). For `kind = "tool"`, `submit_behavior` is ignored.

- FR-032: Visibility & logging
  - For `kind = "tool"`, log a concise entry including `tool_name` and a sanitized preview of `tool_args` (no secrets) in session logs; add a frozen summary in the originating IR bubble.
  - Sanitization MUST follow the Agent Zero secrets architecture and PrintStyle masking policy (e.g., masking values matching secret patterns/registered keys), ensuring no secret material is logged or rendered in UI.

- FR-033: Idempotency for tool callbacks
  - Respect the same idempotency key policy (FR-021) for tool callbacks to prevent double execution on retries.

- FR-034: Security and validation for tool callbacks
  - FR-035: Default prompt template fallback
    - When `callback` is omitted, render a default Jinja template located under `prompts/iresponse/default.md.jinja` (path configurable), following existing prompt naming conventions.
    - The template MUST contain a `{{ variables }}` placeholder where the collected IR values are presented in a highly structured form suitable for LLMs.
    - Variables MUST be injected as a fenced JSON block (e.g., ```json\n{...}\n```), and the surrounding text must concisely state that these are the user’s choices in the InteractiveResponse dialog.
    - The default template path may be overridden via settings; absence of a valid template MUST surface an actionable error and keep the IR interactive.
  - Validate `tool_name` against available server-side tools. Do not execute unknown tools. Enforce CSRF/authn/loopback protections per existing API patterns.
  - Error response schema for validation/dispatch failures MUST be JSON of shape `{ code: string, message: string, details?: object }` where `code` ∈ { `invalid_args_json`, `unknown_tool`, `validation_error`, `dispatch_failed` }.

### Key Entities (include if feature involves data)

- Variable: { id: string, value: any } — id matches a valid Jinja variable identifier; value is JSON-serializable.
- InteractiveResponse: { elements: Element[], callback?: PromptCallback | ToolCallback, submit_behavior?: "auto"|"prefill" }.
- Element (common): { type: string, id?: string, label?: string, value?: any, disabled?: boolean, required?: boolean, tooltip?: string, default?: any }.
- Container: { type: "container", layout?: "horizontal"|"vertical", collapsed?: boolean, children: Element[] }.
- Text: { type: "text", html?: boolean, content: string } (safe subset only).
- Button: { type: "button", id: string, label?: string, role: "submit", submit_action_id?: string, value?: "clicked" }.
- Checkbox: { type: "checkbox", id: string, label?: string, value: boolean }.
- Checklist: { type: "checklist", options: [ { id: string, label: string, value?: boolean, tooltip?: string } ] } (each option yields its own variable).
- Select: { type: "select", id: string, label?: string, options: [ { id: string, label: string, value: any, selected?: boolean } ], multi?: boolean }.
- Inputs: input_text: { value: string }, input_number: { value: number, min?: number, max?: number, step?: number }.
- Toggle/Slider: toggle: { value: boolean }, slider: { value: number, min?: number, max?: number, step?: number }.
- PromptBuilder: { template: string } → returns { text: string }.
- SubmitResult (internal): { text: string, submit_action_id?: string, variables: Record<string, any> }.

#### Synthetic Variables (derived convenience variables)
- For multi-item controls, additional variables are produced for easier Jinja usage:
  - Per-option booleans: `<elementId>_<optionId>` → `true|false`
  - Compound mapping: `<elementId>_selected` → `{ [optionId]: true|false }`
- Applies to: `select` with `multi=true` and `checklist`.
- Purpose: Enable simple `if` conditions and lookups without looping, while keeping the canonical `<id>` scalar/array contract intact.

#### Callback (union)
- PromptCallback: `{ kind: "prompt", template: string }`
- ToolCallback: `{ kind: "tool", tool_name: string, args_template: string /* renders to JSON */ }`
- InteractiveResponse: `{ elements: Element[], callback?: PromptCallback | ToolCallback, submit_behavior?: "auto"|"prefill" }`

### Edge Cases (additions)
- Tool callback args template renders to invalid JSON → show inline error; IR remains interactive.
- Tool not found or disabled → actionable error; IR remains interactive.
- Tool execution error → surface tool error message in history; IR bubble freezes only after a successful dispatch. The IR remains interactive on any error prior to dispatch (rendering, validation, registry lookup) and on tool dispatch failures.

### Non-Functional Requirements

- NFR-API-Contract: Maintain an OpenAPI contract for new IR endpoints; contract lives under `specs/003-interactive-response-promptbuilder/contracts/` and must be kept in sync with implementation.
- NFR-Logging-Safety: All logs and frozen summaries must redact/omit secrets per Agent Zero secrets system and PrintStyle masking.
- NFR-Performance-Quality: Keep submit → render → route responsive in typical conditions. Performance hooks may be added for observation, but performance checks must not complicate design or become gating; if end-to-end exceeds ~1s consistently, treat as a separate optimization task.
- NFR-Component-Styles: Minimize inline style attributes; prefer component-scoped CSS classes in the component's `<style>` block to drive both active and frozen states for easy restyling. Avoid global CSS files; keep styles self-contained.

## Success Criteria (mandatory)

### Measurable Outcomes

- SC-001: Users complete IR configuration and receive a rendered prompt in ≤1 click action (auto path) with end-to-end latency ≤1.0s in typical conditions.
- SC-002: At least 95% of valid IR submissions succeed without client-visible errors across 200+ submissions in QA.
- SC-003: Prefill mode: 100% of successful submits place the rendered text into the input box without posting a message and move focus to the input.
- SC-004: Validation: 100% of schema/validation errors produce actionable messages without breaking the conversation.
- SC-005: Safety: 0 instances of executable JavaScript or blocked attributes in text elements across 1000+ fuzzed payloads; only the allowed HTML subset is rendered.
- SC-006: After successful submit, the frozen IR displays the user’s chosen values accurately in 100% of test runs.
