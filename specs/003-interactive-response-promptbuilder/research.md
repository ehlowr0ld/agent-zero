# Research: InteractiveResponse + PromptBuilder

Date: 2025-10-30
Branch: 003-interactive-response-promptbuilder
Spec: /home/rafael/Workspace/Repos/rafael/a0-local/specs/003-interactive-response-promptbuilder/spec.md

## Decisions

1) Select shape + synthetic variables (uniformity)
- Decision: Single-select → scalar; Multi-select → array; Synthetic per-option booleans `<id>_<optionId>` and mapping `<id>_selected` for BOTH single and multi; Checklist gains `<id>_selected`.
- Rationale: Uniform Jinja ergonomics; simple `if` checks without loops; preserves canonical value.
- Alternatives: Always-array (more noise in single-select), join to string (lossy), no synthetic vars (more complex templates).

2) Callback union: prompt | tool
- Decision: Support `{ kind: "prompt", template }` or `{ kind: "tool", tool_name, args_template }`. `args_template` renders to JSON, parsed server-side and executed via existing tool system.
- Rationale: Keeps agent workflow intact while allowing IR to trigger tools; server-side execution is secure and auditable.
- Alternatives: Only prompt (limited), client-side tool exec (security violation), dual-dispatch (adds complexity).

3) Tool callback freeze behavior
- Decision: Freeze IR after successful dispatch to the tool (i.e., after render + args parsed + enqueued). On error (parse/tool-not-found), keep IR interactive with inline error.
- Rationale: Prevent duplicate submissions while providing recoverable UX for errors.
- Alternatives: Freeze on click (risk of dead-end on error), freeze after tool completes (allows double-submit during processing).

4) Idempotency key
- Decision: Frontend generates UUIDv4 per submit; included in POST; backend enforces idempotent behavior for both prompt and tool callbacks.
- Rationale: Simple, consistent, avoids double execution on retries.
- Alternatives: Server-generated keys (extra round-trip), no keys (risk of duplication).

5) Missing variable policy for PromptBuilder
- Decision: Default "error on missing" with friendly message listing variables; IR remains interactive for correction.
- Rationale: Encourages explicitness and prevents silent prompt defects.
- Alternatives: Null default (silent issues), placeholder tokens (leak into output).

6) Safe HTML subset for `text` element
- Decision: Allow tags: a, p, br, strong, em, code, pre, ul, ol, li, blockquote. Attributes: href (http/https), target=_blank, rel=noopener noreferrer. Disallow inline styles and events.
- Rationale: Prevent XSS; readable copy.
- Alternatives: Markdown-only (would require converter), broader HTML (higher risk).

7) ARIA & accessibility
- Decision: Labels tied via `for`/`id`; roles for groupings (e.g., `role="group"`); keyboard tabbable submit; focus management on prefill.
- Rationale: Basic accessibility without over-engineering.
- Alternatives: Extensive ARIA patterns (defer to future pass if needed).

8) Python minor version (execution environment)
- Decision: RESOLVED → Python 3.12 (active `.venv`).
- Rationale: Align with plan.md and current project baseline; avoid drift.

## Patterns and Integrations

- ApiHandler: New endpoints under `python/api/` auto-registered; CSRF/loopback/auth via decorators; async discipline.
- Tool execution: Use existing tool system (`python/tools/*`), server-side only; PrintStyle logging.
- Frontend: Alpine.js component renders IR; submission via `callJsonApi()`; idempotency and validation.
- Jinja rendering: Backend-only using installed Jinja2; no filesystem includes.

## Open Questions (to resolve before implementation)

- (none)
- Finalize exact UI copy for error messages (Jinja errors, tool-not-found) → Copy pass.

## References

- Constitution: /home/rafael/Workspace/Repos/rafael/a0-local/.specify/memory/constitution.md
- Feature Spec: /home/rafael/Workspace/Repos/rafael/a0-local/specs/003-interactive-response-promptbuilder/spec.md
