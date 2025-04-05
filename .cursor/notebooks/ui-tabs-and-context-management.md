# UI Tabs and Context Management

This document details insights and lessons learned from implementing tabbed interfaces and context management in the UI.

## Tab Implementation

### Alpine.js Tab System

The tab system follows a pattern using Alpine.js for reactive state management:

```html
<div x-data="{ activeTab: 'default' }">
  <!-- Tab buttons -->
  <div class="tabs">
    <button
      @click="activeTab = 'tab1'"
      :class="{ 'active': activeTab === 'tab1' }">
      Tab 1
    </button>
    <button
      @click="activeTab = 'tab2'"
      :class="{ 'active': activeTab === 'tab2' }">
      Tab 2
    </button>
  </div>

  <!-- Tab content -->
  <div class="tab-content">
    <div x-show="activeTab === 'tab1'">Content 1</div>
    <div x-show="activeTab === 'tab2'">Content 2</div>
  </div>
</div>
```

### Context-Aware Tab Logic

For the left panel tabs (chats vs. tasks), we implemented context-aware tab logic that:

1. Stores the active tab in localStorage
2. Initializes from localStorage or defaults to 'chats'
3. Updates other components when the tab changes

```javascript
Alpine.data('tabSystem', () => ({
    activeTab: localStorage.getItem('leftPanelTab') || 'chats',

    setActiveTab(tab) {
        this.activeTab = tab;
        localStorage.setItem('leftPanelTab', tab);

        // Notify other components about tab change
        this.$dispatch('tab-changed', { tab });
    },

    init() {
        // Initialize tab on component load
        this.setActiveTab(this.activeTab);
    }
}));
```

### Complex Tab Selection Challenges

When implementing the scheduler tab in the settings modal, we encountered a specific tab selection issue: the scheduler tab couldn't be selected on initial click, but worked after clicking another tab first.

The root causes were identified as:

1. **Alpine.js Reactivity Cycles**: Complex components sometimes require multiple reactivity cycles to fully update
2. **DOM Structure Complexity**: The scheduler tab had deeper nesting than other tabs
3. **Event Handling Issues**: Click events weren't correctly propagating through the Alpine.js reactivity system

#### Solution: Two-Step Activation Process

To solve this, we implemented a specialized two-step tab activation process:

```javascript
// In settings.js
if (this.activeTab === 'scheduler') {
    // First switch to a known-working tab
    this.activeTab = 'agent';

    // Then after a DOM update cycle, switch to scheduler
    setTimeout(() => {
        this.activeTab = 'scheduler';
    }, 50);
}
```

This approach ensures reliable tab selection by:
1. Breaking a complex state transition into two simpler ones
2. Giving Alpine.js time to complete a full reactivity cycle between transitions
3. Using setTimeout to ensure DOM updates between state changes

Additionally, we added a global click interceptor to handle problematic tab clicks:

```javascript
// In scheduler.js
document.addEventListener('click', function(e) {
    const schedulerTab = e.target.closest('.settings-tab[title="Task Scheduler"]');
    if (!schedulerTab) return;

    e.preventDefault();
    e.stopPropagation();

    // Use two-step process for activation
    const modalEl = document.getElementById('settingsModal');
    if (modalEl && modalEl.__x) {
        const modalData = Alpine.$data(modalEl);

        // First switch to agent tab
        modalData.activeTab = 'agent';

        // Then switch to scheduler
        setTimeout(() => {
            modalData.activeTab = 'scheduler';
            localStorage.setItem('settingsActiveTab', 'scheduler');
        }, 50);
    }
}, true); // Use capturing phase for earliest interception
```

### CSS Layout Stability for Tabs

Another issue we addressed was a subtle 2-pixel content jump when switching tabs. This was caused by inconsistent border handling between tab states.

```css
/* Incorrect approach - causes content jump */
.tab {
    border-bottom: none;
}
.tab.active {
    border-bottom: 2px solid var(--color-primary);
}

/* Correct approach - maintains layout stability */
.tab {
    border-bottom: 2px solid transparent;
}
.tab.active {
    border-bottom-color: var(--color-primary);
}
```

This consistent border approach ensures that the tab dimensions remain the same between states, preventing layout shifts.

## Context Management

### Multiple Contexts System

The application manages multiple types of contexts:

1. **Chat contexts** - Regular chat histories stored in `CHATS_FOLDER`
2. **Task contexts** - Task-specific chat histories stored in `TASKS_FOLDER`

We implemented an intelligent auto-detection system to determine the correct context location:

```python
def get_chat_folder_path(chat_id):
    # First check if it exists in tasks folder
    task_path = os.path.join(TASKS_FOLDER, chat_id)
    if os.path.exists(task_path):
        return task_path

    # Then check regular chats folder
    chat_path = os.path.join(CHATS_FOLDER, chat_id)
    if os.path.exists(chat_path):
        return chat_path

    # Default to tasks folder for new contexts that have task_id format
    if is_task_id_format(chat_id):
        return os.path.join(TASKS_FOLDER, chat_id)

    # Default to chats folder
    return os.path.join(CHATS_FOLDER, chat_id)
```

### Context Switching UI

When switching contexts (either between chats or tasks), the UI needs to:

1. Save the current context if needed
2. Load the new context
3. Update the UI state to reflect the new context

This is handled through a combination of API calls and Alpine.js state management:

```javascript
async function switchContext(contextId) {
    // First save current context if needed
    if (currentContextId && isDirty) {
        await saveCurrentContext();
    }

    // Load the new context
    const response = await fetch(`/load_context?id=${contextId}`);
    const contextData = await response.json();

    // Update Alpine.js store
    Alpine.store('app').currentContext = contextData;

    // Update UI state
    currentContextId = contextId;
    isDirty = false;

    // Update selected item in the appropriate tab
    if (contextData.isTask) {
        Alpine.store('taskList').selectTask(contextId);
    } else {
        Alpine.store('chatList').selectChat(contextId);
    }
}
```

### Context Type Detection

The application needs to determine whether a context is a task or a regular chat. This is done through:

1. Context ID format (tasks use a specific format)
2. Storage location (tasks are stored in `TASKS_FOLDER`, chats in `CHATS_FOLDER`)
3. Context metadata (tasks have additional properties)

This detection influences UI behavior, such as which tab gets highlighted and which actions are available.

## Tab-Specific Context Handling

### Left Panel Task Tab

The Task tab in the left panel shows only task contexts, with special handling for:

1. **Task status indication** - Visual indicators for task status (running, idle, etc.)
2. **Task type indication** - Different icons for scheduled vs. ad-hoc tasks
3. **Task-specific actions** - Such as run task, reset task, etc.

```html
<div x-show="activeTab === 'tasks'" class="tab-content">
    <div x-data="taskList" class="task-list">
        <template x-for="task in tasks" :key="task.id">
            <div
                class="task-item"
                :class="{ 'selected': selectedTaskId === task.id }"
                @click="selectTask(task.id)">

                <!-- Task status indicator -->
                <div class="task-status" :class="task.status"></div>

                <!-- Task type icon -->
                <div class="task-icon" :class="task.type"></div>

                <!-- Task name -->
                <div class="task-name" x-text="task.name"></div>

                <!-- Task actions -->
                <div class="task-actions">
                    <button @click.stop="runTask(task.id)"
                            title="Run Task"
                            :disabled="task.status === 'running'">
                        ▶
                    </button>
                </div>
            </div>
        </template>
    </div>
</div>
```

## Best Practices for Tabbed Interfaces

Based on our implementation experience, here are key best practices:

1. **State Persistence**: Always persist tab state to localStorage for better UX across sessions.

2. **Consistent CSS Structure**: Maintain consistent DOM structure and CSS styles across tabs to prevent layout shifts.

3. **Tab Initialization Order**: Pay attention to initialization order, especially for complex tabs.

4. **Defensive Tab Selection**: Implement defensive tab selection with the two-step process for complex tabs:
   ```javascript
   function selectComplexTab(tab) {
       // First switch to a simple tab
       this.activeTab = 'simple-tab';

       // Then switch to the complex tab after a DOM update
       setTimeout(() => {
           this.activeTab = tab;
       }, 10);
   }
   ```

5. **Event Capturing**: Use capturing phase for critical event handling:
   ```javascript
   document.addEventListener('click', handleTabClick, true); // true = use capturing phase
   ```

6. **Debug Logging**: Add comprehensive logging for tab state transitions:
   ```javascript
   function switchTab(tab) {
       console.log(`Switching from ${this.activeTab} to ${tab}`);
       this.activeTab = tab;
       console.log(`Active tab is now: ${this.activeTab}`);
   }
   ```

7. **Global Event Handlers**: Add global document-level handlers for problematic tabs.

8. **Border Handling**: Use transparent borders for inactive states rather than removing borders.

9. **Tab Content Preloading**: For better performance, consider preloading tab content:
   ```javascript
   // Preload content for all tabs but hide non-active ones
   initializeTabs() {
       const tabs = ['tab1', 'tab2', 'tab3'];
       tabs.forEach(tab => {
           this.loadTabContent(tab);
           if (tab !== this.activeTab) {
               document.querySelector(`.tab-content[data-tab="${tab}"]`).style.display = 'none';
           }
       });
   }
   ```

10. **Tab Accessibility**: Ensure keyboard navigation works for all tabs:
    ```javascript
    // Add keyboard support for tabs
    initKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight') {
                this.navigateToNextTab();
            } else if (e.key === 'ArrowLeft') {
                this.navigateToPreviousTab();
            }
        });
    }
    ```

By following these practices, we can create robust, responsive, and user-friendly tabbed interfaces that handle context switching properly.
