# AI Assistant Scratchpad

## ⚠️ CRITICAL WARNINGS ⚠️

- **CONTAINER ENVIRONMENT**: Application runs in a container! Changes outside mounted volumes WILL BE LOST!
- **CSS NAMING**: ALWAYS use component-specific prefixes (e.g., `scheduler-` for task scheduler CSS classes)
- **UI PATTERN**: NEVER modify the standard section structure used across the application
- **BUTTON STYLING**: NEVER change global button styles without explicit approval
- **MEMORY FAILURES**: ALWAYS assume context will be lost between sessions - keep notes updated!
- **SPEECH MODULE**: Always include safety checks when using speech functionality
- **DOCUMENTATION SYSTEM**: This scratchpad works WITH .context.md and .warning-flags files - all three are MANDATORY
- **NAMING CONVENTION**: All scheduler-related code MUST use the `scheduler-` prefix
- **API MODIFICATION**: DO NOT modify existing API patterns or create alternate implementations for existing features
- **CONSERVATIVE CHANGES**: Be extremely conservative when working with existing functionality - do not change established conventions
- **CSS CLASS REUSE**: NEVER reuse existing CSS classes if it would mean changing them - always create new, distinctly named classes
- **PRESERVE STYLING**: When fixing functional issues, NEVER modify styling elements unless specifically requested
- **TRANSPARENT COMMUNICATION**: ALWAYS communicate when fixes might cause temporary regressions or instability
- Application runs in Docker; direct file system access reflects the *container's* file system.
- Saving settings (`/settings_set`) re-initializes agent configurations and can trigger model preloading (`settings.py -> _apply_settings`).
- UI state relies heavily on the `/poll` endpoint; discrepancies between frontend perception and backend reality can occur between polls.
- Complex Alpine.js reactivity issues, especially with nested components or tab switching, may require workarounds (e.g., `setTimeout`, two-step updates). See `settings.js` and `scheduler.js`.
- File-based state persistence (`tmp/chats/`, `tmp/chat_names.json`, `memory/scheduler/tasks.json`) might be susceptible to race conditions if not properly locked (some locking exists in `task_scheduler.py`).

## ⚠️ TRANSPARENT COMMUNICATION PROTOCOL ⚠️

When implementing complex fixes, especially those involving initialization, timing, or recursive issues, CLEARLY communicate potential temporary regressions to the user.

### When to Provide Warnings

1. **Multi-Step Fixes**
   - When a solution requires multiple changes that won't work until all are in place
   - When intermediate states may break functionality temporarily
   - When refactoring critical components that may cause temporary instability

2. **High-Risk Changes**
   - When modifying core initialization code
   - When fixing recursive loops or timing-dependent code
   - When changing event handlers that might affect multiple components
   - When altering the sequence of operations in critical sections

3. **Uncertain Outcomes**
   - When implementing solutions with unpredictable edge cases
   - When the fix might work in testing but could behave differently in production
   - When fixing one issue might expose or trigger other underlying problems

### How to Communicate

1. **Before Implementing**
   - "This fix involves changes to [critical component] which might temporarily cause [specific issue] while we implement the complete solution"
   - "We'll need to implement this in multiple steps. During this process, [feature] might not work correctly until all steps are complete"
   - "This is a complex issue that might require multiple iterations to fully resolve"

2. **During Implementation**
   - Provide clear status updates on what's working/not working
   - Explain which issues are expected vs. unexpected
   - Communicate timeline for completing remaining steps

3. **After Implementation**
   - Confirm which issues have been resolved
   - Note any remaining issues or limitations
   - Explain any necessary follow-up changes

### Examples of Good Communication

**BEFORE CHANGE:**
"I'm going to fix the infinite recursion in the settings modal. This involves changes to both the openModal method and its dependencies. There's a risk that the settings modal might not open at all during intermediate steps of this fix. We'll need to update both index.js and settings.js to fully resolve the issue."

**DURING CHANGE:**
"I've fixed the recursion in index.js, but we still need to update settings.js. Currently, clicking the settings button might fail with an error until we complete the next step."

**AFTER CHANGE:**
"The infinite recursion issue is now fixed. Both files have been updated and the settings modal should open properly. The fix includes error handling that should prevent the UI from freezing even if there are initialization issues."

## ⚠️ STYLING PRESERVATION PROTOCOL ⚠️

### Core Principle: Separate Functional Changes from Styling

When fixing functional issues in the code, it's CRITICAL to maintain strict separation between functional changes and styling elements. Follow these guidelines to prevent unintended styling changes:

1. **Targeted Edits Only**
   - When fixing a function or behavior, modify ONLY the lines directly related to functionality
   - DO NOT "clean up" or "improve" styling elements while fixing functional code
   - Resist the temptation to refactor or reorganize styling elements

2. **Preserve Visual Design Elements**
   - Visual design choices are INTENTIONAL - respect them even if they seem unusual
   - Keep all SVG paths, dimensions, viewBox settings, and fill properties exactly as they are
   - Maintain original styling classes, properties, and values in HTML elements

3. **Element Structure Preservation**
   - Keep the original HTML structure intact when making functional changes
   - Preserve element classes, IDs, and attributes unrelated to the fix
   - DO NOT add, remove, or reorder elements unless necessary for the functional fix

4. **Strict Separation of Concerns**
   - When editing code, mentally separate it into "functional" and "styling" components
   - Only modify the specific parts needed to fix the issue at hand
   - If a styling change is needed for a functional fix, explicitly document WHY it's necessary

5. **Anti-Patterns to Avoid**
   - DO NOT replace SVG paths with "simpler" or "cleaner" versions
   - DO NOT change button text, icons, or layouts while fixing functionality
   - DO NOT modify color schemes, spacing, or visual elements
   - DO NOT alter class names or CSS properties unless explicitly required to fix the issue

### How to Make Functional Changes Without Affecting Styling

1. **Analyze Thoroughly Before Editing**
   - Identify exactly which lines of code are responsible for the issue
   - Determine the minimal change needed to fix the problem
   - Map out dependencies to ensure changes won't affect styling

2. **Use Precise Edit Targets**
   - Edit only the specific attributes or properties causing the problem
   - If modifying a multi-line element, preserve all styling attributes
   - Be extremely careful with elements containing both functional and styling properties

3. **Test Changes Visually**
   - After making a functional change, verify the visual appearance hasn't changed
   - Check that all styling elements remain exactly as they were
   - Confirm no unintended visual side effects occurred

### Examples of Acceptable vs. Unacceptable Changes

**UNACCEPTABLE**:
```html
<!-- Before -->
<button class="config-button" id="settings" @click="window.openSettings()">
  <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="-5.0 -17.0 110.0 135.0" fill="currentColor" width="24" height="24">
    <!-- Complex SVG path data -->
  </svg>
  Settings
</button>

<!-- After - Changed SVG and styling while fixing click handler -->
<button class="config-button" id="settings" @click="handleSettingsClick()">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
    <!-- Different, "cleaner" SVG path -->
  </svg>
  <span>Settings</span>
</button>
```

**ACCEPTABLE**:
```html
<!-- Before -->
<button class="config-button" id="settings" @click="window.openSettings()">
  <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="-5.0 -17.0 110.0 135.0" fill="currentColor" width="24" height="24">
    <!-- Complex SVG path data -->
  </svg>
  Settings
</button>

<!-- After - Only fixed the click handler, preserved styling -->
<button class="config-button" id="settings" @click="handleSettingsClick()">
  <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="-5.0 -17.0 110.0 135.0" fill="currentColor" width="24" height="24">
    <!-- Same exact SVG path data -->
  </svg>
  Settings
</button>
```

### When Styling Changes ARE Required

If a styling change is absolutely necessary to fix a functional issue:

1. Explicitly document WHY the styling change is needed
2. Make the minimal possible styling change to fix the issue
3. Preserve as much of the original styling as possible
4. Ensure the styling change doesn't affect other components

## UI COMPONENT STYLING SYSTEM (CRITICAL)

### CSS Naming and Reuse Guidelines

1. **NEVER modify existing CSS classes** - this can cause unexpected side effects across the application
2. **ALWAYS create new, distinctly named classes** with appropriate prefixes for new components
3. **Follow the established prefix convention** (e.g., `scheduler-` for task scheduler components)
4. **Keep CSS scoped to components** to prevent conflicts
5. **When styling similar elements**, study the existing patterns but create new classes rather than reusing
6. **Document all new CSS classes** in this scratchpad

### Button Styling System

There is a carefully defined button styling system that must be preserved:

1. **Button CSS Variables** (defined in `settings.css`):
   ```css
   :root {
     --button-text-color: white;
     --button-border-color: white;
     --button-glow-color: rgba(255, 255, 255, 0.3);
     --button-text-shadow-color: rgba(255, 255, 255, 0.5);
     --button-padding: 8px 15px;
     --button-gap: 8px;
     --button-border-radius: 4px;
     --button-border-width: 1px;
     --button-transition: background-color 0.2s;
     --button-shadow: 0 0 5px rgba(255, 255, 255, 0.3);
     --button-text-shadow: 0 0 5px rgba(255, 255, 255, 0.5);
   }
   ```

2. **Shared Button Components**:
   - `.btn-save` - For "Save Changes" buttons in modal dialogs
   - `.scheduler-btn` - For "New Task" buttons in scheduler

3. **Consistent Button Properties**:
   - Both button types use the SAME CSS variables
   - Both have identical styling with display: flex, white borders with glow
   - Background color uses `var(--color-primary)`
   - Hover color uses `var(--color-primary-hover)`

4. **Special Button Styling Concerns**:
   - NEVER USE !important unless absolutely necessary
   - ALWAYS use the CSS variables for consistency
   - Button styles are designed to follow the theme system
   - DO NOT create unique one-off button styles

### Tab Styling System

1. **Left Panel Tabs**:
   - Uses `.tabs-container`, `.tabs`, and `.tab` classes
   - Active tab indicator is a grey underline (`#808080`)
   - DO NOT change this to match primary color!

2. **Settings Modal Tabs**:
   - Uses `.settings-tabs-container`, `.settings-tabs`, and `.settings-tab` classes
   - Active tab styling is distinct with box-shadow effect

3. **Tab Styling Interactions**:
   - Hover behaviors have subtle opacity changes (DO NOT add color changes)
   - Active indicators use specific colors that should not be changed

### Color Variables System

1. **Primary Colors**:
   - `--color-primary`: Set to `#171717` (dark grey/black) to match modal background
   - `--color-primary-hover`: Set to `#5141c9` (violet/purple) for hover states

2. **Other Theme Colors**:
   - `--color-text`: Text color throughout the app
   - `--color-border`: Border color for elements (NOT for buttons)
   - `--color-panel`: Background color for panels and modals

3. **Component-Specific Colors**:
   - Each component can have its own color variables (e.g., button colors)
   - These MUST be consistent with the overall theme

## Active Context

- Application runs in CONTAINERIZED ENVIRONMENT with Docker
- Working on: Task Scheduler UI implementation with proper API integration
- Critical files:
  - `/home/rafael/Workspace/Repos/rafael/a0-local/webui/index.html`
  - `/home/rafael/Workspace/Repos/rafael/a0-local/webui/css/task_scheduler_settings.css`
  - `/home/rafael/Workspace/Repos/rafael/a0-local/webui/js/task_scheduler_settings.js`
  - `/home/rafael/Workspace/Repos/rafael/a0-local/run_ui.py`
  - `/home/rafael/Workspace/Repos/rafael/a0-local/python/helpers/api.py`
  - `/home/rafael/Workspace/Repos/rafael/a0-local/python/helpers/task_scheduler.py`
- Current task:
  - Completed implementation of task scheduler UI components
  - Added CSS styling with "task-scheduler-" prefix
  - Implemented JavaScript functionality with Alpine.js
  - Integrated with backend API endpoints
  - Updated documentation to reflect implementation details

## Recent Activity

- [2023-06-01] Implemented task_scheduler_settings.js with full Alpine.js component
- [2023-06-01] Created comprehensive CSS styling for task scheduler UI
- [2023-06-01] Updated HTML structure for task scheduler settings section
- [2023-06-01] Added proper API integration for task operations
- [2023-06-01] Fixed local storage key from selectedSchedulerTaskId to lastSelectedSchedulerTask
- [2023-06-01] Added context flags (ctx_planning, ctx_reasoning, ctx_deep_search) to task form
- [2023-06-01] Implemented task status visualization with color-coded indicators
- [2023-06-01] Added responsive design for task scheduler UI
- [2023-06-01] Created loading and empty states for better user experience
- [2023-06-01] Updated documentation with implementation details
- [2023-03-23] Updated button styling to use less bright white (changed from pure white to #e6e6e6)
- [2023-03-23] Fixed issues with action buttons in scheduler table - removed box-shadow to eliminate visual artifact
- [2023-03-23] Fixed scheduler action button positioning by using proper cell alignment and static positioning
- [2023-03-23] Added consistent table cell styling for all action buttons
- [2023-03-23] Created .btn-bordered class for standardized button styling across the app
- [2023-03-23] Updated `--color-primary` to match modal background color (#171717)
- [2023-03-23] Set tab underlining for left panel to grey (#808080)
- [2023-03-23] Created consistent button styling system with shared variables
- [2023-03-23] Fixed section title colors to be visible grey (#999999)
- [2023-03-23] Removed unnecessary !important declarations for maintainability
- [2023-03-23] Ensured buttons use same styling with shared CSS variables

## Related Context Files

### Mandatory Context Retention System

This scratchpad is part of a three-file mandatory context retention system:

1. **THIS SCRATCHPAD** (`.cursor/notebooks/ai_assistant_scratchpad.md`):
   - Contains detailed AI assistant working notes and observations
   - Maintains chronological record of changes and decisions
   - Tracks component-specific implementation details
   - MUST be updated during EVERY development session

2. **PROJECT CONTEXT** (`.context.md` in project root):
   - Contains high-level project context visible to all developers
   - Focuses on environment settings and architecture notes
   - Tracks major changes at a project level
   - Should be reviewed at the start of each session
   - Last updated: 2023-06-01

3. **WARNING FLAGS** (`.warning-flags` in project root):
   - Contains boolean flags for critical facts that must be remembered
   - Provides quick reference for essential guidelines
   - Should be checked before making any significant changes
   - Current critical flags include:
     - `CONTAINERIZED_ENVIRONMENT=TRUE`
     - `CSS_PREFIX_REQUIRED=TRUE`
     - `STANDARD_SECTION_PATTERN_REQUIRED=TRUE`
     - `BUTTON_STYLING_MUST_BE_PRESERVED=TRUE`

**VITAL PROTOCOL**: Before making ANY changes to the codebase:
1. Review this scratchpad for detailed context
2. Check `.context.md` for project-wide information
3. Verify critical facts in `.warning-flags`
4. Update all three files when appropriate

## Component Structure Notes

### Left Panel Layout
- Contains chats-list-container and tasks-list-container
- Tab system switches between chats and tasks views
- Structure follows standard pattern with tabs-container and config-section
- Tab underlining MUST be grey (#808080)

### Task Scheduler Component
- Uses standard section pattern with `.section` class
- All CSS classes use task-scheduler- prefix
- Alpine.js component manages state via x-data="taskSchedulerSettings"
- Standard button styling must be preserved
- DOM structure follows established pattern for other tabs

### Modal Dialog System
- Settings modal uses a standard pattern with section containers
- Each tab follows the same structure pattern
- Buttons have specific styling that must be preserved
- Save Changes button must match New Task button styling

### Speech Detection
- Safety checks required when accessing window.speech
- Verified window.speech exists before calling methods
- Added similar checks to speech stop button click handler

## Styling Do's and Don'ts

### DO:
- Use CSS variables for theme consistency
- Follow component-specific prefixing
- Preserve existing style patterns
- Test changes visually before committing
- Document ALL styling changes in this scratchpad
- Match exact colors for tab underlining (#808080 for grey)
- Use same button styling for Save and New Task buttons

### DON'T:
- Use !important declarations
- Hardcode colors without variables
- Create one-off styles for similar components
- Change tab underlining colors
- Mix primary-color and primary-hover colors incorrectly
- Apply unrelated styling to multiple components
- Create duplicate CSS definitions

## Container Awareness

- Files in `/app/data` and `/app/config` persist after restart
- UI changes to HTML, CSS, and JS files require persistence verification
- Container restart will reset all non-persistent files
- Always check whether changes are made to files in persistent volumes
- Development environment is inside a Docker container
- Context loss between sessions is assumed - this scratchpad is critical!

## Performance and Debugging Notes

- Application uses Alpine.js for reactive UI components
- CSS uses BEM-like approach with component prefixes
- Button styling issues may affect multiple components
- Always check for side effects when modifying shared styles
- Performance implications of DOM structure changes should be documented
- Speech module errors appear when the module isn't properly initialized
- Tab selection uses localStorage for persistence

## Task Scheduler Implementation Details

### ⚠️ CURRENT TASK SCHEDULER IMPLEMENTATION STATE ⚠️

1. **Completed Components**:
   - **JavaScript (scheduler.js)**:
     - Full Alpine.js component implementation
     - Task loading, filtering, and sorting
     - CRUD operations (Create, Read, Update, Delete)
     - API integration for task operations
     - Form validation and error handling
     - Context flags support
     - Local storage for selected task
     - UI Tab and Modal Integration
     - Fixed tab selection initialization

   - **CSS Styling**:
     - Complete styling with scheduler- prefix
     - Responsive table layout
     - Status indicators
     - Form styling
     - Loading/empty states
     - Responsive design
     - Animations

   - **HTML Integration**:
     - Dedicated section in settings modal
     - Task list view with filters
     - Task form
     - Loading and empty states
     - Consistent UI integration
     - Fixed tab selection behavior in settings modal

2. **Current State**:
   - All UI components are fully implemented
   - Backend API integration is complete
   - Context flags are supported (ctx_planning, ctx_reasoning, ctx_deep_search)
   - Local storage key is updated (settingsActiveTab)
   - Task status visualization is implemented
   - Documentation is updated
   - Fixed: Tab selection issue in settings modal
   - Fixed: Content jump when clicking scheduler tab
   - Fixed: Initialization order for Alpine.js components
   - Fixed: Event handling for scheduler tab clicks
   - Fixed: Corrected runTask function to use scheduler_task_run endpoint instead of scheduler_tick
   - Implemented: New scheduler_task_run API for manual task execution

3. **API Endpoints Implementation**:
   - ✅ `scheduler_tick.py` - Handles periodic checks for due tasks (cron-triggered)
   - ✅ `scheduler_task_run.py` - Manually runs a specific task by UUID (user-triggered)
   - ✅ `scheduler_tasks_list.py` - Lists all tasks with their types
   - ✅ `scheduler_task_create.py` - Creates new tasks
   - ✅ `scheduler_task_delete.py` - Deletes tasks
   - ✅ `scheduler_task_update.py` - Updates existing tasks

4. **Recent Critical Fixes**:
   - Fixed settings modal tab initialization for the scheduler tab
   - Implemented proper event handling for scheduler tab selection
   - Added workaround for Alpine.js reactivity issues during tab switching
   - Fixed initialization timing issues when modal opens with scheduler tab pre-selected
   - Resolved content jump (2px) when clicking the scheduler tab
   - Added explicit debugging logs for easier troubleshooting

5. **Technical Implementation Approach**:
   - Enhanced click handler that properly manages Alpine.js reactivity
   - Two-step tab activation process to ensure proper DOM updates
   - Global click interceptor to ensure tab clicks are properly processed
   - Tab state preservation using localStorage
   - Improved initialization sequence to ensure components are ready before use
   - Active monitoring of Alpine.js data model state transitions
   - Added proper cross-component communication

6. **UI Interaction Model**:
   - Task list in settings shows detailed view
   - Filtering by type and status
   - Sorting by name, type, status, and creation date
   - Action buttons for run, edit, delete
   - Form for creating and editing tasks
   - Selection preserved between sessions

7. **API Integration**:
   - Task creation: POST /scheduler_task_create
   - Task update: POST /scheduler_task_update
   - Task deletion: POST /scheduler_task_delete
   - Task running: POST /scheduler_task_run
   - Task listing: POST /scheduler_tasks_list

8. **Future Improvements**:
   - Task execution history and logs view
   - Advanced scheduling options with visual builder
   - Task status monitoring with real-time updates
   - Enhanced error reporting
   - Task templates for common use cases

### ⚠️ CRITICAL TASK SCHEDULER IMPLEMENTATION NOTES ⚠️

1. **Naming/Namespace Conventions**:
   - ALWAYS use "task-scheduler-" prefix for CSS classes
   - Avoid using "task" alone - always use "task-scheduler-task"
   - Maintain clear distinction from agent tasks/notes

2. **Task Types and Properties**:
   - ScheduledTask: Has schedule (cron format)
   - AdHocTask: Has api_token instead of schedule
   - Both need start_time/not_before property (to be added)
   - Both share status: idle, running, disabled, error
   - Status display as badges (blue/green/grey/red)

3. **UI Interaction Model**:
   - Left pane task name click -> Opens chat context in main view
   - Identical behavior to chat list name clicks
   - Settings modal only for task configuration
   - Task list in settings shows detailed view

4. **Schedule Display**:
   - Store as cron syntax internally
   - Display human-readable when possible (e.g., "Every hour")
   - Fallback to cron display for complex schedules

5. **Critical Technical Requirements**:
   - Datetime serialization/deserialization needed for BaseModel
   - Use isoformat for datetime fields
   - Status "error" must be added if not present
   - Status badges with specific colors:
     - idle: blue
     - running: green
     - disabled: grey
     - error: red

6. **API Integration**:
   - AdHoc task API endpoints out of scope
   - Focus on task management UI
   - Maintain API function-style convention

### Implementation Priorities Updated

1. **Phase 1 - Backend Enhancement**:
   - Add error status if missing
   - Add start_time/not_before field
   - Implement datetime serialization
   - Add schedule display helpers

2. **Phase 2 - Left Panel Integration**:
   - Verify existing task list implementation
   - Enhance with proper naming
   - Add status badges
   - Implement chat context opening

3. **Phase 3 - Settings Modal**:
   - Task list with filters
   - Schedule input/display
   - Status management
   - Detail view

4. **Phase 4 - Polish & Integration**:
   - Error handling
   - Loading states
   - Schedule presets
   - Validation

### Technical Implementation Notes

1. **Datetime Handling**:
   ```python
   # Example datetime serialization for BaseModel
   class TaskBase(BaseModel):
       created_at: datetime

       class Config:
           json_encoders = {
               datetime: lambda v: v.isoformat()
           }

       @validator("created_at", pre=True)
       def parse_datetime(cls, v):
           if isinstance(v, str):
               return datetime.fromisoformat(v)
           return v
   ```

2. **Status Badge CSS**:
   ```css
   .scheduler-status-badge {
     padding: 2px 8px;
     border-radius: 12px;
     font-size: 0.85em;
   }

   .scheduler-status-idle { background: var(--color-blue); }
   .scheduler-status-running { background: var(--color-green); }
   .scheduler-status-disabled { background: var(--color-grey); }
   .scheduler-status-error { background: var(--color-error); }
   ```

3. **Schedule Display Helper**:
   ```python
   def get_human_readable_schedule(schedule: TaskSchedule) -> str:
       # Convert cron to human readable if possible
       # Return cron string if complex schedule
       pass
   ```

### Critical Reminders

- ALWAYS maintain proper namespace prefixing
- NEVER mix task scheduler with agent tasks
- Datetime serialization MUST be handled
- Status badges MUST follow color scheme
- Chat context opening MUST match chat list behavior
- Schedule display MUST be human-readable when possible

### Core Components

1. **Backend Task Management** (`

## Task Scheduler API Implementation

### API Endpoints

1. **Task Listing** (`scheduler_tasks_list`):
   - Supports filtering by status and type
   - Supports sorting by name, status, type, created_at
   - Returns human-readable schedule display
   - Returns task type (scheduled/adhoc)

2. **Task Retrieval** (`scheduler_task_get`):
   - Gets single task by UUID
   - Returns full task details
   - Includes human-readable schedule
   - Includes task type

3. **Task Creation** (`scheduler_task_create`):
   - Creates scheduled or adhoc tasks
   - Validates required fields
   - Handles schedule creation
   - Supports start_time in ISO format

4. **Task Update** (`scheduler_task_update`):
   - Updates any task field
   - Handles schedule updates
   - Preserves task type
   - Updates timestamps

5. **Task Deletion** (`scheduler_task_delete`):
   - Removes task by UUID
   - Validates task existence
   - Returns success status

### API Response Format

1. **Success Responses**:
   ```json
   {
     "task": {
       "uuid": "...",
       "name": "...",
       "state": "idle|running|disabled|error",
       "type": "scheduled|adhoc",
       "schedule_display": "Every hour" // for scheduled tasks
     }
   }
   ```

2. **Error Responses**:
   ```json
   {
     "error": "Error message"
   }
   ```
   - Status codes: 400, 404, 500

### UI Implementation Plan

1. **Left Panel Task List**:
   - Matches chat list behavior
   - Shows task name and status badge
   - Click opens chat context in main view
   - Uses scheduler-specific CSS classes
   - Status badges with colors:
     - idle: blue
     - running: green
     - disabled: grey
     - error: red

2. **Settings Modal Task List**:
   - Full task details table
   - Filter/sort controls
   - Action buttons
   - Schedule display
   - Status management

3. **Task Forms**:
   - Create new task form
   - Edit existing task form
   - Schedule input with presets
   - Path input for attachments
   - Validation feedback

### Component Structure

1. **Left Panel**:
   ```html
   <div class="tasks-list-container">
     <div class="scheduler-task-list">
       <div class="scheduler-task-item" x-for="task in tasks">
         <span class="scheduler-task-name" @click="openTaskChat(task.uuid)">
           {{ task.name }}
         </span>
         <span class="scheduler-status-badge" :class="getStatusClass(task.state)">
           {{ task.state }}
         </span>
       </div>
     </div>
   </div>
   ```

2. **Settings Modal**:
   ```html
   <div x-show="activeTab === 'task_scheduler'" class="settings-section">
     <div class="scheduler-controls">
       <div class="scheduler-filters">
         <!-- Filter/sort controls -->
       </div>
       <button class="scheduler-btn-new">New Task</button>
     </div>
     <div class="scheduler-task-table">
       <!-- Task list with details -->
     </div>
     <div x-show="showTaskForm" class="scheduler-task-form">
       <!-- Task form -->
     </div>
   </div>
   ```

### CSS Structure

1. **Status Badges**:
   ```css
   .scheduler-status-badge {
     padding: 2px 8px;
     border-radius: 12px;
     font-size: 0.85em;
   }
   .scheduler-status-idle { background: var(--color-blue); }
   .scheduler-status-running { background: var(--color-green); }
   .scheduler-status-disabled { background: var(--color-grey); }
   .scheduler-status-error { background: var(--color-error); }
   ```

2. **Task List**:
   ```css
   .scheduler-task-list {
     display: flex;
     flex-direction: column;
     gap: 0.5rem;
   }
   .scheduler-task-item {
     display: flex;
     justify-content: space-between;
     align-items: center;
     padding: 0.5rem;
   }
   ```

### Implementation Order

1. **Phase 1 - Left Panel Integration**:
   - Add task list to left panel
   - Implement status badges
   - Add chat context opening
   - Match chat list styling

2. **Phase 2 - Settings List View**:
   - Create task list table
   - Add filter/sort controls
   - Implement status badges
   - Add action buttons

3. **Phase 3 - Task Forms**:
   - Create new task form
   - Add schedule input
   - Add validation
   - Implement editing

4. **Phase 4 - Polish**:
   - Add loading states
   - Improve error handling
   - Add success feedback
   - Test edge cases

### Critical Reminders

- ALWAYS use scheduler- prefix for CSS classes
- NEVER mix with agent task/note functionality
- Status badges MUST follow color scheme
- Chat context opening MUST match chat list
- Schedule display MUST be human-readable when possible
- Forms MUST validate all inputs
- ALWAYS handle loading/error states
- Container paths MUST be absolute

### Testing Notes

- Application requires basic auth
- Container environment required
- API endpoints need auth headers
- Test all status transitions
- Verify schedule parsing
- Check datetime handling
- Validate file paths

## Task Scheduler Implementation - Latest Updates

### Name Uniqueness Implementation
- Added task name uniqueness validation in frontend
- Validation happens before API calls to prevent unnecessary requests
- Shows clear error messages in UI
- Handles both create and update scenarios
- Excludes current task when validating during edit

### Validation System
1. **Frontend Validation**:
   ```javascript
   validateTask(task) {
       // Clear previous validation error
       this.validationError = '';

       // Check required fields
       if (!task.name?.trim()) {
           this.validationError = 'Task name is required';
           return false;
       }

       // Check name uniqueness
       const isUnique = this.isTaskNameUnique(task.name, task.uuid);
       if (!isUnique) {
           this.validationError = 'Task name must be unique';
           return false;
       }

       // Type-specific validation
       if (task.type === 'scheduled') {
           if (!task.schedule) {
               this.validationError = 'Schedule is required for scheduled tasks';
               return false;
           }
       } else if (task.type === 'adhoc') {
           if (!task.token?.trim()) {
               this.validationError = 'Token is required for ad-hoc tasks';
               return false;
           }
       }

       return true;
   }
   ```

2. **UI Error Display**:
   - Added error state styling for form fields
   - Shows validation messages below fields
   - Clears errors when input changes
   - Uses toast notifications for validation errors

### Critical Implementation Notes
1. **Task Types**:
   - Scheduled tasks require valid cron schedule
   - Ad-hoc tasks require unique token
   - Both types share common fields (name, prompts, attachments)

2. **State Management**:
   - Tasks can be: idle, running, disabled, error
   - State transitions handled through API
   - UI updates automatically through polling

3. **Views Integration**:
   - Left panel shows simplified task list
   - Settings modal shows full management interface
   - Both views share same taskManager component
   - Real-time updates through 30-second polling

### Pending Considerations
1. **Additional Validations Needed**:
   - Cron expression validation
   - Token format validation
   - Attachment path validation
   - System/user prompt validation

2. **UI Enhancements**:
   - Add cron expression helper/builder
   - Improve schedule display format
   - Add task execution history view
   - Enhance error message clarity

### Backend Review Needed
- Need to review backend code for:
  - Task model implementation
  - API endpoint handlers
  - Schedule processing
  - Task execution logic

### Next Steps
1. Implement comprehensive validation rules
2. Review and enhance backend code
3. Add task execution history
4. Improve schedule input UX
5. Add task duplication feature

## Latest Implementation Updates

### Task Scheduler Validation System
- Implemented unified backend validation endpoint `/scheduler_validate_task`
- Created comprehensive frontend validation in `task_scheduler.js`
- Added real-time field validation with error display
- Implemented proper file path validation for container environment

### Validation Rules Implementation
1. **Task Name Validation**:
   - Length: 3-50 characters
   - Must start/end with alphanumeric
   - Unique across all tasks
   - Real-time validation with debounce

2. **Schedule Validation (Scheduled Tasks)**:
   - Valid cron expression required
   - All schedule fields must be present
   - Human-readable display when possible

3. **Token Validation (Ad-hoc Tasks)**:
   - Length: 8-32 characters
   - Must contain: uppercase, lowercase, number
   - Must start/end with alphanumeric
   - Unique across ad-hoc tasks

4. **Prompt Validation**:
   - System Prompt: Optional, max 2000 chars
   - User Prompt: Required, 10-2000 chars
   - Real-time length validation

5. **Attachment Validation**:
   - Maximum 10 files
   - Size limits: 10MB per file, 50MB total
   - Absolute paths required
   - Existence and permissions checked

6. **State Transition Validation**:
   - Explicit state machine implementation
   - Valid transitions:
     ```
     idle → [running, disabled]
     running → [idle, error]
     disabled → [idle]
     error → [idle, disabled]
     ```

### Critical Implementation Notes
1. **Container Awareness**:
   - All file paths MUST be absolute
   - File validation respects container boundaries
   - Permission checks within container context

2. **Error Handling**:
   - Field-specific error messages
   - Form-level validation summary
   - Network error handling
   - File system error handling

3. **UI Integration**:
   - Real-time validation feedback
   - Clear error message display
   - Loading state indicators
   - Validation summary when needed

### Pending Improvements
1. **UI Enhancements**:
   - File picker interface needed
   - Schedule builder UI would improve UX
   - Better validation error display

2. **Performance Optimization**:
   - Consider validation result caching
   - Batch file validation
   - Optimize API calls

3. **Enhanced Validation**:
   - File type restrictions
   - Template variable support
   - More sophisticated schedule validation

### Latest Technical Decisions
1. **Unified Validation Endpoint**:
   - Single source of truth for validation
   - Reduces API calls
   - Enables cross-field validation
   - Consistent validation rules

2. **Frontend Integration**:
   - Uses Alpine.js reactivity
   - Real-time field validation
   - Proper error state management
   - Loading state handling

3. **Error Display Strategy**:
   - Field-level error messages
   - Validation summary for multiple errors
   - Toast notifications for major issues
   - Clear error state indicators

## Recent Changes

### [2023-03-24] Task Scheduler Naming Convention Update
- Updated all task scheduler components to use consistent `scheduler-` prefix
- Renamed component from `taskManager` to `schedulerTaskManager`
- Updated all method names to include `Scheduler` prefix
- Updated all CSS classes to use `scheduler-` prefix
- Updated localStorage keys to use scheduler-specific names
- Updated documentation to reflect naming convention requirements

### Component Naming Updates
1. **JavaScript Components**:
   - `taskManager` → `schedulerTaskManager`
   - `loadTasks()` → `loadSchedulerTasks()`
   - `saveTask()` → `saveSchedulerTask()`
   - `toggleTaskState()` → `toggleSchedulerTaskState()`

2. **CSS Classes**:
   - `.task-list` → `.scheduler-task-list`
   - `.task-item` → `.scheduler-task-item`
   - `.status-badge` → `.scheduler-status-badge`
   - `.form-group` → `.scheduler-form-group`

3. **LocalStorage Keys**:
   - `lastSelectedTask` → `lastSelectedSchedulerTask`
   - `activeTab` → `scheduler-tasks`

4. **API Endpoints** (already correctly prefixed):
   - `/scheduler_tasks_list`
   - `/scheduler_task_create`
   - `/scheduler_task_update`
   - `/scheduler_task_delete`

## Implementation Status

### Completed
- ✅ Updated component naming to use scheduler- prefix
- ✅ Updated all method names for consistency
- ✅ Updated CSS classes with proper prefixing
- ✅ Updated localStorage keys
- ✅ Updated documentation
- ✅ Verified API endpoint naming

### Pending
- ⏳ Review any remaining generic task references
- ⏳ Update test files to use new naming
- ⏳ Add validation for naming convention in linting
- ⏳ Update any remaining documentation

## Critical Implementation Notes

### Naming Convention Rules
1. **Component Names**:
   - MUST start with `scheduler`
   - Use camelCase for JavaScript
   - Use kebab-case for CSS
   - Use underscore for API endpoints

2. **Method Names**:
   - MUST include `Scheduler` in the name
   - Be explicit about the task context
   - Follow verb-noun pattern

3. **CSS Classes**:
   - MUST start with `scheduler-`
   - Use kebab-case
   - Be specific about the component

4. **Storage Keys**:
   - MUST include `Scheduler` in the name
   - Be explicit about stored data
   - Use consistent casing

## Testing Requirements

1. **Naming Convention Tests**:
   - Verify all components use proper prefix
   - Check all method names
   - Validate CSS class names
   - Check storage key names

2. **Integration Tests**:
   - Verify no interference with other systems
   - Check proper state isolation
   - Validate storage separation

3. **UI Tests**:
   - Verify consistent styling
   - Check proper class application
   - Validate component isolation

## Future Considerations

1. **New Features**:
   - Follow naming convention for all new code
   - Document prefix requirement
   - Update validation rules

2. **Code Reviews**:
   - Check for naming consistency
   - Verify proper isolation
   - Validate prefix usage

3. **Documentation**:
   - Keep naming convention docs updated
   - Document rationale for separation
   - Maintain examples of proper usage

## LocalStorage Key Naming Patterns
- Settings Modal: `settingsActiveTab`
- Left Panel: `leftPanelActiveTab`
- Chat Selection: `lastSelectedChat`
- Task Selection: `lastSelectedTask`
- Scheduler: `lastSelectedSchedulerTask`, `schedulerTaskFilter`, `schedulerTaskSort`
- General Settings: `darkMode`, `speech`, `collapseMessages`

## Alpine.js Store Structure
```javascript
Alpine.store('root', {
    reasoning: "auto",
    planning: "auto",
    deep_search: false,
    selectedTab: 'chats' // For left panel tab selection
});
```

## Recent Changes

### [2024-01-XX] LocalStorage Key Standardization
- Updated all localStorage keys to follow camelCase pattern
- Changed `settings-active-tab` to `settingsActiveTab`
- Changed `left-panel-active-tab` to `leftPanelActiveTab`
- Documented naming convention in all relevant files

### [2024-01-XX] Alpine.js Store Improvements
- Ensured proper store initialization timing
- Added safety checks for store existence
- Improved store property updates
- Added documentation for store management

## Implementation Status

### Completed
- ✅ Standardized localStorage key naming to camelCase
- ✅ Fixed Alpine.js store initialization
- ✅ Updated documentation for naming conventions
- ✅ Improved error handling for store access

### Pending
- ⏳ Review any remaining non-standard key names
- ⏳ Add validation for naming conventions in linting
- ⏳ Update tests to reflect naming standards

## Critical Implementation Notes

### Naming Convention Rules
1. **LocalStorage Keys**:
   - MUST use camelCase
   - MUST be descriptive and specific
   - MUST follow established patterns

2. **Alpine.js Store**:
   - MUST initialize during `alpine:init`
   - MUST check for existing store
   - MUST maintain consistent property names

3. **Component Integration**:
   - MUST follow proper initialization order
   - MUST handle store access safely
   - MUST use proper naming conventions

## Testing Requirements

1. **Store Initialization**:
   - Verify store exists after initialization
   - Check all required properties
   - Test store access patterns

2. **Naming Conventions**:
   - Verify all localStorage keys follow camelCase
   - Check component naming consistency
   - Validate CSS class naming

3. **Integration Tests**:
   - Verify tab system functionality
   - Check state persistence
   - Test component interactions

## Future Considerations

1. **Code Quality**:
   - Add automated naming convention checks
   - Improve error handling
   - Enhance documentation

2. **State Management**:
   - Consider more robust store management
   - Improve state synchronization
   - Add better error recovery

3. **Documentation**:
   - Keep naming convention docs updated
   - Document new patterns as they emerge
   - Maintain implementation history

## Container Awareness

- Files in `/app/data` and `/app/config` persist
- UI changes require persistence verification
- Container restart resets non-persistent files
- Always check file persistence
- Development environment is containerized
- Context loss between sessions is assumed

## Performance Notes

- Alpine.js used for reactive UI
- Store initialization timing is critical
- Proper naming helps maintenance
- State management affects performance
- Documentation helps prevent errors

Remember: This scratchpad is part of a three-file system with .context.md and .warning-flags. All three MUST be maintained for proper context retention.

## Task Scheduler System

### System Architecture
- Task scheduler uses a single context storage location:
  - `CHATS_FOLDER` = "tmp/chats" for both regular chat contexts and task contexts
- Tasks are managed through `SchedulerTaskList` class which maintains a list of tasks
- Tasks can be either `ScheduledTask` or `AdHocTask` types
- Chat contexts are saved/loaded using functions in `persist_chat.py`
- Task contexts are identified by checking if their UUID matches a task in the scheduler

### Core Components
1. **Task Types**:
   - `ScheduledTask`: Runs on a cron schedule
   - `AdHocTask`: Runs on demand

2. **Storage System**:
   - Task definitions stored in memory and persisted to JSON
   - Task chat contexts stored in file system alongside regular chats
   - Chat names managed through `ChatNames` class

3. **Context Management**:
   - `AgentContext` objects represent chat/task state
   - Task contexts identified by checking scheduler task UUIDs
   - All contexts stored in the same location

### Task Context Management
- **Current Approach**: All contexts stored in a single `CHATS_FOLDER`
- **Identification Method**: Scheduler.get_task_by_uuid() used to check if a context is a task context
- **Benefits**: Simplified code and reduced complexity of context management

### Task Chat Lifecycle
1. **Creation**:
   - Task created through API
   - Initial context saved to `CHATS_FOLDER`
   - Task name recorded with "TASK:" prefix

2. **Execution**:
   - Context loaded from `CHATS_FOLDER`
   - Agent performs task and accumulates chat history
   - Context saved back to `CHATS_FOLDER`

3. **Reset**:
   - Context file fully removed
   - New empty context created and saved
   - Task name preserved

4. **Deletion**:
   - Task removed from scheduler list
   - Context removed from memory and disk

### Key Functions
- `get_chat_folder_path(ctxid)`: Returns the path to the chats folder
- `save_tmp_chat(context)`: Saves context to the chats folder
- `load_tmp_chats()`: Loads all contexts from the chats folder
- `remove_chat(ctxid)`: Removes context from the chats folder

### Task Chat Reset Fix
- **Problem**: Task chat contexts were not properly reset, causing old messages to reappear
- **Root Cause**: Incorrect folder detection in `get_chat_folder_path`
- **Solution**: Implemented auto-detection to check both folders
- **Key Changes**:
  1. Modified `get_chat_folder_path` to actively check for context existence
  2. Updated `_get_chat_file_path` to support auto-detection
  3. Enhanced `save_tmp_chat` and related functions to properly handle context storage
  4. Fixed `chat_reset.py` to use auto-detection
  5. Updated `scheduler_task_delete.py` to properly clean up context files

### Task Chat Lifecycle
1. **Creation**:
   - Task created through API
   - Initial context saved to `CHATS_FOLDER`
   - Task name recorded with "TASK:" prefix

2. **Execution**:
   - Context loaded from `CHATS_FOLDER`
   - Agent performs task and accumulates chat history
   - Context saved back to `CHATS_FOLDER`

3. **Reset**:
   - Context file fully removed
   - New empty context created and saved
   - Task name preserved

4. **Deletion**:
   - Task removed from scheduler list
   - Context removed from memory and disk

### Key Functions and Parameters
- `get_chat_folder_path(ctxid)`: Returns the path to the chats folder
- `save_tmp_chat(context)`: Saves context to the chats folder
- `load_tmp_chats()`: Loads all contexts from the chats folder
- `remove_chat(ctxid)`: Removes context from the chats folder

### Future Improvements
- Better separation of concerns between task management and context management
- More explicit task type tracking beyond relying on folder location
- Enhanced error handling for context operations
- Unified context lifecycle management

## Settings Modal Implementation Roadmap

### Current State
- Task scheduler backend functionality is largely implemented
- Basic task list is integrated in the left panel
- Settings modal integration is completely missing
- Comprehensive task management UI is required

### Implementation Priorities

1. **Phase 1: Modal Tab Integration**
   - Create scheduler settings tab template
   - Register tab in settings modal system
   - Implement basic layout with sections
   - Add tab switching functionality

2. **Phase 2: Task List Implementation**
   - Create task data table with sorting/filtering
   - Implement status badge components
   - Add action buttons (run, edit, delete)
   - Create list refresh functionality

3. **Phase 3: Task Form Components**
   - Build task creation form
   - Implement task type switching logic
   - Create field validation system
   - Add form submission handling

4. **Phase 4: Advanced Form Elements**
   - Build schedule builder component
   - Implement cron expression helper
   - Create file path selector/validator
   - Add token generation for ad-hoc tasks

5. **Phase 5: UI Polish & Integration**
   - Finalize responsive design
   - Implement loading states
   - Add success/error toasts
   - Ensure consistent styling

### Component Architecture

1. **Modal Tab Structure**
   ```html
   <div x-show="activeTab === 'scheduler'" class="settings-section">
     <div class="scheduler-controls">
       <!-- Filter/sort controls -->
       <button class="scheduler-btn-new">New Task</button>
     </div>
     <div class="scheduler-task-table">
       <!-- Task list with details -->
     </div>
     <div x-show="showTaskForm" class="scheduler-task-form">
       <!-- Task form -->
     </div>
   </div>
   ```

2. **Task List Component**
   ```javascript
   Alpine.data('schedulerTaskTable', () => ({
     tasks: [],
     filteredTasks: [],
     sortBy: 'name',
     sortOrder: 'asc',
     filterType: 'all',
     filterStatus: 'all',

     init() {
       this.loadTasks();
     },

     async loadTasks() {
       // Implementation
     },

     // Sort, filter, and action methods
   }));
   ```

3. **Task Form Component**
   ```javascript
   Alpine.data('schedulerTaskForm', () => ({
     task: {
       name: '',
       type: 'scheduled',
       schedule: { minute: '*', hour: '*', day: '*', month: '*', weekday: '*' },
       token: '',
       system_prompt: '',
       prompt: '',
       attachments: []
     },
     validationErrors: {},
     isEditing: false,
     editId: null,

     // Form handling methods
   }));
   ```

4. **Schedule Builder Component**
   ```javascript
   Alpine.data('schedulerCronBuilder', () => ({
     schedule: { minute: '*', hour: '*', day: '*', month: '*', weekday: '*' },
     humanReadable: '',

     init() {
       this.updateHumanReadable();
     },

     updateHumanReadable() {
       // Implementation
     },

     // Cron builder methods
   }));
   ```

### Integration Points

1. **Settings Module Integration**:
   - Modify `settings.js` to add scheduler tab
   - Register tab in `setupTabs()` function
   - Add tab to settings modal HTML template

2. **API Integration**:
   - Use existing `/scheduler_tasks_list` endpoint
   - Implement form submission via `/scheduler_task_create` and `/scheduler_task_update`
   - Add task deletion via `/scheduler_task_delete`
   - Implement task execution via `/scheduler_task_run`

3. **CSS Integration**:
   - Add scheduler-specific styles to `settings.css`
   - Ensure consistent styling with other modal sections
   - Implement responsive design rules

4. **Validation Integration**:
   - Use existing validation rules from `task_scheduler.py`
   - Implement client-side validation mirroring server rules
   - Add real-time validation feedback

### Technical Considerations

1. **Alpine.js Components**:
   - Use Alpine.js data components for reactivity
   - Leverage x-for for list rendering
   - Implement proper form bindings for two-way data flow
   - Use x-show/x-if for conditional rendering

2. **Responsive Design**:
   - Implement table view for desktop
   - Create card view for mobile
   - Use flex layouts for adaptable forms
   - Ensure proper spacing and readability

3. **Performance Optimization**:
   - Implement pagination for large task lists
   - Use debounced search for filtering
   - Optimize API calls with proper caching
   - Minimize reflows during form updates

4. **Testing Strategy**:
   - Test form validation logic
   - Verify sorting and filtering functionality
   - Check responsive behavior across devices
   - Validate API integration points

This roadmap provides a structured approach to implementing the settings modal for the task scheduler, focusing on the UI components needed to complete the feature while leveraging the existing backend functionality.

## API Handler Refactoring

### Current Issues

1. **Inconsistent API Handler Implementation**:
   - Modern handlers extend `ApiHandler` class and implement the `process()` method
   - Legacy handlers are standalone `handle_request()` functions (not class methods)
   - The parent `ApiHandler` class has a `handle_request()` method that internally calls `process()`
   - Child handlers should NEVER override `handle_request()`, only implement `process()`

2. **Unnecessary Dependencies**:
   - `request_helpers.py` module is only used by legacy handlers
   - Functions like `build_cors_preflight_response`, `build_cors_actual_response` are not needed

3. **Type Checking Issues**:
   - Linter errors when accessing type-specific attributes (schedule, token)
   - Need explicit type checking to handle different task types

### Refactoring Plan

1. **Convert Legacy Handlers to Modern Format**:
   - Replace standalone `handle_request()` functions with classes that extend `ApiHandler`
   - Implement the required `process()` method (NOT `handle_request()`)
   - Remove CORS-related response building (handled by the parent class)
   - Fix type checking for task attributes

2. **API Handlers to Update**:
   - ✅ `scheduler_tasks_list.py`: Converted to use ApiHandler
   - ✅ `scheduler_task_create.py`: Converted to use ApiHandler
   - ❌ `scheduler_task_delete.py`: Needs conversion
   - ❌ `scheduler_task_run.py`: Needs conversion
   - ❌ `scheduler_task_update.py`: Needs conversion
   - ✅ `scheduler_tasks_get.py`: Already using ApiHandler
   - ✅ `scheduler_tick.py`: Already using ApiHandler

3. **Remove Unused Code**:
   - After all handlers are converted, `request_helpers.py` can be removed
   - Clean up unnecessary imports

4. **Fix Type Checking**:
   - Use `isinstance()` to check task types
   - Add type annotations for better IDE support
   - Cast variables to specific types for attribute access

### Implementation Notes

For each legacy handler, follow this pattern:

1. Import `ApiHandler`, `Input`, `Output`, `Request` from `python.helpers.api`
2. Create a class that extends `ApiHandler`
3. Implement `async def process(self, input: Input, request: Request) -> Output:`
4. Copy the logic from the existing standalone `handle_request` function
5. Remove CORS-related code and simplify response handling
6. Fix type checking for task attributes

Example conversion:

```python
# Before - Legacy standalone function
def handle_request(environ):
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        return build_cors_preflight_response()

    # Logic here

    return build_cors_actual_response(json.dumps(response))

# After - Modern ApiHandler class
class MyHandler(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        # Logic here
        return response  # Handle_request in parent class will format the response
```

Fixing type checking:

```python
# Before - causes linter errors
if is_scheduled:
    task_json['schedule'] = {
        'minute': task.schedule.minute,  # Error: Cannot access attribute "schedule" for class "AdHocTask"
    }

# After - type-safe
if isinstance(task, ScheduledTask):
    scheduled_task = cast(ScheduledTask, task)
    task_json['schedule'] = {
        'minute': scheduled_task.schedule.minute,  # No error
    }
```

### Benefits of Refactoring

1. **Consistency**: All API handlers follow the same pattern
2. **Type Safety**: Proper type checking avoids runtime errors
3. **Simplicity**: No unnecessary CORS handling for local API calls
4. **Maintainability**: Easier to understand and modify code
5. **Reduced Dependencies**: Remove unnecessary code and imports

## Critical Lessons Learned

### API and Endpoint Handling
- **ALWAYS VERIFY ENDPOINTS**: Before referencing or creating endpoints, check the actual files in the API folder
- **ENDPOINT NAMING PATTERN**: Endpoints are named after their Python files (e.g., `contexts.py` = `/contexts` endpoint)
- **MODULE STRUCTURE**: Python modules need proper __init__.py files and correct import paths
- **CREATE BEFORE REFERENCING**: When introducing new endpoints, create the backend file first, then reference it in frontend

### Code Structure and Organization
- **AVOID DUPLICATION**: Extract shared functionality into reusable modules (like context_processor.py)
- **FOLLOW ESTABLISHED PATTERNS**: Study existing code to understand patterns and conventions
- **PROPER MODULE STRUCTURE**: Ensure Python packages have the necessary structure (proper __init__.py files)
- **TEST INCREMENTALLY**: Make and test small changes before committing to larger architectural changes

### UI Component Integration
- **ALPINE STORE HANDLING**: Careful management of Alpine.js stores is essential
- **DATA FLOW CONSISTENCY**: Be consistent in how components fetch and use data
- **REACTIVE UPDATES**: Consider how reactive UI updates are triggered and managed

### Communication Patterns
- **LISTEN TO USER GUIDANCE**: Pay close attention to user suggestions and domain knowledge
- **VERIFY BEFORE SUGGESTING**: Check assumptions against actual code before making recommendations
- **ACKNOWLEDGE MISTAKES PROMPTLY**: Quickly admit when an approach isn't working and pivot
- **DOCUMENT CLEARLY**: Maintain comprehensive notes about code patterns and decisions

## API Handler Loading System

### Automatic API Handler Registration

The application uses an automated system to register API handlers without requiring manual registration. This is a critical feature to understand:

1. **Handler Discovery Process**:
   - In `run_ui.py`, the `load_classes_from_folder()` function is called to load all API handlers
   - This function scans the "python/api" directory for Python files matching "*.py"
   - It filters for classes that extend the `ApiHandler` base class
   - Each discovered handler is automatically registered via `register_api_handler()`

2. **Key Implementation in `run_ui.py`**:
   ```python
   # initialize and register API handlers
   handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)
   for handler in handlers:
       register_api_handler(app, handler)
   ```

3. **How `load_classes_from_folder` Works**:
   - Located in `python/helpers/extract_tools.py`
   - Takes parameters: folder path, filename pattern, base class, and one_per_file flag
   - Imports each module dynamically using `importlib.import_module()`
   - Uses `inspect.getmembers()` to find classes in the module
   - Filters for classes that are subclasses of the specified base class
   - Returns a list of class types that meet the criteria

4. **Handler-to-Endpoint Mapping**:
   - Each API handler class is automatically mapped to an endpoint
   - The endpoint name is derived from the Python file name (minus the .py extension)
   - For example, `scheduler_tasks_list.py` becomes the `/scheduler_tasks_list` endpoint

### ⚠️ CRITICAL IMPLEMENTATION NOTES ⚠️

1. **Never Manually Register Handlers**:
   - NEVER add manual `register_api_handler()` calls for handlers in the "python/api" directory
   - The automatic discovery system handles this automatically
   - Manual registration leads to duplicate endpoints and errors

2. **Proper Handler Implementation**:
   - API handlers MUST extend the `ApiHandler` base class
   - Handlers MUST implement the `process()` method (NOT `handle_request()`)
   - The parent class handles request parsing and response formatting

3. **Endpoint Naming Convention**:
   - Endpoint URLs are derived from Python filenames
   - File naming should follow the snake_case convention
   - Names should be descriptive of the handler's function

4. **Handler Location Requirements**:
   - Handlers MUST be placed in the "python/api" directory to be discovered
   - Subdirectories are not automatically scanned by default
   - Each file should contain only one handler class (due to one_per_file=True)

### Best Practices for Adding New API Handlers

1. **Create the Handler File First**:
   - Always create the Python file in the "python/api" directory first
   - Ensure it extends `ApiHandler` and implements `process()`
   - Test it before referencing the endpoint in frontend code

2. **Follow Existing Patterns**:
   - Study existing handlers to understand the pattern
   - Keep handler logic focused on a single responsibility
   - Maintain consistent error handling and response formatting

3. **Type Safety**:
   - Use proper type annotations for `Input`, `Output`, and `Request`
   - Implement type checking for conditional logic
   - Cast variables when necessary for attribute access

4. **Documentation**:
   - Document the handler's purpose and API contract
   - Include example request/response formats
   - Note any authentication or permission requirements

### Example Handler Implementation

```python
from python.helpers.api import ApiHandler, Input, Output, Request

class MyNewHandler(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        # Validate input
        if 'required_field' not in input:
            return {'error': 'Missing required field'}

        # Process request
        result = self.perform_operation(input['required_field'])

        # Return response
        return {'result': result}

    def perform_operation(self, data):
        # Implementation details
        return processed_data
```

By understanding this automatic handler registration system, we can avoid manual registration attempts that would create duplicate endpoints and lead to errors.

# Task Scheduler Feature Overview

## Current Implementation Status

### Backend
- 7 API endpoints exist in `python/api/` directory:
  - `scheduler_task_create.py` - Creates new tasks
  - `scheduler_task_delete.py` - Deletes tasks by UUID and cleans up associated contexts
  - `scheduler_tasks_get.py` - Lists all tasks with their types (scheduled vs adhoc)
  - `scheduler_task_run.py` - Manually triggers a task to run
  - `scheduler_task_update.py` - Updates task properties (has linter errors, now fixed)
  - `scheduler_tick.py` - Periodic endpoint for checking and running due tasks
  - (One more endpoint not identified yet)

- Core task scheduler implementation in `python/helpers/task_scheduler.py`:
  - `TaskSchedule` - Cron-like schedule representation
  - `AdHocTask` - On-demand tasks (no schedule)
  - `ScheduledTask` - Tasks with schedules
  - `SchedulerTaskList` - Collection of tasks with CRUD methods
  - `TaskScheduler` - Main orchestration class

### Task Models
From `task_scheduler.py`, the task models are:

1. **TaskSchedule** - Represents a cron schedule
   ```python
   class TaskSchedule(BaseModel):
       minute: str
       hour: str
       day: str
       month: str
       weekday: str
   ```

2. **AdHocTask** - On-demand task without a schedule
   ```python
   class AdHocTask(BaseModel):
       uuid: str
       state: Literal["idle", "running", "disabled", "error"]
       name: str
       system_prompt: str
       prompt: str
       attachments: list[str]
       ctx_planning: Literal["on", "off", "auto"]
       ctx_reasoning: Literal["on", "off", "auto"]
       ctx_deep_search: Literal["on", "off"]
       # ... other fields
   ```

3. **ScheduledTask** - Task with a cron schedule
   ```python
   class ScheduledTask(BaseModel):
       uuid: str
       state: Literal["idle", "running", "disabled", "error"]
       name: str
       schedule: TaskSchedule
       system_prompt: str
       prompt: str
       attachments: list[str]
       ctx_planning: Literal["on", "off", "auto"]
       ctx_reasoning: Literal["on", "off", "auto"]
       ctx_deep_search: Literal["on", "off"]
       # ... other fields
   ```

4. **SchedulerTaskList** - Collection of tasks
   ```python
   class SchedulerTaskList(BaseModel):
       tasks: list[Union[ScheduledTask, AdHocTask]]
   ```

### Frontend
- Left panel has a simplified task list view (implemented)
- Settings modal has a Scheduler Tab with early implementation
- `scheduler_tasks.js` contains several functions:
  - `openSchedulerTaskListModal()` - Opens the task list modal
  - `runSchedulerTask(taskId)` - Triggers a task to run via API
  - `showEditorModal(data, type, title, description)` - Shows a modal for editing task data
  - `openSchedulerTaskSettings(taskId)` - Opens settings for a specific task
  - `resetSchedulerTaskContext(taskId)` - Resets the context for a task

- CSS classes for scheduler UI with `scheduler-` prefix exist in `index.css`

## Task Management APIs

Based on the API handlers:

1. **Task Creation** - `scheduler_task_create.py`
   - Creates new tasks (AdHoc or Scheduled)
   - Requires name, prompts, and optional schedule

2. **Task Deletion** - `scheduler_task_delete.py`
   - Deletes a task by UUID
   - Also cleans up associated contexts

3. **Task Listing** - `scheduler_tasks_get.py`
   - Returns a list of all tasks with metadata
   - Adds type information (scheduled vs adhoc)

4. **Task Running** - `scheduler_task_run.py`
   - Manually triggers a task to run
   - Checks for already running state

5. **Task Updating** - `scheduler_task_update.py`
   - Updates task properties
   - Handles schedule updates for scheduled tasks

6. **Scheduler Tick** - `scheduler_tick.py`
   - Periodic background task that checks for due tasks
   - Requires loopback authentication

## Missing Index.html

The index.html file is not directly accessible in the outline, making it challenging to inspect the overall HTML structure, including how the settings modal and task view are organized. I need to look at other references to understand the structure better.

## Scheduler Tasks JS Functions

Based on the function names in `scheduler_tasks.js`, we can infer:

1. Tasks can be run via UI (`runSchedulerTask`)
2. Task data can be edited in a modal (`showEditorModal`)
3. Task settings can be opened for editing (`openSchedulerTaskSettings`)
4. Task contexts can be reset (`resetSchedulerTaskContext`)
5. A task list modal can be opened (`openSchedulerTaskListModal`)

This suggests the tasks can be managed via UI actions, but it's unclear if there's a proper interface for creating new tasks or for viewing the complete task list in the settings modal.

## Settings Modal Structure
From `settings.js` and `settings.css`, we can infer:

1. The settings modal uses an Alpine.js component (`x-data="settings"`) with methods:
   - `init()` - Initializes the component
   - `initializeFilteredSections()` - Sets up sections for display
   - `switchTab(tab)` - Changes active tab
   - `openModal()` - Opens the settings modal
   - `handleButton(buttonId)` - Handles button clicks
   - `handleCancel()` - Handles cancel action
   - `handleFieldButton(field)` - Handles field-specific button clicks

2. Settings data structure:
   - Backed by Python `Settings` TypedDict in `settings.py`
   - Converted to UI-friendly format with `convert_out` function
   - Sections are organized with tab identifiers

3. The modal likely has:
   - A tab navigation bar (`.settings-tabs`)
   - Tab buttons (`.settings-tab`)
   - Section containers for each tab
   - Fields with different input types (text, number, select, etc.)

4. Each settings section contains:
   - id: unique identifier
   - title: display name
   - description: help text
   - fields: array of input fields
   - tab: which tab this section belongs to

5. Each field has:
   - id: unique identifier
   - title: display name
   - description: help text
   - type: input type (text, number, select, etc.)
   - value: current value
   - min/max/step: for numeric inputs
   - options: array of options for select inputs

## Issues & Warnings
- Linter errors in `scheduler_task_update.py` - trying to access `schedule` attribute on `AdHocTask` (FIXED)
- Several warning flags:
  - `SCHEDULER_SETTINGS_MODAL_PENDING=TRUE`
  - `SCHEDULER_NAMING_CONVENTION_REQUIRED=TRUE`
  - `SCHEDULER_COMPONENTS_USE_ALPINE_DATA=TRUE`
  - `SCHEDULER_CSS_PREFIX_REQUIRED=TRUE`
  - `SCHEDULER_VALIDATION_MIRRORED_CLIENT_SERVER=TRUE`
  - `USE_EXISTING_TASK_SCHEDULER_API=TRUE`

## UI Patterns & Best Practices
- Alpine.js for reactive UI components
  - State management through Alpine.store()
  - Creating new array instances to trigger reactivity
  - Careful initialization of data
  - Event delegation for dynamic content
- Settings modal uses tabbed interface with filtered sections
- CSS follows clear naming conventions with component-specific prefixes

## Left Panel Task List Implementation
From examining the CSS and structure:

1. Tasks are presented in a container with class `.tasks-list-container`
2. Individual tasks use `.task-name` styling
3. The tabs system switches between chats and tasks
4. Task list uses Alpine.js for reactivity

## Tab System Implementation
Based on the CSS classes and JavaScript functions:

1. Tabs are contained in a `.tabs-container`
2. Individual tabs use `.tab` class
3. Active tab has `.active` class
4. Tab switching logic stores the active tab in localStorage
5. Content for tabs is shown/hidden based on the active tab

## UI Requirements for Task Management

Based on the backend models and existing frontend, a complete task management UI should have:

1. **Task List View**
   - Display name, status (idle, running, disabled, error)
   - Show task type (scheduled vs adhoc)
   - Actions (run, edit, delete, reset context)
   - Sort/filter capabilities

2. **Task Creation/Edit Form**
   - Name field
   - System prompt field
   - Prompt field
   - Attachment handling
   - Context settings (planning, reasoning, deep search)
   - Task type selection (adhoc/scheduled)
   - Schedule builder for scheduled tasks

3. **Schedule Builder**
   - Fields for cron components (minute, hour, day, month, weekday)
   - Helper UI for building cron expressions
   - Validation for cron syntax

## Implementation Plan for Scheduler Settings

### 1. Add Scheduler Tab to Settings Modal

1. Identify where the existing tabs are defined in the settings modal
2. Add a new tab for "Task Scheduler" with proper styling
3. Ensure it follows the existing tab pattern with:
   - `.settings-tab` class
   - Tab switching logic via Alpine.js

### 2. Create Basic Task List Section

1. Add a new section for the task list with:
   - Section title: "Scheduled Tasks"
   - Description: "Manage and monitor automated tasks"
   - Tab identifier: "scheduler"

2. Create a task list container with:
   - `.scheduler-tasks-list-container` class for styling
   - Alpine.js data binding for tasks
   - Empty state message when no tasks are available

3. Add a "New Task" button:
   - Follow existing button styling patterns
   - Connect to task creation flow

### 3. Implement Task List Items

1. Create a template for task list items with:
   - Task name with `.scheduler-task-name` class
   - Status badge with appropriate status class
   - Type indicator (scheduled/adhoc)
   - Action buttons (run, edit, delete, reset)

2. Connect task actions to appropriate API endpoints:
   - Run → `/api/scheduler_task_run`
   - Edit → Open edit form
   - Delete → `/api/scheduler_task_delete`
   - Reset → Context reset function

### 4. Create Task Edit/Create Form

1. Create a modal form with:
   - Task name field (required)
   - System prompt textarea
   - User prompt textarea
   - Type selector (adhoc/scheduled)
   - Context settings (planning, reasoning, deep search toggles)

2. Add conditional schedule builder for scheduled tasks:
   - Show/hide based on task type
   - Inputs for minute, hour, day, month, weekday
   - Helper text explaining cron format

3. Add validation:
   - Client-side validation matching server requirements
   - Error messages for invalid inputs

4. Connect form submission to API endpoints:
   - Create → `/api/scheduler_task_create`
   - Update → `/api/scheduler_task_update`

### 5. Implement Schedule Builder

1. Create a UI component for building cron expressions:
   - Simple text inputs for each component
   - Dropdowns or helpers for common values
   - Preview of resulting schedule

2. Add validation for cron expressions:
   - Check format for each component
   - Ensure values are within valid ranges

### 6. Add CSS Styling

1. Create new CSS classes with `scheduler-` prefix:
   - `.scheduler-section`
   - `.scheduler-form`
   - `.scheduler-schedule-builder`
   - `.scheduler-task-item`

2. Follow existing CSS patterns:
   - Use CSS variables for colors and spacing
   - Maintain dark/light mode compatibility
   - Ensure responsive design

### 7. Implement Alpine.js Logic

1. Add Alpine data store or component:
   ```javascript
   Alpine.data('schedulerTasks', function() {
     return {
       tasks: [],
       loading: false,
       editingTask: null,

       init() {
         this.loadTasks();
       },

       async loadTasks() {
         // Fetch tasks from API
       },

       // ... other methods
     }
   });
   ```

2. Implement reactive UI updates:
   - Create new arrays when updating task lists
   - Handle loading states
   - Show/hide UI components based on state

### 8. Connect to Existing API Endpoints

1. Implement API calls:
   - GET tasks list
   - POST create task
   - PUT update task
   - DELETE task
   - POST run task

2. Handle API responses:
   - Success messages
   - Error handling
   - UI state updates

## Next Steps
1. Locate where to add the scheduler tab in the settings modal
2. Implement the task list view in the settings modal
3. Create the task creation/editing form
4. Implement the schedule builder component
5. Connect the UI to the API endpoints

## Questions to Resolve
- Is there a specific design for the scheduler settings tab?
- What additional validation is needed for task creation/editing?
- How should the cron schedule builder be implemented?
- Are there any missing API endpoints needed for the complete UI?

## Latest Implementation Updates

### [2024-06-XX] Task Manual Execution Fix
- Created new API endpoint `scheduler_task_run.py` for manually running tasks
- Updated frontend `runTask` function to use correct endpoint
- Clarified purpose of `scheduler_tick.py` vs `scheduler_task_run.py`
- Fixed functionality according to proper design:
  - `scheduler_tick.py` - Only for cron-based scheduled execution (called by system cron)
  - `scheduler_task_run.py` - For manual execution through UI (called by user action)
- Improved error handling in both endpoints
- Added proper task state checking before execution

### Key Implementation Details
1. **Scheduler Tick Endpoint**:
   - Purpose: Automatically check and run all due tasks based on their schedules
   - Execution: Called automatically by system cron job every minute
   - Pattern: Scans all tasks and runs those with schedules that are due
   - Authentication: Requires loopback (only accessible from localhost)
   - Not intended for manual execution of specific tasks

2. **Task Run Endpoint**:
   - Purpose: Allow manual execution of a specific task
   - Execution: Called manually through UI "Run" button
   - Pattern: Targets a single task by UUID
   - Authentication: Requires user authentication
   - Includes state checking to prevent running already-running tasks

3. **Task Execution Implementation**:
   - Both endpoints ultimately use `TaskScheduler.run_task_by_uuid()` method
   - Tasks run asynchronously through `DeferredTask` mechanism
   - State transitions handled automatically (idle → running → idle)
   - Execution respects context settings (planning, reasoning, deep_search)
   - Results and errors are properly stored in task state

### Frontend Integration
1. **UI Actions**:
   - "Run" button now correctly calls the `scheduler_task_run` endpoint
   - Updated error handling to display meaningful messages
   - Added UI feedback during task execution
   - Implemented automatic refresh after task execution starts

2. **API Interaction**:
   - All API calls use proper JSON format
   - Error handling at both frontend and backend levels
   - State transitions properly reflected in UI
   - Task status updates visible to user

## Task Scheduler Implementation Insights (2024-07-18)

### Check Schedule Methods

The `check_schedule` method is a crucial part of the task scheduler system as it determines when tasks should run. Each task type implements its own version:

1. **BaseTask Implementation**:
   ```python
   def check_schedule(self, frequency_seconds: float = 60.0) -> bool:
       return False
   ```
   - Base implementation returns False by default
   - Serves as fallback for any task types that don't override it
   - Parameter `frequency_seconds` represents the polling window (typically 60 seconds)

2. **ScheduledTask Implementation**:
   ```python
   def check_schedule(self, frequency_seconds: float = 60.0) -> bool:
       with self._lock:
           crontab = CronTab(crontab=self.schedule.to_crontab())
           # Get the timezone from the schedule or use UTC as fallback
           task_timezone = pytz.timezone(self.schedule.timezone or Localization.get().get_timezone())
           # Get reference time in task's timezone (by default now - frequency_seconds)
           reference_time = datetime.now(timezone.utc) - timedelta(seconds=frequency_seconds)
           reference_time = reference_time.astimezone(task_timezone)
           # Get next run time as seconds until next execution
           next_run_seconds: Optional[float] = crontab.next(now=reference_time, return_datetime=False)
           if next_run_seconds is None:
               return False
           return next_run_seconds < frequency_seconds
   ```
   - Uses CronTab library to parse and evaluate cron expressions
   - Handles timezone conversion for proper schedule evaluation
   - Checks if the next scheduled run time falls within the frequency window
   - Returns True if the task should run, False otherwise

3. **PlannedTask Implementation**:
   ```python
   def check_schedule(self, frequency_seconds: float = 60.0) -> bool:
       with self._lock:
           return self.plan.should_launch() is not None
   ```
   - Uses `TaskPlan.should_launch()` to check if any planned datetime is due
   - Simple delegation to the plan object which handles the datetime comparisons
   - Thread-safe with lock to prevent race conditions

### Task Scheduler Execution Flow

The execution flow is orchestrated by the `TaskScheduler` class:

1. **Tick Method**: Called periodically (usually by cron job every minute):
   ```python
   async def tick(self):
       for task in await self._tasks.get_due_tasks():
           await self._run_task(task)
   ```

2. **Get Due Tasks**: Identifies which tasks should be executed now:
   ```python
   async def get_due_tasks(self) -> list[Union[ScheduledTask, AdHocTask, PlannedTask]]:
       with self._lock:
           await self.reload()
           return [
               task for task in self.tasks
               if task.check_schedule() and task.state == TaskState.IDLE
           ]
   ```
   - Reloads the task list to ensure latest state
   - Filters tasks where `check_schedule()` returns True AND state is IDLE
   - This is where the different task types' check_schedule implementations come into play

3. **Run Task**: Executes tasks that are due:
   ```python
   async def _run_task(self, task: Union[ScheduledTask, AdHocTask, PlannedTask]):
       async def _run_task_wrapper(task_uuid: str):
           # Task setup and execution logic
           await current_task.on_run()
           # Agent execution
           result = await agent.monologue()
           # Success
           await current_task.on_success(result)

       deferred_task = DeferredTask(thread_name=self.__class__.__name__)
       deferred_task.start_task(_run_task_wrapper, task.uuid)
   ```
   - Runs task in a background thread via DeferredTask
   - Tasks execute asynchronously to avoid blocking the main thread
   - Calls lifecycle hooks (on_run, on_success, on_error)

### PlannedTask Progression

The `PlannedTask` class has a unique execution model centered around a `TaskPlan` that manages a progression of datetime items:

1. **TaskPlan Structure**:
   ```python
   class TaskPlan(BaseModel):
       todo: list[datetime] = Field(default_factory=list)
       in_progress: datetime | None = None
       done: list[datetime] = Field(default_factory=list)
   ```
   - Maintains todo, in_progress, and done lists of datetimes
   - Tracks progression through the plan items

2. **Lifecycle Hooks**:
   ```python
   async def on_run(self):
       with self._lock:
           # Get the next launch time and set it as in_progress
           next_launch_time = self.plan.should_launch()
           if next_launch_time is not None:
               self.plan.set_in_progress(next_launch_time)
       await super().on_run()

   async def on_success(self, result: str):
       with self._lock:
           # If there's an in_progress time, mark it as done
           if self.plan.in_progress is not None:
               self.plan.set_done(self.plan.in_progress)
       # Call the parent implementation to update state, etc.
       await super().on_success(result)
   ```
   - `on_run` moves a todo item to in_progress state
   - `on_success` moves the in_progress item to done state
   - Both use locks to ensure thread safety during state transitions

3. **TaskPlan Methods**:
   ```python
   def should_launch(self) -> datetime | None:
       next_launch_time = self.get_next_launch_time()
       if next_launch_time is None:
           return None
       # return next launch time if current datetime utc is later than next launch time
       if datetime.now(timezone.utc) > next_launch_time:
           return next_launch_time
       return None
   ```
   - `should_launch()` checks if the next todo item is due
   - Returns the datetime if it should launch now, otherwise None
   - This powers the PlannedTask's check_schedule implementation

### Critical Insights

1. **Thread Safety**:
   - All operations that modify task state use locks to prevent race conditions
   - The `TaskScheduler` uses atomic updates with verification callbacks
   - PlannedTask state transitions are particularly sensitive and require careful locking

2. **Timezone Handling**:
   - All datetimes are stored in UTC with timezone awareness
   - Conversion to local timezone happens during schedule evaluation
   - This ensures consistent behavior across different server timezones

3. **Task State Transitions**:
   - Tasks follow a state machine (IDLE → RUNNING → IDLE/ERROR)
   - State updates are done atomically through the TaskScheduler
   - Each task type can customize behavior at transition points via lifecycle hooks

4. **Execution Model**:
   - Tasks run in background threads to avoid blocking the main thread
   - The `tick()` method serves as the entry point for scheduled execution
   - Manual execution is triggered via the `run_task_by_uuid()` method

5. **Different Task Types**:
   - ScheduledTask: Time-based execution using cron expressions
   - AdHocTask: Manual execution only, no automatic scheduling
   - PlannedTask: Datetime-based execution with progression tracking

6. **Extension Points**:
   - Custom task types can be created by extending BaseTask
   - Lifecycle hooks (on_run, on_success, on_error, on_finish) provide customization points
   - The check_schedule method determines execution timing

This architecture provides a flexible and extensible task scheduling system with support for different scheduling patterns and proper thread safety.

## Critical Fix: PlannedTask Error Handling (2023-07-03)

A critical bug was discovered and fixed in the `PlannedTask` class's error handling. When a planned task encountered an error during execution, the plan item was left in an "in_progress" state permanently, causing it to be stuck and never moving to the "done" state.

### Issue Details
- When a `PlannedTask` succeeded, its `on_success` method properly moved the current plan item from `in_progress` to `done`
- However, when an error occurred, there was no equivalent handler in the `on_error` method to mark the task as done
- This resulted in plan items getting stuck in the "in_progress" state when errors occurred
- Over time, this could lead to task plans becoming unusable as items never progressed

### Implementation Fix
Added an `on_error` method to the `PlannedTask` class that marks the current in-progress item as done before calling the parent's error handler:

```python
async def on_error(self, error: str):
    with self._lock:
        # If there's an in_progress time, mark it as done even on error
        # This ensures plan items don't get stuck in in_progress state when errors occur
        if self.plan.in_progress is not None:
            self.plan.set_done(self.plan.in_progress)
    # Call the parent implementation to update state, etc.
    await super().on_error(error)
```

This fix ensures consistent behavior between success and error cases, preventing planned tasks from getting stuck in an inconsistent state when errors occur during execution.

### Impact
- Previously, if a task encountered an error, the plan item would remain in the "in_progress" state indefinitely
- This could lead to "zombie" tasks that would never progress
- The fix ensures that plan items are properly marked as "done" even when the task fails
- This maintains the integrity of the task plan progression regardless of execution outcome

### Additional Findings
The PlannedTask class uses a locking mechanism (with self._lock) to ensure thread-safety during state transitions, which is critical since the TaskScheduler runs tasks in background threads. The newly added error handling follows the same locking pattern as the success handling to maintain consistent behavior.
