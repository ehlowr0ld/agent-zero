# Implementation Plan: InteractiveResponse + PromptBuilder

**Branch**: `003-interactive-response-promptbuilder` | **Date**: 2025-10-30 | **Spec**: `/home/rafael/Workspace/Repos/rafael/a0-local/specs/003-interactive-response-promptbuilder/spec.md`
**Input**: Feature specification from `/specs/003-interactive-response-promptbuilder/spec.md`

**Note**: Generated via `/speckit.plan` workflow.

## Summary

Enable agents to emit InteractiveResponse (IR) bubbles containing simple UI controls. On submit, collected values feed PromptBuilder (Jinja) to render either: (a) a prompt routed as auto/prefill (explicit callback or default template fallback), or (b) a server-side tool call (name + Jinja-rendered JSON args). Elements render top-down, containers control layout only, and IDs map 1:1 to template variables with synthetic per-option booleans and `<id>_selected` maps for uniformity.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12 (venv required)
**Primary Dependencies**: Flask server, Jinja2 (PromptBuilder), Alpine.js (UI), existing Agent Zero tool/ApiHandler framework
**Storage**: N/A (no new persistence)
**Testing**: pytest (unit/integration), manual UI verification in SPA
**Target Platform**: Linux (Docker container runtime), SPA frontend
**Project Type**: web (single-user)
**Performance Goals**: Submit→render→route ≤ 1.0s typical; responsive UI for ≤10 elements
**Constraints**: Non-blocking async; CSRF/auth; server-side tool execution; safe HTML subset; idempotent submits
**Scale/Scope**: Single-user application (no multi-tenancy)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Security-First: ✓ No secrets to frontend; CSRF via existing `fetchApi()/callJsonApi()`; tool execution server-side only.
- Non-Blocking Async: ✓ Backend endpoints async, no `time.sleep()`; use existing async patterns.
- Architectural Boundaries: ✓ New API handlers under `python/api/`; uses `ApiHandler` defaults and tool system; no parallel systems.
- Environment Separation: ✓ No container management from UI; use RFC only if accessing container resources (not planned here).
- PrintStyle Logging: ✓ All logs via PrintStyle; no alternate logging frameworks.
- Self-Contained Components: ✓ UI as Alpine components with inline CSS/JS; no global CSS additions.
- Dual Communication Channels: ✓ Rely on HTTP polling for this feature; no WebSocket dependency.
- Project Scope & Simplicity: ✓ Single-user; no roles, multi-tenancy, or enterprise theater.

Gate Status: PASS

Post-Design Recheck: PASS (no new violations introduced by Phase 0/1 artifacts)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
python/
├── api/
│   └── iresponse_submit.py                    # ApiHandler endpoint
├── helpers/
│   ├── iresponse_schema.py                    # schema + safe HTML + ID rules
│   └── prompt_builder.py                      # Jinja render + missing-var policy
└── tools/
    └── response.py                            # IR routing/logging hooks (extend)

webui/
└── components/
    └── iresponse/
        └── iresponse.html                     # Alpine component, inline style+script

tests/
├── unit/
│   ├── test_prompt_builder.py
│   └── test_iresponse_schema.py
└── integration/
    └── test_iresponse_submit.py
```
Prompts (default fallback):
```text
prompts/
└── iresponse/
    └── default.md.jinja        # Default prompt fallback with {{ variables }} placeholder
```

**Structure Decision**: Web application structure. Backend under `python/api/` (new endpoints for IR submit), `python/tools/` (PromptBuilder integration if needed), `python/helpers/` for validation/rendering helpers. Frontend under `webui/components/interactive_response/` (new component), integrated via existing SPA. Tests under `tests/` (unit for PromptBuilder and schema validation; integration for API and UI flows).

Frontend Styling Note: Use component-scoped CSS classes inside the component's `<style>` block to style active vs frozen states and collapsed containers; avoid inline style attributes to ease future restyling while keeping styles self-contained (no global CSS files).

Frontend Decisions:
- Container layout: Use CSS flex row with wrap and gap for `layout="horizontal"`; fallback to vertical below ~480px to avoid jitter.
- Collapse toggle: Minimal button control with `aria-expanded` and `aria-controls`; visually light header to preserve chat bubble aesthetics.
- Jinja filters: Register a global `tojson` filter in PromptBuilder for args template rendering.
- Prefill UX: Append rendered text to existing input, focus input, caret at end (no selection).

Backend Decisions:
- Default prompt fallback: If `callback` omitted, render `prompts/iresponse/default.md.jinja` with `variables` = fenced JSON of IR values and a concise explanatory preface.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
