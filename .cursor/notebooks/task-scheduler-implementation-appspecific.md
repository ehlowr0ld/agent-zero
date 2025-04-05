# Task Scheduler Application-Specific Implementation Details

## ⚠️ CRITICAL: NAMING CONVENTION AND CONTAINERIZED ENVIRONMENT AWARENESS ⚠️

## ⚠️ CRITICAL: NAMING CONVENTION AND CASE STYLE RULES ⚠️

### Naming Convention Requirements

1. **Mandatory Prefix Usage**:
   - ALL components MUST use the `scheduler-` prefix (with appropriate case style)
   - This includes CSS classes, JavaScript components, Python classes, and API endpoints
   - This distinguishes scheduler functionality from other task-related features

2. **Case Style by File Type**:
   - **JavaScript**: camelCase prefix
     ```javascript
     // Components
     schedulerTaskManager
     schedulerTaskForm

     // Methods
     loadSchedulerTasks()
     saveSchedulerTask()
     ```

   - **CSS**: kebab-case prefix
     ```css
     /* Always use scheduler- prefix with dashes */
     .scheduler-task-list
     .scheduler-task-item
     .scheduler-status-badge
     .scheduler-list-container
     ```

   - **Python**: snake_case prefix for endpoints, PascalCase for classes
     ```python
     # API Endpoints
     /scheduler_tasks_list
     /scheduler_task_update

     # Classes
     class SchedulerTaskManager:
     class SchedulerStatusBadge:
     ```

   - **HTML**: Use CSS kebab-case convention
     ```html
     <div class="scheduler-task-list">
     <div class="scheduler-status-badge">
     ```

3. **Strict Separation**:
   - Never mix scheduler task components with other task-related features
   - Maintain clear distinction in naming and functionality
   - Avoid generic terms like "task" without the "scheduler-" prefix

4. **LocalStorage Key Naming**:
   - MUST use camelCase for all keys
   - Examples:
     ```javascript
     // Correct
     settingsActiveTab
     leftPanelActiveTab
     lastSelectedSchedulerTask
     schedulerTaskFilter
     schedulerTaskSort

     // Incorrect - DO NOT USE
     settings-active-tab
     left-panel-active-tab
     scheduler-task-filter
     ```

5. **CSS Class Naming**:
   - Use kebab-case with component prefix
   - Example: `scheduler-task-list`, `scheduler-status-badge`

6. **JavaScript Identifiers**:
   - Use camelCase consistently
   - Example: `schedulerTaskManager`, `loadSchedulerTasks`

7. **Store Property Naming**:
   - Use camelCase for all properties
   - Example: `selectedTab`, `isLoading`

### Component Integration

1. **Alpine.js Component Registration**:
   ```javascript
   Alpine.data('schedulerTaskManager', () => ({
       tasks: [],
       selected: '',
       isLoading: true,
       // ... other properties

       async loadSchedulerTasks() {
           // Implementation
       },

       async saveSchedulerTask() {
           // Implementation
       }
   }));
   ```

2. **HTML Structure**:
   ```html
   <div x-data="schedulerTaskManager" class="scheduler-container">
       <div class="scheduler-task-list">
           <div class="scheduler-task-item" x-for="task in tasks">
               <!-- Task content -->
           </div>
       </div>
   </div>
   ```

3. **API Integration**:
   ```javascript
   // API endpoints
   const ENDPOINTS = {
       LIST: '/scheduler_tasks_list',
       CREATE: '/scheduler_task_create',
       UPDATE: '/scheduler_task_update',
       DELETE: '/scheduler_task_delete',
       RUN: '/scheduler_task_run'
   };
   ```

### Critical Implementation Notes

1. **Component Isolation**:
   - Scheduler components MUST be self-contained
   - No sharing of state with other task systems
   - Use dedicated stores and methods

2. **State Management**:
   - Use `schedulerTaskManager` for all scheduler-related state
   - Maintain separate storage keys for scheduler tasks
   - Clear distinction in localStorage keys:
     ```javascript
     localStorage.setItem('lastSelectedSchedulerTask', uuid);
     localStorage.setItem('activeTab', 'scheduler-tasks');
     ```

3. **Error Handling**:
   - Clear error messages specific to scheduler tasks
   - Proper error state management
   - Consistent error display in UI

4. **Validation System**:
   - Dedicated validation methods for scheduler tasks
   - Clear validation error messages
   - Real-time validation with proper feedback

### UI/UX Guidelines

1. **Status Badges**:
   ```css
   .scheduler-status-badge {
       /* Common badge styles */
   }
   .scheduler-status-idle { /* Idle state styles */ }
   .scheduler-status-running { /* Running state styles */ }
   .scheduler-status-disabled { /* Disabled state styles */ }
   .scheduler-status-error { /* Error state styles */ }
   ```

2. **Task List Display**:
   ```css
   .scheduler-task-list {
       display: flex;
       flex-direction: column;
       gap: 8px;
   }

   .scheduler-task-item {
       /* Task item styles */
   }
   ```

3. **Form Elements**:
   ```css
   .scheduler-form-group {
       /* Form group styles */
   }

   .scheduler-form-input {
       /* Input styles */
   }
   ```

### Common Pitfalls to Avoid

1. **❌ DO NOT use generic task names**:
   ```javascript
   // INCORRECT
   loadTasks()
   saveTask()

   // CORRECT
   loadSchedulerTasks()
   saveSchedulerTask()
   ```

2. **❌ DO NOT mix with other task systems**:
   ```javascript
   // INCORRECT
   if (task.type === 'scheduler' || task.type === 'agent') {
       // Don't mix different task systems
   }

   // CORRECT
   // Keep scheduler tasks completely separate
   ```

3. **❌ DO NOT share state or storage**:
   ```javascript
   // INCORRECT
   localStorage.setItem('lastSelectedTask', uuid);

   // CORRECT
   localStorage.setItem('lastSelectedSchedulerTask', uuid);
   ```

4. **❌ DO NOT use kebab-case for localStorage keys**:
   ```javascript
   // INCORRECT
   localStorage.getItem('settings-active-tab')

   // CORRECT
   localStorage.getItem('settingsActiveTab')
   ```

5. **❌ DO NOT skip store existence checks**:
   ```javascript
   // INCORRECT
   Alpine.store('root').selectedTab

   // CORRECT
   if (window.Alpine && Alpine.store('root')) {
       Alpine.store('root').selectedTab
   }
   ```

6. **❌ DO NOT mix naming patterns**:
   ```javascript
   // INCORRECT - mixing patterns
   const settings_active_tab = localStorage.getItem('settingsActiveTab')

   // CORRECT - consistent camelCase
   const settingsActiveTab = localStorage.getItem('settingsActiveTab')
   ```

### Testing Requirements

1. **Component Testing**:
   - Test scheduler-specific functionality in isolation
   - Verify proper prefix usage in all components
   - Check for naming consistency

2. **Integration Testing**:
   - Verify no interference with other task systems
   - Test proper state isolation
   - Validate storage key separation

3. **UI Testing**:
   - Verify consistent styling with scheduler- prefix
   - Check proper class application
   - Validate status badge displays

4. **Naming Convention Tests**:
   - Verify localStorage key naming
   - Check JavaScript identifier patterns
   - Validate CSS class naming
   - Test store property naming

5. **Store Integration Tests**:
   - Test store initialization
   - Verify safety checks
   - Validate property access
   - Check error handling

6. **State Management Tests**:
   - Test state persistence
   - Verify naming consistency
   - Check data recovery
   - Validate error states

### Future Considerations

1. **Component Extensions**:
   - Maintain prefix convention for new features
   - Document prefix requirement in component docs
   - Update validation for new fields

2. **API Evolution**:
   - Keep endpoint naming consistent
   - Document API changes with prefix requirement
   - Maintain backwards compatibility

3. **UI Enhancements**:
   - Follow prefix convention for new styles
   - Maintain consistent visual language
   - Document styling requirements

4. **Automated Validation**:
   - Add naming convention linting
   - Implement store access validation
   - Add property naming checks
   - Create safety check validation

5. **Enhanced Documentation**:
   - Keep naming patterns updated
   - Document new conventions
   - Maintain implementation history
   - Track pattern evolution

6. **Testing Improvements**:
   - Add comprehensive test suite
   - Implement naming validation
   - Add store access tests
   - Create safety check tests

Remember: This is a containerized environment. All changes must consider container lifecycle and persistence requirements.

## ⚠️ CRITICAL: CONTAINERIZED ENVIRONMENT AWARENESS ⚠️

This application runs in a **CONTAINERIZED ENVIRONMENT**. This fact MUST be remembered throughout development to prevent data loss and unexpected behavior.

### Fundamental Environment Facts to Remember

1. **Container Context Preservation**:
   - The application runs within a Docker container
   - File changes are NOT persistent unless in mounted volumes
   - Container restarts will RESET all non-persistent changes
   - All debugging sessions MUST consider container lifecycle

2. **Development Memory Aids**:
   - Use the `.context.md` file in the project root to maintain critical facts
   - Review this file at the start of EVERY development session
   - Create a `.warning-flags` file that explicitly tracks must-remember facts
   - Document container-specific properties to prevent regression errors

3. **UI Change Safeguards**:
   - Before making ANY UI changes, explicitly verify:
     - The file persistence behavior in the containerized environment
     - The component structure pattern used by other parts of the app
     - The CSS naming conventions across the application
   - Document the rationale for changes to prevent future confusion

4. **Memory Failure Prevention Protocol**:
   - Always maintain context about previous actions in a development session
   - Keep a running log of changes made and the reasoning behind them
   - Explicitly note when changes affect container-mounted vs ephemeral paths
   - Create explicit reminders about important architectural decisions

**IF YOU FORGET THAT THIS IS A CONTAINERIZED APPLICATION, YOU WILL CAUSE CRITICAL FAILURES.**

## Integration with Settings Modal
The task scheduler is integrated into the existing settings modal dialog in the A0 platform. The settings modal is implemented using Alpine.js and has the following integration points:

1. **Tab Structure**:
   - The scheduler is implemented as a tab within the settings modal
   - The tab ID is 'task_scheduler' for internal references
   - The tab appears alongside other settings tabs like 'general', 'agent', etc.

### CRITICAL: Task Scheduler Tab HTML Structure

When implementing the Task Scheduler tab, you MUST follow these guidelines to ensure consistency across the application:

1. **Standard Section Structure**:
   - The task scheduler MUST use the standard `.section` class for its container, NOT a special-case class like `.settings-section`
   - The section MUST include a `.section-title` and `.section-description` following the same pattern as other tabs
   - Example of correct implementation:
   ```html
   <div x-show="activeTab === 'task_scheduler'">
     <div id="section-task-scheduler" class="section">
       <div class="section-title">Task Scheduler</div>
       <div class="section-description">Manage scheduled tasks and automated processes.</div>
       <!-- Content here -->
     </div>
   </div>
   ```

2. **Namespace CSS Classes**:
   - All task scheduler-specific CSS classes MUST use the `scheduler-` prefix (e.g., `scheduler-task-list`, `scheduler-form-group`)
   - This prevents naming conflicts with other components while maintaining clear ownership
   - Example:
   ```html
   <div class="scheduler-task-controls">
     <div class="scheduler-left-controls">
       <!-- Controls here -->
     </div>
   </div>
   ```

3. **NO Special-Case Styling**:
   - The task scheduler tab MUST NOT use any special styling that deviates from the standard tab pattern
   - The red border and other section styling will be applied automatically when using the standard `.section` class
   - DO NOT create custom CSS rules specifically for the task scheduler container that override or duplicate the standard section styles

4. **Component Pattern Consistency**:
   - The task scheduler MUST follow the same DOM structure patterns as other tabs
   - If other tabs use a specific nesting pattern, the task scheduler must use the same pattern
   - Any deviation will result in inconsistent styling and behavior

### CRITICAL: Styling Preservation Warning

1. **DO NOT Modify Core UI Styles**:
   - NEVER change the appearance of the `.section` element (it should have ONLY a red border, no added background)
   - NEVER modify button styles for the modal dialog (`btn-cancel`, `btn-save`, etc.)
   - NEVER add custom background colors, borders, or other visual treatments that aren't consistent with other tabs

2. **Visual Consistency Requirements**:
   - Task scheduler elements MUST match the visual styling of equivalent elements in other tabs
   - Any visual enhancements must be approved by the UX team before implementation
   - If existing styles seem inadequate, consult with UX team rather than making independent changes

3. **Changes Requiring Explicit Approval**:
   - Global button style modifications
   - Section background or border changes
   - Modal dialog structure or appearance modifications
   - Any styling that affects elements outside the scheduler component itself

Following these guidelines ensures that the task scheduler seamlessly integrates with the application's design system and minimizes maintenance overhead. This approach makes the codebase more maintainable and prevents future regressions.

2. **Alpine.js Component Integration**:
   ```javascript
   // Registration with Alpine.js
   document.addEventListener('alpine:init', () => {
     // Register taskScheduler component
     Alpine.data('taskScheduler', function() {
       return {
         // State management
         tasks: [],
         isLoading: true,
         showNewTaskForm: false,
         editingTask: null,
         validationErrors: {},
         isValidating: false,

         // Validation methods
         async validateTask(task) {
           this.isValidating = true;
           this.validationErrors = {};

           try {
             const response = await fetch('/scheduler_validate_task', {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify(task)
             });

             const result = await response.json();

             if (!result.valid) {
               this.validationErrors = result.errors;
               return false;
             }

             return true;
           } catch (error) {
             console.error('Validation error:', error);
             window.toast?.('Validation failed', 'error');
             return false;
           } finally {
             this.isValidating = false;
           }
         },

         // Field validation
         async validateField(field, value) {
           const taskData = this.editingTask ?
             { ...this.editingTask, [field]: value } :
             { ...this.newTask, [field]: value };

           await this.validateTask(taskData);
         },

         // Error display
         getFieldError(field) {
           return this.validationErrors[field] || '';
         },

         hasError(field) {
           return field in this.validationErrors;
         },

         // Form submission
         async handleSubmit() {
           if (await this.validateTask(this.editingTask || this.newTask)) {
             await this.saveTask();
           }
         }
       };
     });
   });
   ```

3. **Settings Modal Initialization**:
   The settings modal is initialized when the user clicks the settings button. The task scheduler tab becomes visible when selected by the user.

4. **CRITICAL: Backend Placeholder Removal**:
   The backend sends placeholder content for features in development. These must be removed in `python/helpers/settings.py`:
   ```python
   # Task Scheduler section - REMOVE ALL PLACEHOLDER CONTENT
   task_scheduler_fields: list[SettingsField] = []
   # NO placeholder fields should be added - frontend will handle implementation

   task_scheduler_section: SettingsSection = {
       "id": "task_scheduler",
       "title": "Task Scheduler",
       "description": "",  # Empty description - frontend handles the content
       "fields": task_scheduler_fields,
       "tab": "task_scheduler",
   }
   ```

5. **CRITICAL: Direct Integration in Settings Modal**:
   The task form MUST be integrated directly within the settings tab content, NOT teleported to a separate modal:
   ```html
   <!-- Task Form (New/Edit) directly in the tab, not teleported -->
   <div x-show="showNewTaskForm" class="task-form" style="width: 100%; max-width: 100%; margin-top: 20px;">
       <!-- Form content here -->
   </div>
   ```

## Task Form Implementation

1. **Form Structure**:
   - The form should appear within the tab content area when `showNewTaskForm` is true
   - The task list should be hidden when the form is visible
   - The form should include all required fields for task creation and editing

2. **CSS Requirements**:
   ```css
   /* Task form styling for in-tab display */
   .task-form {
     background-color: var(--color-bg-tertiary);
     border-radius: 4px;
     padding: 1.5rem;
     border: 1px solid var(--color-border);
     overflow-y: auto;
   }

   /* Do NOT include modal overlay styles - the form is not a modal */
   ```

3. **Form Visibility Control**:
   ```javascript
   // Toggle between form and list view
   showNewTaskForm = true; // Shows form, hides list
   showNewTaskForm = false; // Shows list, hides form

   // Use conditional rendering with x-show
   <div x-show="!showNewTaskForm">
     <!-- Task list content -->
   </div>
   <div x-show="showNewTaskForm">
     <!-- Task form content -->
   </div>
   ```

## Schedule Format Implementation

The system supports both direct cron syntax and predefined schedule options:

1. **Cron Format**:
   The backend uses the `TaskSchedule` model with cron fields:
   ```python
   class TaskSchedule(BaseModel):
       minute: str
       hour: str
       day: str
       month: str
       weekday: str

       def to_crontab(self) -> str:
           return f"{self.minute} {self.hour} {self.day} {self.month} {self.weekday}"
   ```

2. **Schedule Editor UI**:
   The UI component for schedule editing includes both predefined options and direct cron input:
   ```html
   <div class="task-form-row" x-show="(editingTask && editingTask.type === 'scheduled') || (!editingTask && newTask.type === 'scheduled')">
     <div class="task-form-field full">
       <label class="task-form-label">Schedule (Cron Format)</label>

       <div class="task-schedule-inputs">
         <input type="text" x-model="editingTask ? editingTask.minute : newTask.minute"
                placeholder="*" title="Minute (0-59)">
         <span>:</span>
         <input type="text" x-model="editingTask ? editingTask.hour : newTask.hour"
                placeholder="*" title="Hour (0-23)">
         <span>:</span>
         <input type="text" x-model="editingTask ? editingTask.day : newTask.day"
                placeholder="*" title="Day of Month (1-31)">
         <span>:</span>
         <input type="text" x-model="editingTask ? editingTask.month : newTask.month"
                placeholder="*" title="Month (1-12)">
         <span>:</span>
         <input type="text" x-model="editingTask ? editingTask.weekday : newTask.weekday"
                placeholder="*" title="Day of Week (0-6, 0=Sunday)">
       </div>

       <div class="cron-description" x-show="getCronDescription(editingTask || newTask) !== ''">
         <small x-text="getCronDescription(editingTask || newTask)"></small>
       </div>
     </div>
   </div>
   ```

3. **Schedule Format Helper Functions**:
   ```javascript
   // Convert between formats and provide human-readable descriptions
   function getCronDescription(task) {
     if (!task) return '';
     if (task.type !== 'scheduled') return '';

     const minute = task.minute || '*';
     const hour = task.hour || '*';
     const day = task.day || '*';
     const month = task.month || '*';
     const weekday = task.weekday || '*';

     // Complex logic to generate human-readable description
     // ...

     return description;
   }
   ```

## File Attachment Implementation

1. **CRITICAL: Container Path Handling**:
   File attachments MUST use absolute paths within the container:
   ```html
   <div class="task-form-row full">
     <div class="task-form-field">
       <label class="task-form-label">Attachments (Container Paths)</label>
       <textarea x-model="editingTask ? editingTask.attachments.join('\n') : newTask.attachments.join('\n')"
                rows="3" placeholder="/path/to/file1.txt&#10;/path/to/file2.pdf"></textarea>
       <small class="form-text">Enter absolute paths to files within the container. One file path per line.</small>
     </div>
   </div>
   ```

2. **Attachment Processing**:
   ```javascript
   // Process attachments from textarea input
   function prepareTaskForSave(task) {
     const taskData = { ...task };

     // Handle attachments from textarea
     if (typeof taskData.attachments === 'string') {
       taskData.attachments = taskData.attachments
         .split(/[\n,]/) // Split by newlines or commas
         .map(path => path.trim())
         .filter(path => path !== '');
     }

     return taskData;
   }
   ```

3. **IMPORTANT: Array Initialization**:
   Always ensure attachments are initialized as an array:
   ```javascript
   // Reset to an empty new task object
   resetNewTask() {
     this.newTask = {
       name: '',
       type: 'scheduled',
       state: 'idle',
       minute: '*',
       hour: '*',
       day: '*',
       month: '*',
       weekday: '*',
       system_prompt: '',
       prompt: '',
       attachments: [], // Must be an array
     };
   },

   // Edit an existing task
   editTask(task) {
     // Clone the task to avoid directly modifying tasks array
     this.editingTask = JSON.parse(JSON.stringify(task));

     // CRITICAL: Ensure attachments is always an array
     if (!Array.isArray(this.editingTask.attachments)) {
       if (this.editingTask.attachments) {
         // Convert string to array if needed
         if (typeof this.editingTask.attachments === 'string') {
           this.editingTask.attachments = this.editingTask.attachments
             .split(',')
             .map(path => path.trim())
             .filter(path => path !== '');
         } else {
           this.editingTask.attachments = [];
         }
       } else {
         this.editingTask.attachments = [];
       }
     }

     this.showNewTaskForm = true;
   }
   ```

4. **Backend Attachment Validation**:
   ```python
   def validate_attachments(attachments: list[str]) -> tuple[bool, str]:
       """Validate that all attachments exist and are accessible."""
       for path in attachments:
           if not os.path.exists(path):
               return False, f"Attachment not found: {path}"
           if not os.access(path, os.R_OK):
               return False, f"Attachment not readable: {path}"
       return True, ""
   ```

## Tab Visibility and Task Loading

To ensure tasks load when the tab becomes visible:

   ```html
<div x-show="activeTab === 'task_scheduler'"
     x-data="taskScheduler"
     x-init="$watch('$el.offsetParent', (value) => {
         if(value !== null) {
             console.log('Task scheduler tab became visible, loading tasks...');
             forceLoadTasks();
         }
     })"
     class="task-scheduler-container">
  <!-- Content -->
   </div>
   ```

## Common Pitfalls to Avoid

1. **Don't Use Teleport for Task Form**
   - ❌ `<template x-teleport="body">`
   - ✅ Directly include form in the tab content

2. **Don't Use Placeholder Content from Backend**
   - ❌ "Coming Soon" or "Feature in development" text
   - ✅ Empty backend settings fields, frontend handles implementation

3. **Don't Treat Attachments as Strings**
   - ❌ `attachments: "file1.txt,file2.txt"`
   - ✅ `attachments: ["/path/to/file1.txt", "/path/to/file2.txt"]`

4. **Don't Use Relative Paths in Containerized Environment**
   - ❌ `attachments: ["file1.txt", "file2.txt"]`
   - ✅ `attachments: ["/path/to/file1.txt", "/path/to/file2.txt"]`

5. **Don't Initialize Tasks with Missing Properties**
   - ❌ `newTask = { name: '', type: 'scheduled' }`
   - ✅ Initialize with all required properties, including empty attachments array

6. **Don't Style Form as Modal Overlay**
   - ❌ Using position: fixed, z-index, backdrop etc.
   - ✅ Style as regular form within the tab content

## Critical UI Structural Requirements

To ensure the task scheduler UI displays correctly within the settings modal, the HTML structure must follow a specific pattern to maintain proper content positioning:

### Correct HTML Structure Pattern

```html
<!-- Tab definition with settings-section wrapper -->
<div x-show="activeTab === 'task_scheduler'" class="settings-section" data-section-id="task_scheduler">
    <!-- Section title must be direct child of the section -->
    <h3 class="settings-section-title">Task Scheduler</h3>

    <!-- Task scheduler container with Alpine.js binding -->
    <div x-data="taskScheduler"
         x-init="$watch('$el.offsetParent', (value) => {
             if(value !== null) {
                 forceLoadTasks();
             }
         })"
         class="task-scheduler-container">

        <!-- Task scheduler content here -->
    </div>
</div>
```

### Essential CSS Implementation

   ```css
/* Make sure the task scheduler content is properly positioned inside the section */
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

### Structure Implementation Checklist

1. **✅ Use proper section container**: Always wrap task scheduler content in a `settings-section` div with the correct data attribute
2. **✅ Include section title as direct child**: The `h3` title must be a direct child of the section container
3. **✅ Apply Alpine.js bindings to content container only**: The `x-data="taskScheduler"` binding should be on the content container, not the section itself
4. **✅ Use proper CSS flex layout**: Ensure the section uses `display: flex` and `flex-direction: column`
5. **✅ Position content container correctly**: The task container should have `flex: 1` and `width: 100%`

### Structural Anti-Patterns to Avoid

1. **❌ DO NOT bind x-data to the section element**: This creates scoping issues with Alpine.js
   ```html
   <!-- INCORRECT -->
   <div x-show="activeTab === 'task_scheduler'" x-data="taskScheduler" class="settings-section">
   ```

2. **❌ DO NOT put content directly in section without container**: Always use a dedicated container
   ```html
   <!-- INCORRECT -->
   <div class="settings-section" data-section-id="task_scheduler">
       <h3>Task Scheduler</h3>
       <div class="task-list"><!-- content --></div>
   </div>
   ```

3. **❌ DO NOT use position: relative/absolute for positioning**: Use flex layout instead
   ```css
   /* INCORRECT */
   .task-scheduler-container {
       position: relative;
       z-index: 20;
   }
   ```

Following these structural patterns will ensure the task scheduler UI renders correctly within the settings modal, maintains proper content flow, and avoids the "floating content" issue where components appear below the section heading instead of within it.

## UI Structure Issue Resolution - Updated Solutions

### Critical UI Structure Fix

The issue where the Task Scheduler section header appears separated from its content is caused by incorrect HTML structure and CSS. Here's the corrected implementation:

#### 1. Correct HTML Structure

```html
<!-- Task Scheduler Tab Content -->
<div x-show="activeTab === 'task_scheduler'" x-cloak>
  <div class="settings-section" data-section-id="task_scheduler">
    <h3 class="settings-section-title">Task Scheduler</h3>

    <div x-data="taskScheduler"
         x-init="$nextTick(() => { loadTasks(); })"
         class="task-scheduler-container">
      <!-- Task content here -->
    </div>
  </div>
</div>
```

The key points:
- Use `x-show="activeTab === 'task_scheduler'"` on the outer div (NOT a settings-tab-content class)
- Use correct nesting: outer div → settings-section → section title → container with Alpine binding
- Apply Alpine component binding (`x-data="taskScheduler"`) to the container INSIDE the section, not to the section itself

#### 2. Correct CSS Structure

```css
/* Settings Section Structure */
.settings-section {
  margin-bottom: 2rem;
  width: 100%;
}

.settings-section-title {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.5rem;
  font-weight: 500;
  color: var(--color-primary);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}

/* Task Scheduler Structure */
.settings-section[data-section-id="task_scheduler"] {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.task-scheduler-container {
  width: 100%;
  margin-top: 1rem;
}
```

The key points:
- Ensure the section has `display: flex` and `flex-direction: column`
- Set explicit widths for both section and container
- DO NOT use any fixed positioning, z-indexes, or overlay styles
- Ensure the content container is a direct child of the section element

#### 3. Button Styling

Ensure consistent button styling:

```css
.btn {
  display: inline-block;
  font-weight: 400;
  text-align: center;
  white-space: nowrap;
  vertical-align: middle;
  user-select: none;
  border: 1px solid transparent;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  border-radius: 0.25rem;
  transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out;
  cursor: pointer;
}

.btn-primary {
  color: #fff;
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.btn-secondary {
  color: var(--color-text);
  background-color: var(--color-bg-secondary);
  border-color: var(--color-border);
}
```

#### 4. Common Mistakes to Avoid

These mistakes cause the separation between the section header and content:

- ❌ Using `position: fixed` or absolute positioning
- ❌ Using a modal overlay for the task form
- ❌ Binding the Alpine component to the section element instead of a child container
- ❌ Inconsistent tab structure compared to other tabs
- ❌ Incorrect CSS flex structure for the section

By following the structure above, the task scheduler will appear properly within the settings modal, with the controls correctly nested under the section heading.

## Alpine.js Implementation - Key Patterns To Use

When implementing the Task Scheduler with Alpine.js, follow these patterns to prevent issues:

1. **Keep components simple and flat without special case detection**:
   ```html
   <!-- Correct pattern -->
   <div x-show="activeTab === 'task_scheduler'"
        x-data="taskScheduler"
        x-init="loadTasks()"
        x-cloak>
     <!-- Content -->
   </div>
   ```

2. **Let Alpine's reactivity system handle visibility**:
   - Do NOT manually detect visibility through JavaScript
   - Alpine's `x-show` directive and reactive system will handle this automatically
   - Avoid manual parent element detection using `$el.closest()` or `offsetParent` checks

3. **Avoid injecting special tab-specific logic in parent components**:
   - The `settingsModal` component should NOT contain special code for individual tabs
   - Each tab component should be self-contained and handle its own initialization

4. **Don't add visibility tracking in JS**:
   ```javascript
   // INCORRECT - Don't do this:
   if (window.settingsModal && window.settingsModal.activeTab === 'task_scheduler') {
     loadTasks();
   }
   ```

5. **Key principles for proper Alpine.js usage**:
   - Components should be isolated, with interactions handled through events
   - Use `x-init` for one-time initialization, not conditional logic based on visibility
   - Keep all tab-specific logic within the component itself
   - Let the declarative nature of Alpine.js handle visibility concerns

## Corrected Tab Pattern Implementation

The correct implementation should avoid ANY special case code for task_scheduler, even in x-show directives. The pattern should be completely consistent with how other tabs work in the application:

1. **Use generic tab handling without hardcoded tab names**:
   - Use a data attribute or similar to identify tabs
   - The settings modal should handle all tabs identically with no special cases
   - No conditional code should ever check specifically for "task_scheduler"

2. **No special visibility handling for any specific tab**:
   - All tabs should use the same visibility and initialization patterns
   - Any component should initialize properly regardless of which tab it's in

3. **Core principle**: Do not create any special logic specifically for task_scheduler, regardless of whether it's in HTML directives or JavaScript. The scheduler tab should be treated the same as any other tab in the system.

4. **Consistent tab structure**: All tabs in the settings modal should follow exactly the same DOM and initialization structure without exceptions.

## Common Debugging Challenges and Solutions

When implementing or debugging the task scheduler component, be aware of these common challenges and their solutions:

### 1. Authentication Issues (403 Forbidden)

**Problem**: API endpoints configured with `requires_loopback()` will reject requests from the browser with 403 Forbidden errors.

**Solution**:
```python
# INCORRECT: This blocks browser access
@classmethod
def requires_loopback(cls):
    return True

# CORRECT: This allows authenticated browser access
@classmethod
def requires_loopback(cls):
    return False

@classmethod
def requires_auth(cls):
    return True
```

### 2. Alpine.js Component Nesting Issues

**Problem**: The `$parent` reference is undefined when components are not properly nested.

**Error**:
```
Alpine Expression Error: $parent is not defined
Expression: "$parent.activeTab === 'task_scheduler'"
```

**Solution**: Ensure proper component nesting within the settings modal. Use `template` with `x-if` for tab content rather than `x-show` alone:

```html
<!-- CORRECT pattern -->
<div x-data="settingsModal">
  <!-- Settings modal content -->
  <div x-show="activeTab === 'task_scheduler'" class="settings-tab-content">
    <div x-data="taskScheduler" x-init="$watch('activeTab', val => {
         if(val === 'task_scheduler') forceLoadTasks();
       })">
      <!-- Task scheduler content -->
    </div>
  </div>
</div>
```

### 3. API Endpoint Path Errors

**Problem**: Inconsistent API endpoint paths lead to 404 errors.

**Solution**: Always use the direct endpoint name without the `/api/` prefix:

```javascript
// INCORRECT
const response = await fetch('/api/scheduler_tasks_list');

// CORRECT
const response = await fetch('/scheduler_tasks_list');
```

API endpoints are registered based on the filename in the `python/api` directory, without any `/api/` prefix. The correct pattern is to use the endpoint name directly as the URL path.

### 4. Missing Function Handling

**Problem**: Calling functions that may not exist causes script errors.

**Solution**: Always check if functions exist before calling them:

```javascript
// INCORRECT
window.toast('Message', 'error');

// CORRECT
if (typeof window.toast === 'function') {
    window.toast('Message', 'error');
}
```

### 5. Component Duplication

**Problem**: Multiple instances of the same component cause conflicts.

**Solution**:
- Ensure each component is only initialized once
- Remove any duplicated component declarations
- Check for unintended nesting of components within template loops

### 6. Error Handling for API Responses

**Solution**:
```javascript
try {
    const response = await fetch('/scheduler_tasks_list');
    if (!response.ok) {
        if (response.status === 403) {
            throw new Error('Authentication required');
        }
        throw new Error(`HTTP error ${response.status}`);
    }
    // Process response
} catch (error) {
    console.error('Error fetching tasks:', error);
    if (typeof window.toast === 'function') {
        window.toast('Failed to load tasks: ' + error.message, 'error');
    }
}
```

## Validation System Implementation

### 1. Unified Validation Endpoint
- All validation MUST go through `/scheduler_validate_task`
- Frontend validation is for UX only, not security
- Backend validation is the source of truth
- Cross-field validation MUST be handled by the endpoint

### 2. Validation Rules
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

### 3. Error Display Strategy
- Field-level errors shown below each field
- Form-level validation summary at top
- Toast notifications for major issues
- Loading states during validation

### 4. Container-Aware Validation
- All file paths MUST be absolute
- Paths MUST be validated within container context
- Permissions MUST be checked in container
- Size limits MUST be enforced

## Future Improvements

### 1. UI Enhancements
- File picker interface needed
- Schedule builder UI would improve UX
- Better validation error display

### 2. Performance Optimization
- Consider validation result caching
- Batch file validation
- Optimize API calls

### 3. Enhanced Validation
- File type restrictions
- Template variable support
- More sophisticated schedule validation

## Latest Technical Decisions

### 1. Unified Validation Endpoint
- Single source of truth for validation
- Reduces API calls
- Enables cross-field validation
- Consistent validation rules

### 2. Frontend Integration
- Uses Alpine.js reactivity
- Real-time field validation
- Proper error state management
- Loading state handling

### 3. Error Display Strategy
- Field-level error messages
- Validation summary for multiple errors
- Toast notifications for major issues
- Clear error state indicators
