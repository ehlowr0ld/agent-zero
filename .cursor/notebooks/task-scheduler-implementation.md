# Task Scheduler Implementation

## Design Requirements

### Naming Conventions
- **IMPORTANT**: All task scheduler related classes, files, and endpoints must follow a consistent naming convention:
  - Python classes should be prefixed with `Scheduler` (e.g., `SchedulerTask`, `SchedulerTaskList`)
  - JavaScript classes/components should be prefixed with `scheduler` (e.g., `schedulerTasks`)
  - CSS classes should be prefixed with `scheduler-` (e.g., `scheduler-task-item`)
  - API endpoints should be prefixed with `scheduler_` (e.g., `/scheduler_tasks_list`, `/scheduler_task_update`)

### Core Functionality
- Support for scheduled tasks with cron-style scheduling
- Support for ad-hoc tasks triggered by token
- Task management (CRUD operations)
- Task execution and status tracking
- Comprehensive validation system
- Execution history tracking
- Duration tracking and formatting

### Architecture
- Backend implementation in Python
- Frontend implementation with Alpine.js
- RESTful API interface
- Task state persistence
- Unified validation endpoint

## Implementation Status
- [x] Task scheduler data models (Implemented)
- [x] Core TaskScheduler class (Implemented)
- [x] JSON serialization for task persistence (Implemented)
- [x] Thread safety with locks (Implemented)
- [x] Left panel task list view (Implemented)
- [x] Context management system (Implemented)
- [x] scheduler_tick.py API endpoint (Implemented)
- [ ] Other API handlers for task management (Skeleton files only)
- [ ] Frontend UI for task editing (Not implemented)
- [ ] Settings modal task scheduler tab (Not implemented)
- [ ] Unified validation system (Not implemented)
- [ ] Execution history tracking (Not implemented)
- [ ] Duration tracking and formatting (Not implemented)
- [ ] Real-time validation feedback (Not implemented)
- [ ] File picker interface (Not implemented)
- [ ] Schedule builder UI (Not implemented)
- [ ] Enhanced validation error display (Not implemented)

## Planned Features

### Validation System
1. **Unified Backend Validation**:
   - Single endpoint `/scheduler_validate_task`
   - Comprehensive field validation
   - Cross-field dependency checks
   - File system validation
   - State transition validation

2. **Validation Rules**:
   ```python
   # Task Name
   - Length: 3-50 characters
   - Pattern: Must start/end with alphanumeric
   - Uniqueness: Across all tasks

   # Schedule (for scheduled tasks)
   - Valid cron expression
   - All fields required (minute, hour, day, month, weekday)

   # Token (for ad-hoc tasks)
   - Length: 8-32 characters
   - Must contain: uppercase, lowercase, number
   - Must start/end with alphanumeric
   - Uniqueness: Across all ad-hoc tasks

   # Prompts
   - System Prompt: Optional, max 2000 chars
   - User Prompt: Required, 10-2000 chars

   # Attachments
   - Maximum: 10 files
   - Size Limits: 10MB per file, 50MB total
   - Must be absolute paths
   - Must exist and be readable

   # State Transitions
   idle → [running, disabled]
   running → [idle, error]
   disabled → [idle]
   error → [idle, disabled]
   ```

### Execution History
- Tracks last 10 executions
- Records state, result, and duration
- Formats duration in HH:MM:SS
- Timestamps in ISO format

### State Management
- Explicit state machine implementation
- Validated state transitions
- Error state handling
- Duration tracking

## Core Components

### Task Models (Implemented)
1. **TaskBase**:
   - Common fields for all tasks
   - State management
   - Execution history
   - Duration tracking

2. **ScheduledTask** (Implemented):
   - Cron-style scheduling
   - Next run calculation
   - Schedule validation

3. **AdHocTask** (Implemented):
   - Token-based execution
   - Token validation
   - Unique token enforcement

### API Endpoints (Partially Implemented)
1. **Task Management** (Skeleton files only):
   - `/scheduler_tasks_list`: List tasks with filtering
   - `/scheduler_task_create`: Create new tasks
   - `/scheduler_task_update`: Update existing tasks
   - `/scheduler_task_delete`: Delete tasks

2. **Task Execution** (Partially implemented):
   - `/scheduler_task_run`: Run task immediately (Skeleton only)
   - `/scheduler_tick`: Process due tasks (Fully implemented)

3. **Validation** (Not implemented):
   - `/scheduler_validate_task`: Unified validation endpoint

### Frontend Components
1. **Task List**:
   - Filtering by type and status
   - Sorting by multiple fields
   - Status badge display
   - Action buttons

2. **Task Form**:
   - Real-time validation
   - Schedule input
   - Token generation
   - File path input

3. **Status Display**:
   - Color-coded status badges
   - Execution history
   - Duration display
   - Error messages

## Next Steps
1. Implement file picker interface
2. Create schedule builder UI
3. Enhance validation error display
4. Add template variable support
5. Optimize file validation performance

## Technical Debt
1. File picker interface needed
2. Schedule builder UI would improve UX
3. Template variable support in prompts
4. Enhanced file type validation
5. Performance optimization for file validation

## Critical Implementation Notes
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

4. **State Management**:
   - Explicit state transitions
   - Error state handling
   - Duration tracking
   - History maintenance

## Implementation Discrepancies and Adjustments

During implementation, several adjustments were made from the initial plan to address practical requirements and overcome technical challenges:

### UI Design Adjustments

1. **Tab Naming**
   - Initial plan: Tab named "Scheduled Tasks"
   - Actual implementation: Tab named "Task Scheduler" to better reflect that both scheduled and ad-hoc tasks are managed

2. **Task Display Layout**
   - Initial plan: Grid-based layout for task details
   - Actual implementation: More compact list view with expandable details to improve usability with many tasks

3. **Context Controls Integration**
   - Initial plan: Simple dropdown selectors for context settings
   - Actual implementation: Context controls (reasoning, planning, deep_search) directly tied to root Alpine store to ensure consistency with other UI components

4. **Modal Dialog Architecture**
   - Initial plan: Separate modal for task editing
   - Actual implementation: Integrated editing form within the settings tab using conditional display for better UX

### Data Structure Adjustments

1. **DateTime Handling**
   - Initial plan: Basic datetime storage
   - Actual implementation: Full ISO 8601 datetime handling with proper serialization/deserialization between Python and JavaScript

   ```python
   # Backend serialization using model_dump() and ISO format
   def serialize_task(task):
       data = task.model_dump()
       # Convert all datetime fields to ISO format strings
       for field in ["created_at", "updated_at", "last_run", "next_run"]:
           if field in data and data[field] is not None:
               data[field] = data[field].isoformat()
       return data
   ```

   ```javascript
   // Frontend parsing
   function parseTaskDates(task) {
       // Convert ISO format strings back to JavaScript Date objects
       ["created_at", "updated_at", "last_run", "next_run"].forEach(field => {
           if (task[field]) {
               task[field] = new Date(task[field]);
           }
       });
       return task;
   }
   ```

2. **Schedule Format Conversion**
   - Initial plan: Simple schedule structure
   - Actual implementation: Dual representation of schedules with explicit conversion:

   ```javascript
   // Two-way conversion between string and object formats for schedule
   function scheduleToString(scheduleObj) {
       return `${scheduleObj.minute} ${scheduleObj.hour} ${scheduleObj.day} ${scheduleObj.month} ${scheduleObj.weekday}`;
   }

   function stringToSchedule(scheduleStr) {
       const parts = scheduleStr.split(' ');
       return {
           minute: parts[0] || '*',
           hour: parts[1] || '*',
           day: parts[2] || '*',
           month: parts[3] || '*',
           weekday: parts[4] || '*'
       };
   }
   ```

3. **Type Discrimination**
   - Initial plan: Simple type check
   - Actual implementation: Robust type discrimination with explicit handling:

   ```python
   def get_task_type(task):
       if isinstance(task, ScheduledTask):
           return "scheduled"
       elif isinstance(task, AdHocTask):
           return "adhoc"
       else:
           raise ValueError(f"Unknown task type: {type(task)}")
   ```

### Field Type Specifics

1. **Required Special Field Types**
   - `schedule`: Requires both object and string representation with conversion utilities
   - `ctx_planning`, `ctx_reasoning`: Must be one of "auto", "on", "off"
   - `ctx_deep_search`: Must be one of "on", "off"
   - `state`: Must be one of "idle", "running", "disabled"
   - `token`: For adhoc tasks only, must be validated as unique
   - `attachments`: Array of attachment paths requiring validation

2. **Field Validation Requirements**
   - Schedule fields must validate against cron expression patterns
   - Names must not contain special characters
   - System and user prompts must not be empty
   - Tokens must be validated for uniqueness and proper format

### API Implementation Details

1. **Error Handling Refinements**
   - Initial plan: Basic error response
   - Actual implementation: Structured error responses with specific status codes:

   ```python
   class TaskNotFoundError(Exception):
       pass

   def process(self, input: dict, request: Request) -> dict | Response:
       try:
           result = self.update_task(input)
           return result
       except TaskNotFoundError:
           return Response(status_code=404, content=json.dumps({"error": "Task not found"}))
       except ValueError as e:
           return Response(status_code=400, content=json.dumps({"error": str(e)}))
       except Exception as e:
           logging.error(f"Unexpected error updating task: {e}")
           return Response(status_code=500, content=json.dumps({"error": "Internal server error"}))
   ```

2. **Task Type-Specific Endpoints**
   - Initial plan: Generic task endpoints
   - Actual implementation: Separate endpoints for scheduled and ad-hoc tasks with type-specific validation

### Alpine.js Integration Refinements

1. **Store Structure**
   - Initial plan: Task-specific store
   - Actual implementation: Integrated within settingsModal store with clear component boundaries:

   ```javascript
   // Full integration with settingsModalProxy
   function initSettingsModal() {
       return {
           // Modal state
           isOpen: false,
           activeTab: 'general',

           // Task scheduler state
           tasks: [],
           isEditingTask: false,
           editingTask: null,

           // Methods
           openModal() {
               // Load settings and tasks
               this.isOpen = true;
           },

           // Task scheduler methods
           fetchTasks() { /* ... */ },
           addScheduledTask() { /* ... */ },
           // ... other methods
       };
   }
   ```

2. **Dynamic Component Rendering**
   - Initial plan: Static components
   - Actual implementation: Dynamic rendering based on task type:

   ```html
   <!-- Dynamic field rendering based on task type -->
   <template x-for="field in getFieldsForTaskType(editingTask.type)">
       <div class="form-field" :class="getFieldClass(field)">
           <label :for="'field-' + field.id" class="field-label" :class="{'field-required': field.required}" x-text="field.title"></label>

           <!-- Text field -->
           <template x-if="field.type === 'text'">
               <input :id="'field-' + field.id" x-model="editingTask[field.id]" class="field-input" :required="field.required" :placeholder="field.placeholder || ''">
           </template>

           <!-- Textarea field -->
           <template x-if="field.type === 'textarea'">
               <textarea :id="'field-' + field.id" x-model="editingTask[field.id]" class="field-textarea" :rows="field.rows || 3" :required="field.required" :placeholder="field.placeholder || ''"></textarea>
           </template>

           <!-- Select field -->
           <template x-if="field.type === 'select'">
               <select :id="'field-' + field.id" x-model="editingTask[field.id]" class="field-select" :required="field.required">
                   <template x-for="option in field.options">
                       <option :value="option.value" x-text="option.label"></option>
                   </template>
               </select>
           </template>

           <!-- Cron field -->
           <template x-if="field.type === 'cron'">
               <div class="cron-fields">
                   <template x-for="subfield in field.subfields">
                       <div class="cron-field">
                           <label :for="'field-' + field.id + '-' + subfield.id" class="subfield-label" x-text="subfield.title"></label>
                           <input :id="'field-' + field.id + '-' + subfield.id" x-model="editingTask[field.id][subfield.id]" class="field-input" :placeholder="subfield.placeholder || ''">
                       </div>
                   </template>
               </div>
           </template>
       </div>
   </template>
   ```

3. **Task Execution Monitoring**
   - Initial plan: Basic status display
   - Actual implementation: Live updating status with polling for running tasks:

   ```javascript
   // Task status monitoring
   async monitorRunningTasks() {
       // If we have running tasks, poll for updates
       const runningTasks = this.tasks.filter(task => task.state === 'running');
       if (runningTasks.length > 0) {
           if (!this.monitoring) {
               this.monitoring = true;
               this.monitorInterval = setInterval(async () => {
                   await this.fetchTasks();
                   // Stop monitoring if no tasks are running
                   if (!this.tasks.some(task => task.state === 'running')) {
                       clearInterval(this.monitorInterval);
                       this.monitoring = false;
                   }
               }, 5000); // Poll every 5 seconds
           }
       }
   }
   ```

## Implementation Challenges and Learnings

### Critical Alpine.js Store Dependencies

During implementation, we discovered several critical dependencies on the Alpine.js store system that must be carefully maintained:

1. **The `root` store initialization is critical**
   - The `Alpine.store('root')` initialization in the `alpine:init` event is essential for the entire UI
   - Multiple components across the application depend on `$store.root.deep_search`, `$store.root.reasoning`, and `$store.root.planning`
   - Removing this initialization breaks core UI functionality with "Cannot read properties of undefined" errors
   - This initialization MUST happen during the Alpine.js initialization phase, not conditionally or later

```javascript
document.addEventListener('alpine:init', () => {
  // This initialization is critical for the entire application
  Alpine.store('root', {
    reasoning: "auto",
    planning: "auto",
    deep_search: false
  });

  // Other store initializations
});
```

2. **Settings Modal Visibility**
   - The settings modal visibility is controlled through Alpine.js reactivity on the `isOpen` property
   - Avoid direct DOM manipulation to show/hide the modal as it conflicts with Alpine's reactivity
   - Let Alpine.js handle DOM updates based on state changes using directives like `x-show`

3. **Tab Switching Architecture**
   - The tab switching in the settings modal is controlled by the `activeTab` property
   - Proper tab switching relies on Alpine.js reactivity and class bindings
   - Conditional visibility should be handled with `x-show="activeTab === 'specific_tab'"`

### Modal System Architecture

The settings modal follows a specific architecture that must be respected:

1. **Modal Initialization Flow**
   - Alpine stores are initialized during the `alpine:init` event
   - The modal proxy is initialized during this event and stored in `Alpine.store('settingsModal')`
   - The `window.openSettings()` function calls `settingsModalProxy.openModal()`
   - The `openModal()` method fetches settings and sets `isOpen = true`

2. **Modal Reactivity**
   - The modal visibility is controlled by `x-show="isOpen"` in the HTML
   - Content within the modal is conditionally shown based on the `activeTab` property
   - Avoid direct DOM manipulation for hiding/showing elements

3. **Task Scheduler Tab Integration**
   - The Task Scheduler tab is identified as `task_scheduler` in the `activeTab` property
   - Tab content should be conditionally displayed using `x-show="activeTab === 'task_scheduler'"`
   - When switching to this tab, the `fetchSchedulerTasks()` method should be called to load task data

### Debugging Insights

During implementation debugging, we identified several key areas for robust error handling:

1. **Alpine.js Availability Checks**
   - Always check if Alpine.js is loaded before using it: `if (typeof Alpine === 'undefined')`
   - Provide user-friendly error messages when Alpine.js is not available

2. **Store Existence Checks**
   - Check if stores exist before accessing their properties: `if (!Alpine.store('root'))`
   - Re-initialize stores if they're missing, but don't duplicate initialization

3. **Error Handling for API Calls**
   - Wrap all API calls in try-catch blocks
   - Provide fallback behavior when API calls fail
   - Display meaningful error messages to users

4. **Proper JSON Data Handling**
   - Ensure all data sent to API endpoints is properly JSON serializable
   - Handle conversion between different data representations (e.g., string vs object for schedule)

### Common Pitfalls to Avoid

1. **Don't Remove Store Initialization**
   - Removing `Alpine.store('root')` initialization breaks core functionality
   - Multiple UI components depend on this store being available

2. **Avoid Direct DOM Manipulation**
   - Don't use `element.style.display = 'block'` to show/hide elements
   - Let Alpine.js handle DOM updates via reactivity

3. **Don't Initialize Stores Multiple Times**
   - Multiple store initializations can lead to unexpected behavior
   - Initialize each store exactly once during the Alpine.js init phase

4. **No Race Conditions**
   - Don't assume store values are available immediately
   - Check for existence before accessing store properties

5. **Proper State Initialization**
   - Always initialize complex objects like `editingTask` with all required nested properties
   - For scheduled tasks, ensure the `schedule` object is properly initialized
   - For ad-hoc tasks, ensure the `token` property is initialized

## Data Models

### Backend Models (Pydantic)

From the `task_scheduler.py` file, we have two main Pydantic models:

#### 1. ScheduledTask
```python
class ScheduledTask(BaseModel):
    uuid: str  # Unique identifier
    name: str  # Display name
    system_prompt: str  # System prompt for the task
    prompt: str  # User prompt for the task
    schedule: TaskSchedule  # Cron-style schedule
    ctx_planning: Literal["on", "off", "auto"] = "auto"  # Context planning mode
    ctx_reasoning: Literal["on", "off", "auto"] = "auto"  # Context reasoning mode
    ctx_deep_search: Literal["on", "off"] = "off"  # Deep search mode
    attachments: List[str] = []  # Attachments for the task
    state: Literal["idle", "running", "disabled"] = "idle"  # Current state
```

#### 2. AdHocTask
```python
class AdHocTask(BaseModel):
    uuid: str  # Unique identifier
    name: str  # Display name
    system_prompt: str  # System prompt for the task
    prompt: str  # User prompt for the task
    token: str  # Token for executing the ad-hoc task
    ctx_planning: Literal["on", "off", "auto"] = "auto"  # Context planning mode
    ctx_reasoning: Literal["on", "off", "auto"] = "auto"  # Context reasoning mode
    ctx_deep_search: Literal["on", "off"] = "off"  # Deep search mode
    attachments: List[str] = []  # Attachments for the task
    state: Literal["idle", "running", "disabled"] = "idle"  # Current state
```

#### 3. TaskSchedule
```python
class TaskSchedule(BaseModel):
    minute: str  # Cron minute field
    hour: str  # Cron hour field
    day: str  # Cron day field
    month: str  # Cron month field
    weekday: str  # Cron weekday field
```

### Frontend Models (JavaScript)

For the frontend, we'll implement corresponding JavaScript objects:

#### Field Definitions
```javascript
const taskFields = {
  common: [
    { id: "name", title: "Task Name", type: "text", required: true, width: 30 },
    { id: "system_prompt", title: "System Prompt", type: "textarea", required: true, width: 50, rows: 4 },
    { id: "prompt", title: "Prompt", type: "textarea", required: true, width: 50, rows: 4 },
    { id: "ctx_planning", title: "Context Planning", type: "select", options: [
      { value: "auto", label: "Auto" },
      { value: "on", label: "On" },
      { value: "off", label: "Off" }
    ], required: true },
    { id: "ctx_reasoning", title: "Context Reasoning", type: "select", options: [
      { value: "auto", label: "Auto" },
      { value: "on", label: "On" },
      { value: "off", label: "Off" }
    ], required: true },
    { id: "ctx_deep_search", title: "Deep Search", type: "select", options: [
      { value: "off", label: "Off" },
      { value: "on", label: "On" }
    ], required: true },
    { id: "attachments", title: "Attachments", type: "list", required: false }
  ],
  scheduled: [
    {
      id: "schedule",
      title: "Schedule",
      type: "cron",
      required: true,
      subfields: [
        { id: "minute", title: "Minute", type: "text", required: true, width: 10, placeholder: "*" },
        { id: "hour", title: "Hour", type: "text", required: true, width: 10, placeholder: "*" },
        { id: "day", title: "Day", type: "text", required: true, width: 10, placeholder: "*" },
        { id: "month", title: "Month", type: "text", required: true, width: 10, placeholder: "*" },
        { id: "weekday", title: "Weekday", type: "text", required: true, width: 10, placeholder: "*" }
      ]
    }
  ],
  adhoc: [
    { id: "token", title: "Token", type: "text", required: true, width: 30 }
  ]
};
```

#### Display Definitions
```javascript
const taskDisplayFields = {
  common: [
    { id: "name", title: "Name", format: value => value },
    { id: "state", title: "Status", format: value => {
      const statuses = {
        "idle": { label: "Ready", class: "status-ready" },
        "running": { label: "Running", class: "status-running" },
        "disabled": { label: "Disabled", class: "status-disabled" }
      };
      return {
        value: statuses[value].label,
        class: statuses[value].class
      };
    }},
    { id: "system_prompt", title: "System Prompt", format: value => value.length > 50 ? value.substring(0, 50) + "..." : value },
    { id: "prompt", title: "Prompt", format: value => value.length > 50 ? value.substring(0, 50) + "..." : value }
  ],
  scheduled: [
    {
      id: "schedule",
      title: "Schedule",
      format: value => `${value.minute} ${value.hour} ${value.day} ${value.month} ${value.weekday}`
    }
  ],
  adhoc: [
    { id: "token", title: "Token", format: value => value }
  ]
};
```

## API Endpoints

Based on the analysis of `run_ui.py` and the API handler examples, we need to implement the following API handlers:

1. `tasks_list.py` - Get all tasks
2. `task_scheduled_create.py` - Create a scheduled task
3. `task_adhoc_create.py` - Create an ad-hoc task
4. `task_update.py` - Update an existing task
5. `task_state_update.py` - Update task state (enable/disable)
6. `task_delete.py` - Delete a task
7. `task_run.py` - Run a task immediately

Each API handler class should:
- Inherit from `ApiHandler`
- Implement the `process` method
- Return either a dictionary or a `Response` object

### Example API Handler Structure
```python
from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers.task_scheduler import SchedulerTaskList

class TasksList(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        task_list = SchedulerTaskList.get()
        return {
            "tasks": [task.model_dump() for task in task_list.tasks]
        }
```

## UI Components

### 1. Task List Container
The main container for displaying all tasks with options to add new ones.

```html
<div class="tasks-container">
  <div class="tasks-header">
    <h3>Scheduled Tasks</h3>
    <div class="tasks-actions">
      <button @click="addScheduledTask" class="button">+ New Scheduled Task</button>
      <button @click="addAdHocTask" class="button">+ New AdHoc Task</button>
    </div>
  </div>

  <!-- Task List -->
  <div class="tasks-list" x-show="!isEditingTask">
    <template x-for="(task, index) in tasks" :key="task.uuid">
      <div class="task-item" :class="{'task-even': index % 2 === 0}">
        <!-- Task Display View -->
      </div>
    </template>
    <div x-show="tasks.length === 0" class="no-tasks">
      No tasks available. Create one using the buttons above.
    </div>
  </div>

  <!-- Task Editor -->
  <div class="task-editor" x-show="isEditingTask">
    <!-- Task Edit Form -->
  </div>
</div>
```

### 2. Task Editor
Form for creating or editing tasks.

```html
<form @submit.prevent="saveTask">
  <div class="form-fields">
    <!-- Common Fields -->
    <template x-for="field in getFieldsForTaskType(editingTask.type)">
      <div class="form-field" :class="`field-${field.type}`">
        <!-- Field rendering based on type -->
      </div>
    </template>
  </div>

  <div class="form-actions">
    <button type="button" @click="cancelEdit" class="button button-secondary">Cancel</button>
    <button type="submit" class="button button-primary">Save</button>
  </div>
</form>
```

### 3. Task Item Display
Display view for a saved task.

```html
<div class="task-header">
  <div class="task-name" x-text="task.name"></div>
  <div class="task-status" :class="getStatusClass(task.state)" x-text="getStatusLabel(task.state)"></div>
</div>

<div class="task-details">
  <!-- Task fields displayed in a readable format -->
</div>

<div class="task-actions">
  <button @click="editTask(task)" class="action-button">Edit</button>
  <button @click="toggleTaskState(task)" class="action-button" x-text="task.state === 'disabled' ? 'Enable' : 'Disable'"></button>
  <button @click="runTaskNow(task)" class="action-button" x-show="task.state === 'idle'">Run Now</button>
  <button @click="deleteTask(task)" class="action-button action-delete">Delete</button>
</div>
```

## Alpine.js Implementation

The Alpine.js implementation will include the following components:

### State Management
```javascript
// Add to settingsModalProxy
tasks: [],
isEditingTask: false,
editingTask: null,
editingTaskType: null, // 'scheduled' or 'adhoc'
```

### Methods
```javascript
// Add to settingsModalProxy methods
// Task CRUD operations
async fetchTasks() {
  const response = await fetch('/tasks_list');
  const data = await response.json();
  this.tasks = data.tasks || [];
},

addScheduledTask() {
  this.editingTask = {
    type: 'scheduled',
    name: '',
    system_prompt: '',
    prompt: '',
    schedule: { minute: '*', hour: '*', day: '*', month: '*', weekday: '*' },
    ctx_planning: 'auto',
    ctx_reasoning: 'auto',
    ctx_deep_search: 'off',
    attachments: []
  };
  this.isEditingTask = true;
},

addAdHocTask() {
  this.editingTask = {
    type: 'adhoc',
    name: '',
    system_prompt: '',
    prompt: '',
    token: '',
    ctx_planning: 'auto',
    ctx_reasoning: 'auto',
    ctx_deep_search: 'off',
    attachments: []
  };
  this.isEditingTask = true;
},

editTask(task) {
  this.editingTask = { ...task, type: task.schedule ? 'scheduled' : 'adhoc' };
  this.isEditingTask = true;
},

async saveTask() {
  // Validate task data
  if (!this.validateTask(this.editingTask)) {
    return; // Don't save if validation fails
  }

  let endpoint;
  let payload;

  if (this.editingTask.uuid) {
    // Update existing task
    endpoint = '/task_update';
    payload = { ...this.editingTask };
  } else if (this.editingTask.type === 'scheduled') {
    // Create new scheduled task
    endpoint = '/task_scheduled_create';
    payload = { ...this.editingTask };
    delete payload.type;
  } else {
    // Create new adhoc task
    endpoint = '/task_adhoc_create';
    payload = { ...this.editingTask };
    delete payload.type;
  }

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Failed to save task: ${await response.text()}`);
    }

    // Refresh task list
    await this.fetchTasks();

    // Reset editor state
    this.isEditingTask = false;
    this.editingTask = null;
  } catch (error) {
    console.error('Error saving task:', error);
    // Show error to user
    alert(`Error saving task: ${error.message}`);
  }
},

cancelEdit() {
  this.isEditingTask = false;
  this.editingTask = null;
},

validateTask(task) {
  // Basic validation logic - check required fields
  const fieldsToCheck = this.getFieldsForTaskType(task.type);
  for (const field of fieldsToCheck) {
    if (field.required) {
      if (field.type === 'cron') {
        // Check subfields
        for (const subfield of field.subfields) {
          if (subfield.required && !task[field.id][subfield.id]) {
            alert(`${subfield.title} is required`);
            return false;
          }
        }
      } else if (!task[field.id]) {
        alert(`${field.title} is required`);
        return false;
      }
    }
  }
  return true;
},

async toggleTaskState(task) {
  const newState = task.state === 'disabled' ? 'idle' : 'disabled';
  try {
    const response = await fetch('/task_state_update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uuid: task.uuid, state: newState })
    });

    if (!response.ok) {
      throw new Error(`Failed to update task state: ${await response.text()}`);
    }

    // Refresh task list
    await this.fetchTasks();
  } catch (error) {
    console.error('Error updating task state:', error);
    alert(`Error updating task state: ${error.message}`);
  }
},

async deleteTask(task) {
  if (!confirm(`Are you sure you want to delete task "${task.name}"?`)) {
    return;
  }

  try {
    const response = await fetch('/task_delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uuid: task.uuid })
    });

    if (!response.ok) {
      throw new Error(`Failed to delete task: ${await response.text()}`);
    }

    // Refresh task list
    await this.fetchTasks();
  } catch (error) {
    console.error('Error deleting task:', error);
    alert(`Error deleting task: ${error.message}`);
  }
},

async runTaskNow(task) {
  if (task.state !== 'idle') {
    alert('Task must be in idle state to run');
    return;
  }

  try {
    const response = await fetch('/task_run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uuid: task.uuid })
    });

    if (!response.ok) {
      throw new Error(`Failed to run task: ${await response.text()}`);
    }

    // Refresh task list
    await this.fetchTasks();
  } catch (error) {
    console.error('Error running task:', error);
    alert(`Error running task: ${error.message}`);
  }
},

// Helper methods
getFieldsForTaskType(type) {
  return [
    ...taskFields.common,
    ...(type === 'scheduled' ? taskFields.scheduled : taskFields.adhoc)
  ];
},

getDisplayFieldsForTask(task) {
  const type = task.schedule ? 'scheduled' : 'adhoc';
  return [
    ...taskDisplayFields.common,
    ...(type === 'scheduled' ? taskDisplayFields.scheduled : taskDisplayFields.adhoc)
  ];
},

getFieldValue(task, field) {
  if (field.format) {
    return field.format(task[field.id]);
  }
  return task[field.id];
},

getStatusClass(state) {
  const statuses = {
    "idle": "status-ready",
    "running": "status-running",
    "disabled": "status-disabled"
  };
  return statuses[state] || '';
},

getStatusLabel(state) {
  const labels = {
    "idle": "Ready",
    "running": "Running",
    "disabled": "Disabled"
  };
  return labels[state] || state;
}
```

### Modal Open Method Extension
```javascript
// Extend the existing openModal method to fetch tasks
async openModal() {
  // Existing code...

  // Fetch tasks when opening the modal with the Scheduled Tasks tab
  if (this.activeTab === 'scheduled_tasks') {
    await this.fetchTasks();
  }

  // Rest of existing code...
}
```

## CSS Implementation

```css
/* Task Container */
.tasks-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.tasks-actions {
  display: flex;
  gap: 0.5rem;
}

/* Task List */
.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.task-item {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 0.75rem;
  background-color: var(--card-bg-color);
}

.task-even {
  background-color: var(--card-alt-bg-color);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.task-name {
  font-weight: bold;
  font-size: 1.1rem;
}

.task-status {
  padding: 0.25rem 0.5rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-ready {
  background-color: #d1e7dd;
  color: #0f5132;
}

.status-running {
  background-color: #cfe2ff;
  color: #084298;
}

.status-disabled {
  background-color: #f8d7da;
  color: #842029;
}

.task-details {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem 1rem;
  margin-bottom: 0.75rem;
}

.task-detail {
  display: flex;
  flex-direction: column;
}

.detail-label {
  font-size: 0.875rem;
  color: var(--text-secondary-color);
  margin-bottom: 0.25rem;
}

.detail-value {
  font-size: 0.95rem;
}

.task-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.action-button {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  background-color: var(--button-bg-color);
  color: var(--button-text-color);
  border: 1px solid var(--button-border-color);
  cursor: pointer;
}

.action-button:hover {
  background-color: var(--button-hover-bg-color);
}

.action-delete {
  background-color: var(--button-danger-bg-color);
  color: var(--button-danger-text-color);
  border-color: var(--button-danger-border-color);
}

.action-delete:hover {
  background-color: var(--button-danger-hover-bg-color);
}

/* Task Editor */
.task-editor {
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 1rem;
  background-color: var(--card-bg-color);
}

.form-fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.field-textarea {
  grid-column: 1 / -1;
}

.field-cron {
  grid-column: 1 / -1;
}

.cron-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.cron-field {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 80px;
}

.field-label {
  font-size: 0.95rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.field-input,
.field-select,
.field-textarea {
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--input-bg-color);
  color: var(--text-color);
}

.field-input:focus,
.field-select:focus,
.field-textarea:focus {
  border-color: var(--primary-color);
  outline: none;
}

.field-required::after {
  content: "*";
  color: var(--error-color);
  margin-left: 0.25rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.95rem;
  cursor: pointer;
  border: 1px solid transparent;
}

.button-primary {
  background-color: var(--primary-color);
  color: var(--primary-text-color);
}

.button-primary:hover {
  background-color: var(--primary-hover-color);
}

.button-secondary {
  background-color: var(--secondary-color);
  color: var(--secondary-text-color);
  border-color: var(--secondary-border-color);
}

.button-secondary:hover {
  background-color: var(--secondary-hover-color);
}

.no-tasks {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary-color);
  font-style: italic;
}

/* Dark mode / Light mode adjustments */
:root {
  --card-bg-color: #2d333b;
  --card-alt-bg-color: #343a40;
  --border-color: #444c56;
  --text-color: #adbac7;
  --text-secondary-color: #768390;
  --primary-color: #347d39;
  --primary-hover-color: #46954a;
  --primary-text-color: #ffffff;
  --secondary-color: #2d333b;
  --secondary-hover-color: #444c56;
  --secondary-text-color: #adbac7;
  --secondary-border-color: #444c56;
  --input-bg-color: #22272e;
  --button-bg-color: #2d333b;
  --button-text-color: #adbac7;
  --button-border-color: #444c56;
  --button-hover-bg-color: #444c56;
  --button-danger-bg-color: #3d0106;
  --button-danger-text-color: #ff7b72;
  --button-danger-border-color: #5d0000;
  --button-danger-hover-bg-color: #5a1d20;
  --error-color: #f85149;
}

.light {
  --card-bg-color: #f6f8fa;
  --card-alt-bg-color: #f0f2f4;
  --border-color: #d0d7de;
  --text-color: #24292f;
  --text-secondary-color: #57606a;
  --primary-color: #2da44e;
  --primary-hover-color: #2c974b;
  --primary-text-color: #ffffff;
  --secondary-color: #f6f8fa;
  --secondary-hover-color: #eaeef2;
  --secondary-text-color: #24292f;
  --secondary-border-color: #d0d7de;
  --input-bg-color: #ffffff;
  --button-bg-color: #f6f8fa;
  --button-text-color: #24292f;
  --button-border-color: #d0d7de;
  --button-hover-bg-color: #eaeef2;
  --button-danger-bg-color: #ffebe9;
  --button-danger-text-color: #cf222e;
  --button-danger-border-color: #e5c1c1;
  --button-danger-hover-bg-color: #ffcecb;
  --error-color: #cf222e;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .form-fields {
    grid-template-columns: 1fr;
  }

  .task-details {
    grid-template-columns: 1fr;
  }

  .cron-fields {
    flex-direction: column;
  }
}
```

## Implementation Steps

1. **Backend Implementation**
   - Create API handler files in `python/api/` directory
   - Implement each handler class with the appropriate `process` method
   - Test each endpoint individually

2. **Frontend HTML Implementation**
   - Update the `webui/index.html` file to include the task UI in the "Scheduled Tasks" tab
   - Implement the task list, task editor, and task item display components

3. **Frontend JavaScript Implementation**
   - Add task-related state to the `settingsModalProxy` object
   - Implement the task management methods (CRUD operations)
   - Ensure proper integration with the existing modal functionality

4. **CSS Implementation**
   - Add the task-related CSS to `webui/css/settings.css`
   - Ensure proper styling for both light and dark modes
   - Test responsiveness for different screen sizes

5. **Testing**
   - Test task creation, editing, and deletion
   - Test task state toggling
   - Test immediate task execution
   - Verify error handling
   - Test edge cases (empty fields, invalid cron expressions)

## Integration Points

1. **Modal Integration**
   - Task UI will be displayed within the "Scheduled Tasks" tab in the settings modal
   - Need to hook into the tab switching logic to fetch tasks when the tab is selected

2. **Backend Integration**
   - API handlers will interact with the `SchedulerTaskList` and `TaskScheduler` classes
   - Ensure the task scheduler backend components are properly initialized

3. **Styling Integration**
   - New CSS should follow the existing design system
   - Support both light and dark modes
   - Maintain consistency with the rest of the UI

## Debugging & Error Handling

- Implement proper validation for task inputs
- Use try-catch blocks for API calls
- Display meaningful error messages to users
- Log errors to console for debugging
- Handle edge cases gracefully

## Future Enhancements

- Task execution history
- Better cron expression editor with visual feedback
- Task duplication functionality
- Task categories or tags
- Enhanced filtering and sorting of tasks
- Task execution status monitoring

### Data Serialization and JSON Handling

A critical part of the task scheduler implementation is proper data serialization between the frontend and backend. Several important lessons emerged during debugging:

1. **Datetime Serialization**
   - Python `datetime` objects aren't directly JSON serializable
   - The backend API handlers must convert datetime objects to ISO format strings
   - Always implement proper serialization for any datetime fields:

```python
# Example of proper datetime serialization in handlers
def process(self, input: dict, request: Request) -> dict | Response:
    # Retrieve task by UUID
    task = task_list.get_task_by_uuid(input.get("uuid"))
    if not task:
        return Response(status_code=404, content="Task not found")

    # Serialize any datetime fields to ISO format
    response_data = task.model_dump()
    if hasattr(task, "last_run") and task.last_run:
        response_data["last_run"] = task.last_run.isoformat()

    return response_data
```

2. **Type-Specific Field Handling**
   - The scheduler has two task types (scheduled and ad-hoc) with different fields
   - Type checking must be explicit before accessing type-specific fields
   - Use `isinstance()` for robust type checking, not attribute existence checks:

```python
# Robust type checking before updating type-specific fields
def update_task(task, input_data):
    # Update common fields
    task.name = input_data.get("name", task.name)

    # Type-specific field updates with proper type checking
    if isinstance(task, ScheduledTask) and "schedule" in input_data:
        # Handle schedule updates for scheduled tasks
        task.schedule = input_data["schedule"]
    elif isinstance(task, AdHocTask) and "token" in input_data:
        # Handle token updates for ad-hoc tasks
        task.token = input_data["token"]
```

3. **Schedule Object Format Handling**
   - The schedule can appear in different formats (string vs object) depending on context
   - Frontend sends a string format: `"* * * * *"`
   - Backend stores as a structured object: `{ "minute": "*", "hour": "*", "day": "*", "month": "*", "weekday": "*" }`
   - Conversion between formats must be handled explicitly:

```javascript
// Frontend: Parsing a schedule string into an object
if (task.schedule && typeof task.schedule === 'string') {
  const parts = task.schedule.split(' ');
  task.schedule = {
    minute: parts[0] || '*',
    hour: parts[1] || '*',
    day: parts[2] || '*',
    month: parts[3] || '*',
    weekday: parts[4] || '*'
  };
}

// Frontend: Converting a schedule object to a string for API submission
if (task.schedule && typeof task.schedule === 'object') {
  taskData.schedule = `${task.schedule.minute} ${task.schedule.hour} ${task.schedule.day} ${task.schedule.month} ${task.schedule.weekday}`;
}
```

### Alpine.js and Settings Modal Integration

The settings modal uses Alpine.js for reactivity and state management. Several key aspects must be understood:

1. **Modal State and Alpine Store Binding**

   The settings modal state is managed through the `settingsModalProxy` object, which is registered as an Alpine.js store:

```javascript
// Store registration during Alpine.js initialization
document.addEventListener('alpine:init', () => {
  // Root store contains application-wide state
  Alpine.store('root', {
    reasoning: "auto",
    planning: "auto",
    deep_search: false
  });

  // Settings modal store initialization
  Alpine.store('settingsModal', initSettingsModal());
});
```

2. **HTML-to-JS Binding Architecture**

   The modal HTML uses Alpine.js directives to bind to the `settingsModalProxy` state:

```html
<!-- Example of settings modal HTML structure with Alpine.js bindings -->
<div id="settingsModal" x-data="settingsModalProxy" x-show="isOpen" class="modal">
  <!-- Tabs navigation -->
  <div class="tabs">
    <div class="tab"
         x-bind:class="{ 'active': activeTab === 'general' }"
         @click="switchTab('general')">General</div>
    <div class="tab"
         x-bind:class="{ 'active': activeTab === 'task_scheduler' }"
         @click="switchTab('task_scheduler')">Task Scheduler</div>
  </div>

  <!-- Tab content -->
  <div id="settings-sections" x-show="activeTab !== 'task_scheduler'">
    <!-- General settings content -->
  </div>

  <div class="scheduler-tasks-container" x-show="activeTab === 'task_scheduler'">
    <!-- Task scheduler content -->
  </div>
</div>
```

3. **Modal Opening Process**

   The complete flow for opening the settings modal is:

   ```
   User clicks Settings button
   → @click="window.openSettings()"
   → window.openSettings() function
   → checks if Alpine.js is loaded
   → calls settingsModalProxy.openModal()
   → openModal() fetches settings
   → openModal() sets isOpen = true
   → Alpine.js reactivity shows the modal
   ```

4. **Tab Switching Process**

   The tab switching flow within the settings modal:

   ```
   User clicks a tab
   → @click="switchTab('tab_name')"
   → switchTab() updates activeTab property
   → Alpine.js reactivity updates tab highlight
   → Alpine.js reactivity shows/hides content
   → If task_scheduler tab, fetchSchedulerTasks() is called
   ```

5. **Error Prevention Checklist**

   To avoid issues with the settings modal:

   - ✅ Ensure `Alpine.store('root')` is initialized during `alpine:init`
   - ✅ Let Alpine.js handle DOM visibility via reactivity
   - ✅ Check for Alpine.js availability before using it
   - ✅ Handle async operations with proper error catching
   - ✅ Initialize all required task properties, including nested objects
   - ✅ Validate user input before submission
   - ✅ Ensure all dates are properly serialized
   - ✅ Use proper type checking before accessing type-specific properties

### Alpine.js Root Store Integration

A critical aspect of the Task Scheduler implementation is its integration with the existing Alpine.js root store. This integration is essential for maintaining consistency with the application's context controls.

1. **Root Store Dependencies**

   The task scheduler UI directly depends on the root Alpine store for context controls:

   ```javascript
   // These controls must be bound to the root store
   Alpine.store('root', {
     reasoning: "auto",     // Controls the reasoning context setting globally
     planning: "auto",      // Controls the planning context setting globally
     deep_search: false     // Controls the deep search setting globally
   });
   ```

   Task execution must reflect these settings, and the task editor must sync with them:

   ```html
   <!-- Direct binding to root store for context controls -->
   <div class="form-field">
     <label for="ctx_reasoning">Context Reasoning</label>
     <select id="ctx_reasoning" x-model="$store.root.reasoning">
       <option value="auto">Auto</option>
       <option value="on">On</option>
       <option value="off">Off</option>
     </select>
   </div>
   ```

2. **Initialization Order**

   Ensuring proper initialization order is critical:

   ```javascript
   document.addEventListener('alpine:init', () => {
     // 1. First, initialize the root store - MUST HAPPEN FIRST
     Alpine.store('root', {
       reasoning: "auto",
       planning: "auto",
       deep_search: false
     });

     // 2. Then, initialize the settingsModal store with access to root
     Alpine.store('settingsModal', initSettingsModal());

     // 3. Finally, initialize any component-specific stores
     // ...
   });
   ```

   This order ensures that the root store exists before any components try to access it, preventing "Cannot read properties of undefined" errors.

3. **Bidirectional Data Flow**

   The task scheduler implements bidirectional data flow with the root store:

   ```javascript
   // When editing a task, sync with root store
   function initializeTaskEditor(task) {
     // Start with task's values
     this.editingTask = { ...task };

     // But ensure UI reflects current root store for consistent experience
     this.editingTask.ctx_reasoning = Alpine.store('root').reasoning;
     this.editingTask.ctx_planning = Alpine.store('root').planning;
     this.editingTask.ctx_deep_search = Alpine.store('root').deep_search ? "on" : "off";
   }

   // When updating global settings, apply to active task if applicable
   function updateGlobalContext(setting, value) {
     // Update root store
     Alpine.store('root')[setting] = value;

     // Update any active task
     if (this.activeTask) {
       if (setting === 'deep_search') {
         this.activeTask.ctx_deep_search = value ? "on" : "off";
       } else {
         this.activeTask[`ctx_${setting}`] = value;
       }
     }
   }
   ```

4. **State Persistence**

   The user's preferred context settings must persist across tasks:

   ```javascript
   // When saving global settings
   async saveSettings() {
     try {
       const response = await fetch('/settings_update', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({
           reasoning: Alpine.store('root').reasoning,
           planning: Alpine.store('root').planning,
           deep_search: Alpine.store('root').deep_search
         })
       });

       if (!response.ok) throw new Error('Failed to save settings');

       // Refresh tasks to ensure their display is consistent
       if (this.tasks.length > 0) {
         await this.fetchTasks();
       }

     } catch (error) {
       console.error('Error saving settings:', error);
     }
   }
   ```

### Task Execution Environment

Tasks execute in a server-side environment that must be carefully configured:

1. **Execution Context Preparation**

   Each task needs a properly prepared execution context:

   ```python
   async def prepare_task_context(task: Union[ScheduledTask, AdHocTask]) -> dict:
       """Prepare the execution context for a task."""
       context = {
           "system_prompt": task.system_prompt,
           "prompt": task.prompt,
           "ctx_planning": task.ctx_planning,
           "ctx_reasoning": task.ctx_reasoning,
           "ctx_deep_search": task.ctx_deep_search == "on",
           "attachments": []
       }

       # Load attachment contents
       if task.attachments:
           for attachment_path in task.attachments:
               try:
                   with open(attachment_path, 'r') as f:
                       content = f.read()

                   context["attachments"].append({
                       "path": attachment_path,
                       "content": content,
                       "name": os.path.basename(attachment_path)
                   })
               except Exception as e:
                   logging.error(f"Failed to load attachment {attachment_path}: {e}")

       return context
   ```

2. **Result Handling**

   Task results must be properly captured and stored:

   ```python
   async def execute_task(task_uuid: str) -> dict:
       """Execute a task and return its results."""
       task_list = SchedulerTaskList.get()
       task = task_list.get_task_by_uuid(task_uuid)

       if not task:
           raise TaskNotFoundError(f"Task with UUID {task_uuid} not found")

       # Update task state
       task.state = "running"
       task_list.save()

       try:
           # Prepare context
           context = await prepare_task_context(task)

           # Execute task with appropriate context
           result = await execute_llm_task(
               system_prompt=context["system_prompt"],
               prompt=context["prompt"],
               planning=context["ctx_planning"],
               reasoning=context["ctx_reasoning"],
               deep_search=context["ctx_deep_search"],
               attachments=context["attachments"]
           )

           # Store execution result
           task.last_result = result
           task.last_run = datetime.now()
           task.state = "idle"

           # For scheduled tasks, calculate next run time
           if isinstance(task, ScheduledTask):
               task.next_run = calculate_next_run(task.schedule)

           task_list.save()

           return {
               "status": "success",
               "task_uuid": task_uuid,
               "result": result
           }

       except Exception as e:
           logging.error(f"Error executing task {task_uuid}: {e}")
           task.state = "idle"
           task_list.save()

           return {
               "status": "error",
               "task_uuid": task_uuid,
               "error": str(e)
           }
   ```

3. **Execution Model**

   The execution model supports both scheduled and on-demand execution:

   ```python
   class TaskScheduler:
       """Manages task scheduling and execution."""

       def __init__(self):
           self.scheduler = BackgroundScheduler()
           self.scheduler.start()
           self.reload_tasks()

       def reload_tasks(self):
           """Reload all tasks from the task list and schedule them."""
           # Clear existing jobs
           self.scheduler.remove_all_jobs()

           # Get task list
           task_list = SchedulerTaskList.get()

           # Schedule each active scheduled task
           for task in task_list.tasks:
               if isinstance(task, ScheduledTask) and task.state != "disabled":
                   self._schedule_task(task)

       def _schedule_task(self, task: ScheduledTask):
           """Schedule a task based on its cron schedule."""
           if task.state == "disabled":
               return

           self.scheduler.add_job(
               execute_task,
               'cron',
               minute=task.schedule.minute,
               hour=task.schedule.hour,
               day=task.schedule.day,
               month=task.schedule.month,
               day_of_week=task.schedule.weekday,
               id=task.uuid,
               replace_existing=True,
               args=[task.uuid]
           )

       def run_task_now(self, task_uuid: str):
           """Run a task immediately."""
           # This is run asynchronously
           asyncio.create_task(execute_task(task_uuid))
   ```

4. **External Task Triggering**

   Ad-hoc tasks require a secure external triggering mechanism:

   ```python
   class TaskRun(ApiHandler):
       async def process(self, input: dict, request: Request) -> dict | Response:
           task_uuid = input.get("uuid")
           task_token = input.get("token")

           if not task_uuid:
               return Response(status_code=400, content=json.dumps({"error": "Missing task UUID"}))

           task_list = SchedulerTaskList.get()
           task = task_list.get_task_by_uuid(task_uuid)

           if not task:
               return Response(status_code=404, content=json.dumps({"error": "Task not found"}))

           # For ad-hoc tasks, validate token if provided
           if isinstance(task, AdHocTask) and task_token:
               if task.token != task_token:
                   return Response(status_code=403, content=json.dumps({"error": "Invalid token"}))

           # Check if task is already running
           if task.state == "running":
               return Response(status_code=409, content=json.dumps({"error": "Task is already running"}))

           # Check if task is disabled
           if task.state == "disabled":
               return Response(status_code=403, content=json.dumps({"error": "Task is disabled"}))

           # Run task immediately
           scheduler = TaskScheduler.get_instance()
           scheduler.run_task_now(task_uuid)

           return {
               "status": "success",
               "message": f"Task {task_uuid} has been started"
           }
   ```

5. **Result Storage and Retrieval**

   Task results need proper storage and retrieval mechanisms:

   ```python
   class TaskResult(BaseModel):
       """Model for task execution results."""
       uuid: str
       task_uuid: str
       timestamp: datetime
       result: str
       status: Literal["success", "error"]
       error_message: Optional[str] = None

   class TaskResultsList:
       """Manages a list of task results."""

       def __init__(self):
           self.results: List[TaskResult] = []

       def add_result(self, result: TaskResult):
           """Add a new result to the list."""
           self.results.append(result)
           self.save()

       def get_results_for_task(self, task_uuid: str) -> List[TaskResult]:
           """Get all results for a specific task."""
           return [r for r in self.results if r.task_uuid == task_uuid]

       def save(self):
           """Save the results list to disk."""
           # Implementation of serialization and storage
   ```

## Key Lessons Learned

Throughout the task scheduler implementation and debugging process, several critical insights emerged that are essential for working with Alpine.js and integrating new features into the existing application architecture.

### Alpine.js Reactivity and Initialization

1. **Strict Store Initialization Order**
   - The `Alpine.store('root')` initialization is **absolutely critical** and must happen during the `alpine:init` event
   - Components across the entire application depend on the availability of this store
   - Removing or conditionally initializing this store breaks core functionality with cryptic "Cannot read properties of undefined" errors
   - Store initialization should follow a consistent pattern:
     ```javascript
     document.addEventListener('alpine:init', () => {
       // Core stores first
       Alpine.store('root', {...});
       // Feature-specific stores next
       Alpine.store('settingsModal', initSettingsModal());
       // Component-specific stores last
       // ...
     });
     ```

2. **Declarative vs. Imperative Approach**
   - Alpine.js works best with a declarative approach to UI manipulation
   - Violating this model (e.g., with direct DOM manipulation) leads to difficult-to-debug issues
   - Aligning with the framework's design philosophy leads to more stable code

3. **Defensive Alpine.js Programming**
   - Always check if Alpine is loaded before using it: `if (typeof Alpine === 'undefined')`
   - Check if stores exist before accessing their properties: `if (!Alpine.store('root'))`
   - Include appropriate error handling for Alpine initialization failures
   - Consider fallbacks when Alpine.js features aren't available or fail to initialize

### Data Serialization and Handling

1. **Type Consistency in Data Exchange**
   - Be mindful of data type transformations between frontend and backend
   - Python booleans vs. JavaScript booleans: `True/False` vs. `true/false`
   - String literals vs. Boolean values: `"on"/"off"` vs. `true/false`
   - Explicit type conversions should be documented and handled consistently

2. **Datetime Handling Across Systems**
   - Python `datetime` objects must be converted to ISO strings before JSON serialization
   - JavaScript Date objects require proper parsing from ISO strings
   - Time zone awareness is essential for scheduled tasks
   - Always maintain consistent datetime formats across all system components

3. **Schema Validation**
   - Frontend and backend should validate data against the same schema
   - Use Pydantic models to enforce schema consistency in the backend
   - Implement equivalent validation in JavaScript for the frontend
   - Document all field constraints, types, and validation rules

### UI/UX Integration

1. **Context Control Synchronization**
   - Context controls (`reasoning`, `planning`, `deep_search`) must be synchronized across the application
   - Changes in one place should be reflected globally
   - The task scheduler must respect and maintain this synchronization

2. **Task State Visibility**
   - Task state transitions must be clearly communicated to users
   - Visual indicators should reflect the current state (running, idle, disabled)
   - Status changes should be emphasized through animations or color changes

3. **Error Handling and User Feedback**
   - All API interactions should include proper error handling
   - User feedback should be immediate and clear
   - Loading states should be indicated to avoid confusion
   - Error messages should be actionable and suggest next steps

### Testing and Debugging

1. **Component Isolation Testing**
   - Test each component in isolation before integration
   - Mock dependencies during testing to focus on component functionality
   - Verify component behavior across different scenarios (empty state, error state, loaded state)

2. **Integration Testing**
   - Test interactions between components
   - Verify data flow between frontend and backend
   - Check that store updates propagate correctly
   - Ensure proper event handling and state transitions

3. **Production Safeguards**
   - Include defensive code to handle unexpected scenarios
   - Log errors comprehensively for debugging
   - Implement circuit breakers and fallbacks for critical functionality
   - Monitor task execution and alert on failures

### Final Takeaways

The most important lessons from this implementation:

1. **Understand the Framework's Mental Model**
   - Alpine.js uses a declarative, reactive approach to UI
   - Violating this model (e.g., with direct DOM manipulation) leads to difficult-to-debug issues
   - Aligning with the framework's design philosophy leads to more stable code

2. **Respect Initialization Order**
   - Core stores must be initialized first
   - Dependencies must be available before they are accessed
   - Use event listeners to ensure proper initialization sequence

3. **Test Critical Paths Thoroughly**
   - The task scheduler touches multiple system components
   - Each integration point is a potential failure point
   - Comprehensive testing prevents cascading failures

4. **Document Architecture Decisions**
   - This documentation should serve as a guide for future modifications
   - Understanding "why" a decision was made is as important as "what" was implemented
   - Knowing the pitfalls helps avoid repeating the same mistakes

## Alpine.js Component Integration Best Practices

Throughout our implementation of the task scheduler component, we've discovered several important principles for properly integrating new components in Alpine.js without creating special case handling or direct DOM manipulation.

### Core Principles of Alpine.js Integration

1. **Use Declarative Patterns Exclusively**
   - Use Alpine.js directives (x-data, x-show, x-if, etc.) to control component visibility and behavior
   - Allow Alpine's reactive system to handle DOM updates based on state changes
   - **Avoid direct DOM manipulation** entirely - no manual element creation/modification
   - Rely on Alpine's template system to render UI components

2. **Component Content Loading**
   - For dynamic content loading, use proper Alpine.js patterns:
   ```html
   <div x-data="{
      contentLoaded: false,
      contentError: null,
      async init() {
         try {
            const response = await fetch('path/to/content.html');
            if (!response.ok) throw new Error(`${response.status}: ${response.statusText}`);
            this.$el.innerHTML = await response.text();
            this.contentLoaded = true;

            // Initialize Alpine on the new content
            if (window.Alpine) window.Alpine.initTree(this.$el);
         } catch (error) {
            this.contentError = error.message;
         }
      }
   }">
      <!-- Loading state -->
      <div x-show="!contentLoaded && !contentError">Loading content...</div>

      <!-- Error state -->
      <div x-show="contentError" class="error">
         Failed to load content: <span x-text="contentError"></span>
         <button @click="init()">Retry</button>
      </div>

      <!-- Content will be loaded here -->
   </div>
   ```

3. **Shared State Management**
   - Keep component state in Alpine stores for cross-component access
   - Initialize all stores during the `alpine:init` event
   - Access store data through `$store` in templates
   - Never rely on direct element access to share state between components

4. **Conditional Rendering**
   - Use `x-show` or `x-if` for conditional visibility based on component state
   - Avoid "special case" code paths for specific components or tabs
   - Let Alpine's reactive system handle visibility automatically:
   ```html
   <div id="tab-content">
     <div x-show="activeTab === 'general'" class="tab-panel">General content...</div>
     <div x-show="activeTab === 'scheduler'" class="tab-panel">Scheduler content...</div>
     <div x-show="activeTab === 'developer'" class="tab-panel">Developer content...</div>
   </div>
   ```

5. **Component Initialization**
   - Initialize components lazily when needed through Alpine's lifecycle hooks
   - Use the `init()` method in `x-data` to set up components when they become visible
   - Fetch required data during initialization:
   ```javascript
   Alpine.data('schedulerTasks', function() {
     return {
       tasks: [],
       isLoading: true,

       // Initialize when component is rendered
       init() {
         // Load data only when this component is initialized
         this.loadTasks();
       },

       async loadTasks() {
         this.isLoading = true;
         try {
           const response = await fetch('/api/scheduler_tasks_list');
           const data = await response.json();
           this.tasks = data.tasks || [];
         } catch (error) {
           console.error('Error loading tasks:', error);
         } finally {
           this.isLoading = false;
         }
       }
     };
   });
   ```

### Anti-Patterns to Avoid

1. **Direct DOM Querying and Manipulation**
   - ❌ `document.querySelector('.scheduler-container')`
   - ❌ `document.getElementById('scheduler-tab-content')`
   - ❌ Manually creating elements with `document.createElement()`
   - ❌ Setting styles directly: `element.style.display = 'block'`

2. **Special Case Handling**
   - ❌ Checking for specific tab names in code: `if (tab === 'scheduler')`
   - ❌ Implementation-specific code paths for particular components
   - ❌ Separate initialization routines for different components
   - ❌ Using timeouts to "wait" for DOM elements to appear

3. **Framework Circumvention**
   - ❌ Using setTimeout to work around Alpine's reactivity system
   - ❌ Manually initializing Alpine on specific elements
   - ❌ Creating parallel state management outside Alpine stores
   - ❌ Bypassing Alpine's reactivity system with direct DOM changes

### Correct Approach for Tab Content

For tab-based content like the settings modal:

1. **Unified Tab Structure**
   All tabs should follow the same pattern:
   ```html
   <div class="tab-content">
     <!-- Each tab panel follows identical pattern -->
     <div x-show="activeTab === 'general'" class="tab-panel">General content...</div>

     <div x-show="activeTab === 'scheduler'" class="tab-panel">Scheduler content...</div>

     <!-- Other tab panels... -->
   </div>
   ```

2. **Consistent Tab Switching Logic**
   The tab switching should be generic and not contain special cases:
   ```javascript
   // Generic tab switching without special cases
   switchTab(tab) {
     // Update active tab
     this.activeTab = tab;

     // Store preference
     localStorage.setItem('ACTIVE_TAB', tab);

     // No special handling for specific tabs
   }
   ```

3. **Dynamic Content Loading Pattern**
   For tabs that need to load content dynamically:
   ```html
   <div x-show="activeTab === 'scheduler'" class="tab-panel">
     <div x-data="{
        contentLoaded: false,
        async init() {
           if (!this.contentLoaded) {
              try {
                 const response = await fetch('settings/scheduler.html');
                 if (response.ok) {
                    this.$el.innerHTML = await response.text();
                    this.contentLoaded = true;
                    // Initialize Alpine on the new content
                    if (window.Alpine) window.Alpine.initTree(this.$el);
                 }
              } catch (error) {
                 console.error('Error loading scheduler content:', error);
              }
           }
        }
     }" x-init="init()">
     </div>
   </div>
   ```

By following these best practices, all components (including the scheduler) can be implemented in a clean, maintainable way without special cases or hacks. The Alpine.js framework provides all the necessary tools to create dynamic, reactive components without resorting to direct DOM manipulation or special handling code paths.

## Implementation Updates

After a thorough review of the task scheduler implementation, we've made significant improvements to eliminate special case handling and ensure clean integration with Alpine.js. These changes have resulted in a more maintainable and robust implementation that better aligns with framework best practices.

### Key Changes Implemented

1. **Removed All Direct DOM Manipulation**
   - Eliminated all instances of `document.querySelector` and `document.getElementById` that were being used to find scheduler containers
   - Removed manual Alpine initialization through direct element references
   - Replaced with proper Alpine.js declarative initialization

2. **Eliminated Special Case Handling**
   - Removed all conditional checks for `activeTab === 'scheduler'` in tab switching logic
   - Eliminated setTimeout calls used to handle scheduler initialization
   - Removed redundant initialization functions and special container-finding code
   - Made all tabs follow the same pattern without component-specific code paths

3. **Unified Component Initialization**
   - Updated scheduler component to use `x-init="init()"` to properly self-initialize
   - Removed the custom `schedulerContentLoaded` state property
   - Simplified the empty shell of `initSchedulerTasks()` function to maintain backward compatibility

4. **Refactored HTML Structure**
   - Removed the hardcoded `id="scheduler-tab-content"` attribute
   - Updated scheduler tab content to follow the same pattern as other tabs
   - Properly structured the component with consistent Alpine.js patterns

### Before and After Comparison

#### Before:
```javascript
// Special case handling in switchTab method
switchTab(tab) {
  this.activeTab = tab;
  localStorage.setItem('A0_SETTINGS_ACTIVE_TAB', tab);

  // Special case for scheduler tab
  if (tab === 'scheduler' && typeof window.initSchedulerTasks === 'function') {
    setTimeout(() => {
      console.log('Explicitly initializing scheduler component');
      window.initSchedulerTasks();
    }, 50);
  }
}

// Complex DOM manipulation in initSchedulerTasks
window.initSchedulerTasks = function() {
  try {
    const containers = [
      document.getElementById('scheduler-tab-content'),
      document.querySelector('[x-data="schedulerTasks"]'),
      document.querySelector('.scheduler-container')
    ].filter(el => el);

    if (containers.length === 0) {
      console.error('No container found');
      return false;
    }

    containers.forEach((container, index) => {
      window.Alpine.initTree(container);
    });

    return true;
  } catch (error) {
    console.error('Error initializing scheduler component:', error);
    return false;
  }
}
```

#### After:
```javascript
// Clean tab switching without special cases
switchTab(tab) {
  // For backward compatibility - normalize tab name
  if (tab === 'task_scheduler') {
    tab = 'scheduler';
  }

  this.activeTab = tab;
  this.initializeFilteredSections();
  localStorage.setItem('A0_SETTINGS_ACTIVE_TAB', tab);
}

// Simplified initialization function (only for backward compatibility)
window.initSchedulerTasks = function() {
  console.log('initSchedulerTasks called - component should self-initialize through Alpine.js');
  // This function is kept for backward compatibility
  // Modern approach uses Alpine's x-init directive for component initialization
};

// Clean HTML structure
<div x-show="activeTab === 'scheduler'" x-cloak>
  <div x-data="schedulerTasks" x-init="init()" class="scheduler-container">
    <!-- Component content -->
  </div>
</div>
```

### Benefits of the New Implementation

1. **Improved Reliability**: By letting Alpine.js handle component initialization through its built-in mechanisms, we've eliminated timing issues and race conditions that were causing the scheduler tab to sometimes not appear.

2. **Enhanced Maintainability**: Without special cases and direct DOM manipulation, the code is more consistent and follows standard patterns, making it easier to maintain and understand.

3. **Better Framework Alignment**: The implementation now properly leverages Alpine.js's reactivity and initialization system, working with the framework rather than working around it.

4. **Reduced Code Complexity**: By eliminating special handling, we've reduced the overall complexity of the codebase, leading to fewer potential bugs and easier debugging.

5. **Consistent User Experience**: All tabs now behave the same way structurally, providing a more predictable and stable user experience.

These changes demonstrate how following framework best practices and avoiding special case handling leads to more robust and maintainable code. The task scheduler component now integrates seamlessly with the rest of the application, without requiring special treatment.

## UI Structure Implementation Details

### Critical Section-Content Structure Relationship

When implementing the task scheduler UI within the settings modal, it's essential to maintain the proper structural relationship between the section container and its content:

1. **Proper Section Nesting**
   - The task scheduler content MUST be nested within the settings section element
   - Use `<div class="settings-section" data-section-id="task_scheduler">` as the container
   - Include the section title as a direct child: `<h3 class="settings-section-title">Task Scheduler</h3>`

2. **Content Container Positioning**
   - The task scheduler container should be a child of the section:
   ```html
   <div class="settings-section" data-section-id="task_scheduler">
     <h3 class="settings-section-title">Task Scheduler</h3>
     <div class="task-scheduler-container">
       <!-- Content here -->
     </div>
   </div>
   ```

3. **CSS Display Control**
   - Use proper flex layout in CSS to ensure content flows correctly within the section:
   ```css
   .settings-section[data-section-id="task_scheduler"] {
     display: flex;
     flex-direction: column;
   }

   .settings-section[data-section-id="task_scheduler"] .task-scheduler-container {
     flex: 1;
     width: 100%;
     margin-top: 1rem;
   }
   ```

4. **Alpine.js Binding Structure**
   - Bind the `x-data="taskScheduler"` directive to the content container, not the section
   - The section's visibility should be controlled by `x-show="activeTab === 'task_scheduler'"`
   - The content container should have its own visibility based on task-specific states

### Placeholder Content Handling

To properly handle placeholder content in the task scheduler:

1. **Backend Implementation Requirements**
   - In `python/helpers/settings.py`, ensure the task scheduler fields array is empty:
   ```python
   task_scheduler_fields: list[SettingsField] = []
   task_scheduler_section: SettingsSection = {
       "id": "task_scheduler",
       "title": "Task Scheduler",
       "description": "",  # Empty description - frontend will handle the content
       "fields": task_scheduler_fields,
       "tab": "task_scheduler",
   }
   ```

2. **Frontend Placeholder Removal**
   - In `settings.js`, ensure proper placeholder filtering for "Coming Soon" text:
   ```javascript
   const taskSchedulerSection = this.settings.sections.find(s => s.id === 'task_scheduler');
   if (taskSchedulerSection) {
       // Set description to empty
       if (taskSchedulerSection.description && taskSchedulerSection.description.length > 0) {
           taskSchedulerSection.description = '';
       }

       // Remove all placeholder fields
       if (taskSchedulerSection.fields && taskSchedulerSection.fields.length > 0) {
           taskSchedulerSection.fields = taskSchedulerSection.fields.filter(field => {
               const isPlaceholder = field.description?.includes('Coming Soon') ||
                                   field.description?.includes('Feature in development') ||
                                   field.title?.includes('Coming Soon') ||
                                   field.title?.includes('Feature in development');
               return !isPlaceholder;
           });
       }
   }
   ```

These implementation details ensure the task scheduler UI is properly structured within the settings modal and that no placeholder content appears in the UI.
