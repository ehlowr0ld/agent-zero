# A0 Project Notebooks Directory

This directory contains critical documentation and development notes for the Agent Zero (A0) project.

## Directory Purpose

The `.cursor/notebooks` directory serves as a centralized location for:

1. **Project Documentation**: Technical guides and implementation details
2. **Development Notes**: Records of architectural decisions and patterns
3. **Bug Tracking**: Details about encountered bugs and their resolutions
4. **AI Assistant Scratchpads**: Persistent memory for AI development assistance

## Core Architecture Overview (Added/Updated)
- **Backend:** Python Flask server (`run_ui.py`). API handlers in `python/api/`. Core agent logic in `agent.py`. State persisted mainly via JSON files (`tmp/`, `memory/`).
- **Frontend:** Single Page Application (`webui/index.html`) using Alpine.js for reactivity. `webui/index.js` handles core logic and polling (`/poll`) for state updates.
- **State Sync:** Frontend relies heavily on polling the `/poll` endpoint to reflect backend state changes. UI state (tabs, etc.) also uses `localStorage`.

## Critical Files

### AI Assistant Scratchpad (MANDATORY)

- **Filename**: `ai_assistant_scratchpad.md`
- **Purpose**: Persistent memory to prevent context loss between AI assistant sessions. Contains general observations, architecture notes, current task context, and findings.
- **Requirement**: MUST be maintained by AI assistants during ALL development sessions
- **Structure**: See template below

```markdown
# AI Assistant Scratchpad

## ⚠️ CRITICAL WARNINGS ⚠️
- Important warnings about the environment and critical considerations (e.g., Docker context, state sync issues, complex reactivity).

## Active Context
- Current development focus and environment details.

## Recent Activity
- Chronological log of recent changes, explorations, and decisions made by the AI assistant.

## Pending Considerations
- Issues requiring future attention or follow-up.

## Component Structure Notes
- High-level details about backend and frontend component organization.

## Container Awareness
- Notes specific to the containerized environment and file paths.
```

**CRITICAL**: Failure to maintain the AI assistant scratchpad is considered a serious error that may result in application-breaking changes. AI assistants MUST prioritize scratchpad maintenance throughout development.

### Additional Documentation Files

- **Task Scheduler Implementation History**: `task-scheduler-implementation-history.md`
    - Contains detailed timeline of task scheduler development
    - Documents implementation phases, challenges, and solutions
    - Currently covers four implementation phases:
        - Phase 1: Initial example phase
        - Phase 2: Chat Context Auto-Detection Enhancement
        - Phase 3: Settings Modal Integration and Task Management Interface
        - Phase 4: Task Scheduler UI Implementation and API Integration
    - Last updated: 2023-06-01 (Note: May need further updates based on current code)
- **Task Scheduler Current Status**: `task-scheduler-current-status.md` (Updated based on exploration)
    - Summary of implemented features vs. future work for the Task Scheduler.
    - Verified API endpoints and UI components. Confirmed unified context storage.
- **Task Scheduler Feature Design**: `task-scheduler-feature-design.md`
    - Design document for the scheduler. Naming conventions (`scheduler-`) are critical.
- **Task Scheduler Validation Rules**: `task-scheduler-validation-rules.md`
    - Validation specifics for task properties.
- **Application Developer Documentation**: `application_developer_documentation_full_aigen.md`
    - Comprehensive guide for application developers (Note: Verify against current codebase).
- **Alpine.js Best Practices/Pitfalls**: `alpine-js-*.md` files (Reviewed)
    - Insights on declarative patterns, state management (`Alpine.store`), reactivity issues (esp. tabs), property binding.
- **UI Debugging/Context/Streaming Notes**: `alpine_js_ui_debugging.md`, `ui-context-switching.md`, `ui-streaming-event-handling.md`, `ui-tabs-and-context-management.md` (Reviewed)
    - Notes on debugging UI, handling context switching, managing streaming updates, and tab implementation details.
- **Settings Modal Documentation**: `settings-modal-tabbed-interface.md` (Reviewed)
    - Details on the settings modal structure, tab implementation, styling, and known reactivity challenges (scheduler tab).

## Usage Guidelines

1. **For AI Assistants**:
    - ALWAYS review the scratchpad (`ai_assistant_scratchpad.md`) and related context files (`.context.md`, `.warning-flags`) before beginning work.
    - Update the scratchpad with all relevant information DURING development.
    - Update `.context.md` with factual information about endpoints, data structures, etc.
    - Update `.warning-flags` with concise flags for critical issues or gotchas discovered.
    - Ensure scratchpad files are up-to-date BEFORE ending a session.
    - Cross-reference with project documentation in this directory.

2. **For Human Developers**:
    - Use notebooks for persistent documentation needs.
    - Reference AI assistant scratchpad to understand recent changes.
    - Create new notebooks for significant new components or features.
    - Ensure AI assistants maintain proper note-taking discipline.

## File Naming Conventions

- **Component Documentation**: `component-name-implementation.md`
- **Bug Reports**: `bug-issue-name.md`
- **Design Decisions**: `design-decision-topic.md`
- **Reserved Files**: Files like `ai_assistant_scratchpad.md` are reserved for specific purposes.

## Maintenance Requirements

The notebooks directory requires regular maintenance:

1. **Review**: Review active notebooks periodically.
2. **Conflict Resolution**: Resolve any conflicting information between notebooks.
3. **Outdated Information**: Mark or update outdated information based on code changes.
4. **Cross-Reference**: Ensure consistency with project-level documentation and scratchpad files.

## Integration with Project Documentation

These notebooks are part of a comprehensive documentation strategy that includes:

1. **`.context.md`** in project root: High-level project context (Endpoints, Data Structures, File Paths).
    - **STATUS**: MANDATORY
    - **PURPOSE**: Project-wide context tracking visible to all developers.
    - **UPDATES**: After any significant change to the project affecting these areas.
    - **LOCATION**: `/home/rafael/Workspace/Repos/rafael/a0-local/.context.md`

2. **`.warning-flags`** in project root: Critical reminders in flag format.
    - **STATUS**: MANDATORY
    - **PURPOSE**: Quick-reference boolean flags/notes for critical facts or potential issues.
    - **UPDATES**: When critical facts change or new potential issues are identified.
    - **LOCATION**: `/home/rafael/Workspace/Repos/rafael/a0-local/.warning-flags`

3. **`ai_assistant_scratchpad.md`** in notebooks: AI assistant's detailed working notes.
    - **STATUS**: MANDATORY (for AI)
    - **PURPOSE**: AI assistant's persistent memory, observations, and working notes.
    - **UPDATES**: During every development session by the AI.
    - **LOCATION**: `/home/rafael/Workspace/Repos/rafael/a0-local/.cursor/notebooks/ai_assistant_scratchpad.md`

**CRITICAL**: All three files (`.context.md`, `.warning-flags`, `ai_assistant_scratchpad.md`) are REQUIRED components of the context retention system and must be maintained. They serve different but complementary purposes:

- **Scratchpad**: Detailed development notes, reasoning, and observations by AI assistants.
- **Context file**: Factual, project-wide context (APIs, structures, paths) accessible to all developers.
- **Warning flags**: Concise flags/notes for quick verification of critical facts or potential pitfalls.

Together, these files ensure continuity and consistency across development sessions, especially critical in the containerized environment where the application runs.
