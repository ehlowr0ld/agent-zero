# Agent Zero Developer Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
   - [Components Overview](#components-overview)
   - [Directory Structure](#directory-structure)
   - [Key Files](#key-files)
3. [Core Components](#core-components)
   - [Agent System](#agent-system)
     - [Agent Context](#agent-context)
     - [Agent Implementation](#agent-implementation)
     - [Agent Hierarchy](#agent-hierarchy)
   - [Tools Framework](#tools-framework)
     - [Built-in Tools](#built-in-tools)
     - [Tool Implementation](#tool-implementation)
     - [Custom Tool Development](#custom-tool-development)
   - [Memory and Knowledge](#memory-and-knowledge)
     - [Memory System](#memory-system)
     - [Knowledge Base Integration](#knowledge-base-integration)
     - [Vector Search Implementation](#vector-search-implementation)
   - [Prompts System](#prompts-system)
   - [Extension System](#extension-system)
   - [Instruments](#instruments)
4. [API System](#api-system)
   - [API Architecture](#api-architecture)
   - [API Handler Implementation](#api-handler-implementation)
   - [Key Endpoints](#key-endpoints)
   - [Message Processing Flow](#message-processing-flow)
   - [Authentication Mechanisms](#authentication-mechanisms)
5. [Settings System](#settings-system)
   - [Settings Structure](#settings-structure)
   - [Settings Storage](#settings-storage)
   - [Settings UI Integration](#settings-ui-integration)
   - [Configuration Management](#configuration-management)
6. [Tools System](#tools-system)
   - [Tool Base Class](#tool-base-class)
   - [Tool Lifecycle](#tool-lifecycle)
   - [Built-in Tools](#built-in-tools-1)
   - [Tool Response Format](#tool-response-format)
   - [Creating Custom Tools](#creating-custom-tools)
7. [Logging System](#logging-system)
   - [Log Architecture](#log-architecture)
   - [Log Entry Types](#log-entry-types)
   - [Streaming Updates](#streaming-updates)
   - [Progress Tracking](#progress-tracking)
   - [UI Integration](#ui-integration)
8. [Frontend Implementation](#frontend-implementation)
   - [Web UI Structure](#web-ui-structure)
   - [UI Components](#ui-components)
   - [Client-Server Communication](#client-server-communication)
9. [Task Scheduler System](#task-scheduler-system)
   - [Task Types](#task-types)
   - [Scheduling Capabilities](#scheduling-capabilities)
   - [Task Management](#task-management)
10. [Browser Agent System](#browser-agent-system)
    - [Browser Agent Implementation](#browser-agent-implementation)
    - [Browser Context Management](#browser-context-management)
    - [Browser Interactions](#browser-interactions)
11. [Extension Framework In-Depth](#extension-framework-in-depth)
    - [Extension Types](#extension-types)
    - [Extension Lifecycle](#extension-lifecycle)
    - [Key Extensions](#key-extensions)
12. [Memory System In-Depth](#memory-system-in-depth)
    - [Vector Database Implementation](#vector-database-implementation)
    - [Memory Operations](#memory-operations)
    - [Memory Areas](#memory-areas)
    - [Memory Lifecycle](#memory-lifecycle)
13. [History System](#history-system)
    - [History Structure](#history-structure)
    - [Compression Algorithm](#compression-algorithm)
    - [Message Organization](#message-organization)
    - [Token Management](#token-management)
14. [Code Execution System](#code-execution-system)
    - [Runtime Environments](#runtime-environments)
    - [Shell Session Management](#shell-session-management)
    - [Docker Integration](#docker-integration)
    - [Code Execution Security](#code-execution-security)
15. [Knowledge System](#knowledge-system)
    - [Search Architecture](#search-architecture)
    - [Document Query System](#document-query-system)
    - [Memory Integration](#memory-integration)
    - [Search Providers](#search-providers)
16. [Development Guidelines](#development-guidelines)
    - [Python Best Practices](#python-best-practices)
    - [API Development Conventions](#api-development-conventions)
    - [Frontend Development Conventions](#frontend-development-conventions)
17. [Deployment](#deployment)
    - [Docker Setup](#docker-setup)
    - [Environment Configuration](#environment-configuration)

# Task Management Systems

## Overview of Task Systems

The application features two distinct task management systems that serve different purposes:

1. **Task Scheduler** - For scheduling automated system tasks
2. **Todo List** - Used by AI agents as a tool for managing action items

These systems are separate and have different implementations, data models, and UIs.

## Task Scheduler

The Task Scheduler allows users to create and manage automated tasks that run on a schedule or on-demand.

### Multiple Views

The Task Scheduler appears in two different locations in the application:

#### 1. Left Panel View

- Located in the left sidebar navigation
- Provides a quick overview of all scheduled tasks
- Accessible via the "Tasks" tab in the left panel menu
- Primarily for monitoring task status and quick actions
- Implementation is connected to the main Task Scheduler component via Alpine.js store

```javascript
// Task data is synchronized between views
this.$watch('tasks', (newTasks) => {
    // Update the store
    Alpine.store('taskScheduler').tasks = newTasks;

    // Find tasks section in the left panel
    const tasksSection = document.getElementById('tasks-section');
    if (tasksSection && tasksSection.__x) {
        // If Alpine component exists, update its tasks
        tasksSection.__x.getUnobservedData().tasks = newTasks;
    }
});
```

#### 2. Modal Settings Tab View

- Located within the settings modal dialog
- Provides full task management capabilities:
  - Creating new tasks
  - Editing existing tasks
  - Configuring schedules using cron format
  - Viewing task history and results
- Accessed via the Settings menu and the "Task Scheduler" tab
- Contains the primary implementation of the task scheduler UI

### Implementation Details

- Implemented using Alpine.js for reactive UI
- Task data is shared between views using Alpine.js store
- All UI components follow the "scheduler-" CSS class prefix convention
- Task form appears inline within the tab content (not as a separate modal)
- CRON scheduling format used for recurring tasks

### Tab Selection Implementation

The task scheduler tab in the settings modal uses a specialized initialization approach to ensure reliable selection:

1. **Two-Step Tab Activation Process**:
   ```javascript
   // First activate a different tab, then after a DOM update cycle, switch to scheduler
   if (modalData.activeTab !== 'scheduler') {
       // Set to a known-working tab first
       modalData.activeTab = 'agent';

       // Then after a brief delay, switch to scheduler
       setTimeout(() => {
           console.log('Switching to scheduler tab after delay');
           modalData.activeTab = 'scheduler';
           localStorage.setItem('settingsActiveTab', 'scheduler');
       }, 50);
   }
   ```

2. **Global Click Interceptor**:
   ```javascript
   // Create a global event listener for clicks on the scheduler tab
   document.addEventListener('click', function(e) {
       // Find if the click was on the scheduler tab or its children
       const schedulerTab = e.target.closest('.settings-tab[title="Task Scheduler"]');
       if (!schedulerTab) return;

       console.log('Intercepted click on scheduler tab');
       e.preventDefault();
       e.stopPropagation();

       // Get the settings modal data and handle tab switching
       // ...
   }, true); // Use capture phase to intercept before Alpine.js handlers
   ```

3. **Modal Initialization with Tab State**:
   ```javascript
   // Restore active tab from localStorage or use default
   this.activeTab = localStorage.getItem('settingsActiveTab') || 'agent';
   console.log(`Initial active tab: ${this.activeTab}`);

   // Special handling for scheduler tab
   if (this.activeTab === 'scheduler') {
       console.log('Scheduler tab was pre-selected, setting up tab');
       // Use two-step process to ensure proper initialization
       // ...
   }
   ```

This approach ensures reliable tab selection by addressing Alpine.js reactivity issues and DOM update timing challenges.

### Data Model

Tasks in the scheduler have the following properties:

```javascript
{
    name: '',               // Task name
    type: 'scheduled',      // 'scheduled', 'adhoc', or 'recurring'
    state: 'idle',          // 'idle', 'running', 'completed', 'error', 'disabled'
    system_prompt: '',      // System prompt for AI tasks
    prompt: '',             // Task prompt
    attachments: [],        // Array of file paths (container paths)
    minute: '*',            // Cron fields for scheduled tasks
    hour: '*',
    day: '*',
    month: '*',
    weekday: '*',
    ctx_planning: 'auto',   // AI context settings
    ctx_reasoning: 'auto',
    ctx_deep_search: 'off'
}
```

### Task Types

The task scheduler supports two types of tasks:

1. **AdHocTask**: One-time tasks that can be triggered manually with a token
2. **ScheduledTask**: Recurring tasks with a defined schedule using cron-like syntax

Both task types include:
- System prompt for initialization
- User prompt for instructions
- Context settings (planning, reasoning, deep search)
- State management (idle, running, disabled, error)
- Result tracking

### Scheduling Capabilities

The scheduling system uses a cron-like syntax for flexible scheduling:

- **Components**: minute, hour, day, month, weekday
- **Patterns**: Support for specific values, ranges, and steps
- **Presets**: Hourly, daily, weekly, monthly schedules
- **Human-Readable**: Conversions to readable descriptions

Example schedule: `"*/15 * * * *"` for every 15 minutes

### Task Management

Tasks are managed through the `SchedulerTaskList` class, which provides:

- Task storage and retrieval
- Due task identification
- Task execution tracking
- Persistence between sessions

The task execution process:
1. Creates a new agent context
2. Applies task parameters
3. Sends the task message to the agent
4. Records results and updates state
5. Optionally persists the chat for reference

### API Endpoints

The task scheduler system uses several dedicated API endpoints:

1. **scheduler_tick.py**: Periodic endpoint for checking and running scheduled tasks
   - Called automatically by system cron job
   - Checks all scheduled tasks to determine which are due to run
   - Only accessible from localhost (loopback)
   - Not intended for manual task execution

2. **scheduler_task_run.py**: Endpoint for manually running a specific task
   - Called through UI "Run" button
   - Takes a task UUID parameter
   - Triggers immediate execution of the specified task
   - Requires user authentication

3. **scheduler_tasks_list.py**: Lists all tasks with their metadata
   - Returns complete task information including type, status, and schedules
   - Used by both left panel and settings modal views

4. **scheduler_task_create.py**: Creates new tasks
   - Creates either scheduled or ad-hoc tasks
   - Handles setting up initial task state
   - Creates task context

5. **scheduler_task_update.py**: Updates existing task properties
   - Updates task name, schedule, prompts, etc.
   - Handles status transitions (enable/disable)

6. **scheduler_task_delete.py**: Deletes tasks and their associated contexts
   - Removes task from scheduler
   - Cleans up associated chat contexts

### Best Practices for Task Scheduler Development

1. **Use Correct API Endpoints**
   - Use `scheduler_task_run.py` for manual execution (NOT `scheduler_tick.py`)
   - Use appropriate endpoints for CRUD operations

2. **Follow UI Patterns**
   - Use "scheduler-" prefix for all CSS classes
   - Maintain consistent styling with other components
   - Follow tab selection patterns for settings modal integration

3. **Handle Alpine.js Reactivity**
   - Be aware of Alpine.js reactivity limitations
   - Use two-step process for tab switching when needed
   - Ensure proper data initialization before UI access

4. **Context Awareness**
   - Remember that task contexts are stored in a separate folder
   - Use auto-detection for accessing the correct context location
   - Ensure task associations are preserved during reset operations

5. **Tab Selection**
   - Use the established tab selection mechanism via `switchTab()`
   - Store tab state in localStorage for persistence
   - Handle initialization timing carefully

## Todo List

The Todo List is a separate feature designed for AI agents to track and manage their tasks.

### Purpose and Implementation

- Functions as a tool for AI agents to create, track, and complete tasks
- Simpler model focused on basic to-do functionality
- Not directly related to the scheduler system
- Used for tracking action items rather than system automation

### Key Differences from Task Scheduler

1. **Purpose**:
   - Todo List: Task management for AI agents
   - Task Scheduler: Automated system tasks and jobs

2. **Functionality**:
   - Todo List: Basic create/update/complete actions
   - Task Scheduler: Advanced scheduling, system execution, and monitoring

3. **UI Location**:
   - Todo List: Appears in AI agent interfaces
   - Task Scheduler: Left panel and settings modal

4. **Implementation**:
   - Separate code bases with no shared components
   - Different data models and storage mechanisms

## Integration Considerations

When developing features that interact with tasks, consider:

1. **Identify the correct task system** - Determine whether the feature should interact with the Task Scheduler or Todo List.

2. **Usage of shared data** - The Task Scheduler shares data between its two views through the Alpine.js store.

3. **CSS naming conventions** - Task Scheduler components use the "scheduler-" prefix for CSS classes.

4. **Container environment awareness** - When working with file paths in the Task Scheduler, use absolute paths within the container.

## Best Practices

1. Maintain separation between the two task systems to prevent confusion.

2. Use the established naming conventions and patterns for each system.

3. When modifying the Task Scheduler, ensure changes are reflected in both views.

4. Test changes in both views when updating shared functionality.

5. Be aware of the containerized environment when working with file attachments in tasks.

## Naming Similarity and Potential Confusion

There is potential for confusion due to naming similarities across these task-related features:

### Three Distinct Components with Similar Names

1. **Task Scheduler - Left Panel View**: Called "Tasks" or "Tasklist" in the UI
2. **Task Scheduler - Settings Modal Tab**: Also called "Task Scheduler" or "Scheduled Tasks"
3. **Todo List (Agent Tasklist)**: Also referred to as "tasks" in AI agent contexts

### Disambiguation Guidelines

When referring to these components in code, comments, and documentation:

- Use **"Task Scheduler - Left Panel"** or **"Scheduler List View"** for the left sidebar implementation
- Use **"Task Scheduler - Settings Tab"** or **"Scheduler Settings View"** for the modal implementation
- Use **"Todo List"** or **"Agent Tasks"** (never "Tasklist") for the AI agent todo functionality

### Code-Level Disambiguation

- Use clear naming in code to distinguish between these systems:
  ```javascript
  // For Task Scheduler
  const schedulerTasks = Alpine.store('taskScheduler').tasks;

  // For Todo List
  const agentTodos = window.todoList.items;
  ```

- Use consistent CSS class naming:
  ```css
  /* For Task Scheduler */
  .scheduler-task-item { }

  /* For Todo List */
  .todo-item { }
  ```

### Avoid Ambiguous Terms

When discussing task-related features, avoid ambiguous terms like:
- "task list" (use specific name)
- "tasks" (without context)
- "tasklist" (without qualifier)

Instead, always use the full, specific name of the component you're referring to.

## Introduction

Agent Zero is a flexible, extensible agentic framework that enables autonomous AI agents to complete complex tasks. It is designed with a focus on transparency, allowing developers to understand and modify every aspect of its behavior.

The framework is primarily implemented in Python with a web-based user interface. It uses a modular architecture that separates concerns while providing a unified experience for users and developers.

## System Architecture

### Components Overview

Agent Zero follows a hierarchical architecture where agents can delegate tasks to subordinate agents. The core components include:

1. **Agents**: The central actors that receive instructions and perform tasks
2. **Tools**: Functionalities that agents can use to accomplish tasks
3. **Extensions**: Modular components that enhance agent capabilities
4. **Instruments**: Custom scripts and functions that can be called by agents
5. **Prompts**: Text files that guide agent behavior
6. **Memory**: A persistent storage system for agent knowledge
7. **Knowledge Base**: A repository of information that agents can access
8. **API System**: Endpoints for communication between frontend and backend
9. **Task Scheduler**: System for scheduling and managing recurring tasks

The system employs a containerized runtime architecture:

1. **Host System**: Requires only Docker and a web browser
2. **Runtime Container**: Houses the complete Agent Zero framework

### Directory Structure

```
/
├── docker/              # Docker-related files for runtime
├── docs/                # Documentation files and guides
├── instruments/         # Custom scripts and tools
├── knowledge/           # Knowledge base storage
├── logs/                # HTML CLI-style chat logs
├── memory/              # Persistent agent memory
├── prompts/             # System and tool prompts
├── python/              # Core Python codebase
│   ├── api/             # API endpoints
│   ├── extensions/      # Modular extensions
│   │   ├── message_loop_start/    # Loop initialization
│   │   ├── message_loop_prompts/  # Prompt construction
│   │   └── message_loop_end/      # Loop completion
│   ├── helpers/         # Utility functions
│   └── tools/           # Tool implementations
├── tmp/                 # Temporary runtime data
├── webui/               # Web interface
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript modules
│   └── public/          # Static assets
└── work_dir/            # Working directory for code execution
```

### Key Files

- `agent.py`: Core agent implementation
- `models.py`: Model providers and configurations
- `run_ui.py`: Web UI entry point and server configuration
- `run_cli.py`: CLI interface entry point
- `initialize.py`: Framework initialization
- `preload.py`: Pre-initialization routines
- `.env`: Environment configuration (from example.env template)

## Core Components

### Agent System

#### Agent Context

The `AgentContext` class in `agent.py` serves as the management layer for agent instances. It provides:

- Context creation and persistence
- Agent state management (pausing/resuming)
- Inter-agent communication
- Process management for long-running tasks

Key methods include:
- `__init__()`: Creates a new context with configuration
- `communicate()`: Handles user messages to agents
- `nudge()`: Continues processing after a pause
- `reset()`: Resets the agent state
- `run_task()`: Executes a deferred task in a separate thread

The context acts as a container for agent instances, maintaining the relationship between the main agent and any subordinate agents created during task execution.

#### Agent Implementation

The `Agent` class in `agent.py` is the core implementation of the agent system. It handles:

- Message processing
- Tool execution
- Model interaction
- History management
- System prompt generation

Important methods include:
- `monologue()`: Primary processing loop for agent responses
- `prepare_prompt()`: Constructs chat prompts with system messages and history
- `get_system_prompt()`: Generates system prompts from prompt files
- `call_chat_model()`: Interfaces with language models
- `process_tools()`: Extracts and processes tool calls from agent responses

#### Agent Hierarchy

Agents operate in a hierarchical structure:

1. **Agent 0**: The top-level agent that receives instructions directly from the user
2. **Subordinate Agents**: Created by Agent 0 or other agents to handle specific subtasks
3. **Browser Agent**: A specialized agent capable of interacting with web content

Communication flows through structured messages containing:
- **Observations**: The agent's observations of the environment
- **Thoughts**: The agent's reasoning process
- **Reflection**: The agent's evaluation of its own reasoning
- **Tool name and arguments**: When using tools
- **Responses or queries**: Results from tool usage

### Tools Framework

#### Built-in Tools

Agent Zero includes many built-in tools to enable agent capabilities:

| Tool | Description |
|------|-------------|
| `behaviour_adjustment` | Modifies agent behavior based on user instructions |
| `browser_agent` | Enables web browser interaction |
| `browser_do` | Performs actions in the browser |
| `browser_open` | Opens specific URLs in the browser |
| `call_subordinate` | Delegates tasks to subordinate agents |
| `code_execution_tool` | Executes Python, Node.js, and shell code |
| `document_query` | Analyzes text content from webpages and documents |
| `input` | Provides keyboard interaction with active shells |
| `knowledge_tool` | Retrieves information from memory or online sources |
| `memory_save/load/delete` | Manages information in memory |
| `notepad` | Provides a persistent notepad for the agent |
| `reasoning_tool` | Enables advanced reasoning capabilities |
| `response` | Outputs responses to users |
| `tasklist` | Manages agent tasks |

#### Tool Implementation

Tools in Agent Zero follow a common implementation pattern defined in `python/helpers/tool.py`:

```python
class Tool:
    def __init__(self, agent, name, method, args, message, **kwargs):
        # Initialize tool properties

    @abstractmethod
    async def execute(self, **kwargs) -> Response:
        # Tool-specific implementation

    async def before_execution(self, **kwargs):
        # Common pre-execution setup

    async def after_execution(self, response, **kwargs):
        # Common post-execution processing
```

Each tool implementation must define an `execute()` method that contains the tool's specific functionality. The base `Tool` class provides common logging, formatting, and response handling.

Tools return a `Response` object containing:
- `message`: The text result of the tool execution
- `break_loop`: Whether to break the agent's processing loop
- `attachments`: Any additional files or resources

#### Custom Tool Development

Developers can create custom tools by:

1. Creating a tool prompt file in `prompts/$SUBDIR/agent.system.tool.$TOOLNAME.md`
2. Adding a reference to the tool in `agent.system.tools.md`
3. Implementing a tool class in `python/tools` using the `Tool` base class
4. Following existing patterns for consistency

Example implementation:
```python
from python.helpers.tool import Tool, Response

class MyCustomTool(Tool):
    async def execute(self, **kwargs) -> Response:
        # Implement custom functionality
        result = "Tool output message"
        return Response(message=result, break_loop=False)
```

### Memory and Knowledge

#### Memory System

The memory system enables agents to learn from past interactions, operating with:

- **Storage Areas**:
  - **Main**: General-purpose storage
  - **Fragments**: Conversation pieces
  - **Solutions**: Successful past solutions
  - **Instruments**: Available custom tools

- **Memory Operations**:
  - Vector similarity search
  - Document insertion/deletion
  - Metadata management
  - Threshold-based retrieval

The system employs dynamic summarization to condense information while preserving key details.

#### Knowledge Base Integration

The knowledge base provides structured information access:

- **Document Storage**: PDFs, databases, documentation
- **Integration with Memory**: Seamless retrieval across sources
- **RAG Implementation**: Retrieval-augmented generation for tasks

#### Vector Search Implementation

The vector search system uses FAISS (Facebook AI Similarity Search) for efficient similarity retrieval:

- **Vector Embedding**: Converts text to vector representations
- **Cosine Similarity**: Measures relevance between vectors
- **Threshold Filtering**: Retrieves only highly relevant documents

### Prompts System

The prompts system in Agent Zero uses Markdown files to control agent behavior:

- **Base Location**: `prompts/default/` directory
- **Custom Location**: Custom subdirectories can override defaults

Core prompt files include:
- `agent.system.main.md`: The central prompt hub
- `agent.system.main.role.md`: Defines the agent's role
- `agent.system.main.communication.md`: Communication guidelines
- `agent.system.main.solving.md`: Problem-solving approach
- `agent.system.tools.md`: Tool definitions and organization

Prompts can include variables that are replaced at runtime with actual values from the agent's context.

### Extension System

The extension system allows modular enhancements to the agent's capabilities:

- **Location**: `python/extensions/` directory
- **Organization**: Subdirectories based on function:
  - `message_loop_start/`: Initialization extensions
  - `message_loop_prompts/`: Prompt construction extensions
  - `message_loop_end/`: Completion extensions

Extensions are loaded dynamically and executed in alphabetical order, allowing for precise control over the extension execution sequence.

Example extensions include:
- `_10_iteration_no.py`: Tracks conversation iterations
- `_50_recall_memories.py`: Retrieves relevant memories
- `_90_organize_history_wait.py`: Organizes conversation history

### Instruments

Instruments provide custom functionalities without adding to the system prompt token count:

- **Storage**: Long-term memory within Agent Zero
- **Recall**: On-demand by agents when needed
- **Implementation**: Scripts or function calls
- **Location**: `instruments/custom/` directory

Each instrument includes:
- `.md` description file defining the interface
- `.sh` script (or other executable) implementing the functionality

## API System

### API Architecture

Agent Zero employs a comprehensive API system built on Flask that follows a consistent handler pattern for all endpoints. The API architecture is designed for:

1. **Modularity**: Each endpoint is implemented as a separate handler class
2. **Consistency**: All handlers follow a uniform pattern
3. **Security**: Authentication and authorization are built into the framework
4. **Error Handling**: Standardized error reporting across all endpoints

The key components are:

- **Server**: Defined in `run_ui.py` using Flask's blueprint system
- **Base Handler**: `ApiHandler` abstract class in `python/helpers/api.py`
- **Handler Implementations**: Individual files in the `python/api/` directory
- **Authentication Middleware**: Integrated into the base handler

### API Handler Implementation

All API handlers inherit from the `ApiHandler` base class and must implement the `process()` method:

```python
from python.helpers.api import ApiHandler, Input, Output, Request

class MyApiHandler(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        # Process request and return response
        return {"result": "success", "data": {}}
```

The `ApiHandler` base class provides:

- **Authentication Handling**: Validates user credentials
- **Context Management**: Access to agent contexts
- **Error Handling**: Consistent error format
- **Request Parsing**: Handles JSON and form data
- **Response Formatting**: Ensures consistent response structure

Child handler classes should NOT override the `handle_request()` method, as this is a method provided by the parent `ApiHandler` class that manages the request lifecycle. Instead, they should implement the `process()` method which is called by `handle_request()`.

The distinction between legacy handlers and modern handlers:
- **Legacy Handlers**: Standalone functions that use the `handle_request()` function directly
- **Modern Handlers**: Classes that extend `ApiHandler` and implement the `process()` method

Handlers can override authentication requirements with:

```python
class PublicEndpoint(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False  # No authentication required

class ApiKeyEndpoint(ApiHandler):
    @classmethod
    def requires_api_key(cls) -> bool:
        return True  # Requires API key authentication

class LocalOnlyEndpoint(ApiHandler):
    @classmethod
    def requires_loopback(cls) -> bool:
        return True  # Only accessible from localhost
```

### API Handler Migration Guide

To migrate a legacy standalone handler function to a modern `ApiHandler` class, follow these steps:

1. **Create a new class** that extends `ApiHandler`:

```python
from python.helpers.api import ApiHandler, Input, Output, Request

class MyModernHandler(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        # Implementation goes here
        pass
```

2. **Move the processing logic** from the legacy handler's `handle_request()` function to the `process()` method:

Legacy Handler:
```python
def handle_request(environ):
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        return build_cors_preflight_response()

    try:
        request_body = get_body(environ)
        request_data = json.loads(request_body)

        # Processing logic...

        return build_cors_actual_response(json.dumps(response))
    except Exception as e:
        return build_cors_actual_response(json.dumps({"status": "error", "message": str(e)}), 500)
```

Modern Handler:
```python
class MyModernHandler(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        try:
            # Processing logic...
            # Note: input already contains the parsed JSON data

            return response  # Just return the Python dict, no need to jsonify
        except Exception as e:
            print(f"Error in MyModernHandler: {str(e)}")
            return {"status": "error", "message": str(e)}
```

3. **Remove CORS handling** - The base `ApiHandler` class automatically handles CORS headers

4. **Remove JSON parsing** - The base `ApiHandler` class parses JSON automatically

5. **Update return format** - Return Python dictionaries instead of HTTP responses:
   - For success: `return {"status": "success", "data": {...}}`
   - For errors: `return {"status": "error", "message": "Error message"}`

6. **Add authentication requirements** if needed:
```python
class MyModernHandler(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True  # Requires authentication

    async def process(self, input: Input, request: Request) -> Output:
        # Implementation
        pass
```

7. **Register the handler class** in `run_ui.py` instead of the function:
```python
# Legacy registration
app.add_url_rule('/api/my_endpoint', 'my_endpoint', my_legacy_handle_request, methods=['GET', 'POST', 'OPTIONS'])

# Modern registration
app.add_url_rule('/api/my_endpoint', 'my_endpoint', MyModernHandler.as_view('my_endpoint'), methods=['GET', 'POST', 'OPTIONS'])
```

Example of a complete migration:

Before (Legacy):
```python
def handle_request(environ):
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        return build_cors_preflight_response()

    try:
        request_body = get_body(environ)
        request_data = json.loads(request_body)

        task_id = request_data.get('uuid')
        if not task_id:
            raise ValueError("Task ID is required")

        scheduler = TaskScheduler.get()
        task = scheduler._tasks.get_task_by_uuid(task_id)

        response = {
            'status': 'success',
            'task': task.to_dict()
        }

        return build_cors_actual_response(json.dumps(response))
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        return build_cors_actual_response(json.dumps(error_response), 500)
```

After (Modern):
```python
from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import TaskScheduler

class TaskGet(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        try:
            task_id = input.get('uuid')
            if not task_id:
                raise ValueError("Task ID is required")

            scheduler = TaskScheduler.get()
            task = scheduler._tasks.get_task_by_uuid(task_id)

            return {
                'status': 'success',
                'task': task.to_dict()
            }
        except Exception as e:
            print(f"Error in TaskGet: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
```

### Message Processing Flow

The central message processing endpoint in `message.py` demonstrates the complete flow:

```python
class Message(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        task, context = await self.communicate(input=input, request=request)
        return await self.respond(task, context)
```

The key steps are:

1. **Input Processing**: Handle JSON or form data with attachments
   ```python
   if request.content_type.startswith("multipart/form-data"):
       text = request.form.get("text", "")
       ctxid = request.form.get("context", "")
       message_id = request.form.get("message_id", None)
       attachments = request.files.getlist("attachments")
       # ... process attachments ...
   ```

2. **Context Retrieval**: Get or create agent context
   ```python
   context = self.get_context(ctxid)
   ```

3. **System Message Preparation**: Add reasoning/planning if enabled
   ```python
   system_message = []
   if context.reasoning == "on":
       system_message_reasoning = context.agent0.parse_prompt(
           "fw.msg_system_use_reasoning.md"
       )
       system_message.append(system_message_reasoning)
   ```

4. **Message Dispatch**: Send message to agent
   ```python
   return context.communicate(
       UserMessage(message=message, attachments=attachment_paths, system_message=system_message)
   ), context
   ```

5. **Async Response Handling**: Process and return response
   ```python
   async def respond(self, task: DeferredTask, context: AgentContext):
       result = await task.result()  # type: ignore
       return {
           "message": result,
           "context": context.id,
       }
   ```

This flow enables:
- **Asynchronous Processing**: Long-running tasks don't block the API
- **File Handling**: Seamless processing of attachments
- **Context Persistence**: Conversations maintain state across requests
- **Feature Toggling**: Reasoning/planning can be enabled as needed

### Key Endpoints

#### Chat Management

The chat management endpoints provide functionality to manipulate conversations:

1. **Message** (`message.py`): The primary endpoint for user-agent interaction
   ```python
   # Usage: POST /message with JSON {"text": "user message", "context": "context_id"}
   # Returns: {"message": "agent response", "context": "context_id"}
   ```

2. **Chat Rename** (`chat_rename.py`): Renames existing chats
   ```python
   # Usage: POST /chat_rename with {"chat_id": "id", "name": "New Name"}
   # Returns: {"message": "Chat renamed successfully", "chat_id": "id", "name": "New Name"}
   ```

3. **Chat Reset** (`chat_reset.py`): Resets a chat to its initial state
   ```python
   # Usage: POST /chat_reset with {"context": "context_id"}
   # Returns: {"message": "Chat reset successfully"}
   ```

4. **Chat Remove** (`chat_remove.py`): Completely removes a chat and its history
5. **Chat Export** (`chat_export.py`): Exports chat data for backup
6. **Chat Load** (`chat_load.py`): Loads previously exported chat data

#### History and State Management

Endpoints for retrieving and managing conversation state:

1. **History Get** (`history_get.py`): Retrieves conversation history
   ```python
   class GetHistory(ApiHandler):
       async def process(self, input: dict, request: Request) -> dict | Response:
           ctxid = input.get("context", [])
           context = self.get_context(ctxid)
           agent = context.streaming_agent or context.agent0
           history = agent.history.output()
           size = tokens.approximate_tokens(agent.history.output_text())

           return {
               "history": history,
               "tokens": size
           }
   ```

2. **Poll** (`poll.py`): Checks for updates without sending a message
3. **Nudge** (`nudge.py`): Continues processing after a pause
4. **Pause** (`pause.py`): Pauses agent processing
5. **Restart** (`restart.py`): Restarts the agent

#### Feature Control

Endpoints that control agent capabilities:

1. **Planning Control**:
   - `planning_get.py`: Gets current planning state
   - `planning_set.py`: Enables/disables planning mode

2. **Reasoning Control**:
   - `reasoning_get.py`: Gets current reasoning state
   - `reasoning_set.py`: Enables/disables reasoning mode

3. **Deep Search Control**:
   - `deep_search_get.py`: Gets deep search state
   - `deep_search_set.py`: Enables/disables deep search mode

#### File Management

Endpoints for file operations:

1. **Upload** (`upload.py`): Handles file uploads
2. **Download** (`download_work_dir_file.py`): Downloads files from work directory
3. **Delete** (`delete_work_dir_file.py`): Deletes files
4. **List Files** (`get_work_dir_files.py`): Lists available files
5. **File Info** (`file_info.py`): Retrieves file metadata

#### Utility Endpoints

Various utility endpoints:

1. **Notepad** (`notepad_get.py`): Retrieves agent notepad content
2. **Task Management**:
   - `tasklist_get.py`: Gets agent task list
   - `taskslist.py`: Gets detailed task information
3. **Health Check** (`health.py`): System health and status information
4. **Settings Management**:
   - `settings_get.py`: Retrieves system settings
   - `settings_set.py`: Updates system settings

### Authentication Mechanisms

The API system supports multiple authentication mechanisms:

1. **Basic Authentication**: Username/password for web UI
   ```python
   # Implemented in ApiHandler base class
   if cls.requires_auth() and not cls._is_authenticated(request):
       return cls._unauthorized_response()
   ```

2. **API Key Authentication**: For programmatic access
   ```python
   # Implemented in ApiHandler base class
   if cls.requires_api_key() and not cls._has_valid_api_key(request):
       return cls._forbidden_response("Invalid API key")
   ```

3. **Loopback Restriction**: For sensitive endpoints
   ```python
   # Implemented in ApiHandler base class
   if cls.requires_loopback() and not cls._is_loopback(request):
       return cls._forbidden_response("This endpoint is only available from localhost")
   ```

The authentication system is configurable through environment variables and settings.

## Settings System

### Settings Structure

Agent Zero employs a comprehensive settings system defined in `python/helpers/settings.py`. The core of the system is the `Settings` type:

```python
class Settings(TypedDict):
    chat_model_provider: str
    chat_model_name: str
    chat_model_kwargs: dict[str, str]
    chat_model_ctx_length: int
    chat_model_ctx_history: float
    chat_model_reasoning: bool
    chat_model_vision: bool
    chat_model_rl_requests: int
    chat_model_rl_input: int
    chat_model_rl_output: int

    util_model_provider: str
    util_model_name: str
    util_model_kwargs: dict[str, str]
    util_model_ctx_length: int
    util_model_ctx_input: float
    util_model_rl_requests: int
    util_model_rl_input: int
    util_model_rl_output: int

    embed_model_provider: str
    embed_model_name: str
    embed_model_kwargs: dict[str, str]
    embed_model_rl_requests: int
    embed_model_rl_input: int

    browser_model_provider: str
    browser_model_name: str
    browser_model_vision: bool
    browser_model_kwargs: dict[str, str]

    agent_prompts_subdir: str
    agent_memory_subdir: str
    agent_knowledge_subdir: str
    mcp_servers: str

    api_keys: dict[str, str]

    auth_login: str
    auth_password: str
    root_password: str

    # ... additional settings ...
```

This comprehensive structure defines all configurable aspects of the system, including:

1. **Model Configuration**: Providers, model names, and parameters
2. **Context Management**: Token limits and allocation
3. **Feature Flags**: Vision, reasoning, and planning capabilities
4. **Rate Limiting**: Request and token limits
5. **Resource Locations**: Directories for prompts, memory, and knowledge
6. **Authentication**: Login credentials and API keys
7. **Integration Settings**: MCP servers, RFC configuration, etc.

### Settings Storage

Settings are stored in multiple locations for different purposes:

1. **Settings File**: JSON storage for most settings
   ```python
   SETTINGS_FILE = files.get_abs_path("tmp/settings.json")

   def _write_settings_file(settings: Settings):
       os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
       with open(SETTINGS_FILE, "w") as f:
           json.dump(settings, f, indent=2)
   ```

2. **Environment Variables**: Storage for sensitive settings
   ```python
   def _write_sensitive_settings(settings: Settings):
       dotenv.save_dotenv_value(dotenv.KEY_AUTH_LOGIN, settings.get("auth_login", ""))
       if settings.get("auth_password") and settings.get("auth_password") != PASSWORD_PLACEHOLDER:
           dotenv.save_dotenv_value(dotenv.KEY_AUTH_PASSWORD, settings.get("auth_password", ""))
       # ... additional sensitive settings ...
   ```

3. **System Storage**: Some settings affect system configuration
   ```python
   def set_root_password(password: str):
       if not password:
           return
       # Execute system command to set root password
       result = subprocess.run(["chpasswd"], input=f"root:{password}", text=True)
   ```

The system handles secure storage of sensitive information:
- Passwords are never stored in plain text in the settings file
- API keys are managed separately from general settings
- Environment variables are used for sensitive configuration

### Settings UI Integration

The settings system provides formatted output for the UI:

```python
def convert_out(settings: Settings) -> SettingsOutput:
    # ... create sections and fields ...

    return {
        "sections": [
            auth_section,
            chat_model_section,
            util_model_section,
            embed_model_section,
            browser_model_section,
            # ... other sections ...
        ]
    }
```

UI-friendly structures include:

1. **Sections**: Logical groupings of related settings
   ```python
   class SettingsSection(TypedDict, total=False):
       id: str
       title: str
       description: str
       fields: list[SettingsField]
       tab: str  # Indicates which tab this section belongs to
   ```

2. **Fields**: Individual settings with metadata
   ```python
   class SettingsField(TypedDict, total=False):
       id: str
       title: str
       description: str
       type: Literal["text", "number", "select", "range", "textarea", "password", "switch"]
       value: Any
       min: float
       max: float
       step: float
       options: list[FieldOption]
   ```

3. **Options**: Selection choices for dropdown fields
   ```python
   class FieldOption(TypedDict):
       value: str
       label: str
   ```

This structure enables the frontend to dynamically generate forms based on available settings, organized into tabs and sections for usability.

### Configuration Management

The settings system includes utilities for managing configuration:

1. **Default Settings**: Provides baseline configuration
   ```python
   def get_default_settings() -> Settings:
       return {
           "chat_model_provider": "openai",
           "chat_model_name": "gpt-4o",
           "chat_model_kwargs": {"temperature": "0.7"},
           # ... default values for all settings ...
       }
   ```

2. **Settings Normalization**: Ensures valid settings
   ```python
   def normalize_settings(settings: Settings) -> Settings:
       # Ensure all required settings exist
       defaults = get_default_settings()
       for key in defaults:
           if key not in settings:
               settings[key] = defaults[key]
       return settings
   ```

3. **Runtime Configuration**: Converts settings to agent configuration
   ```python
   def get_runtime_config(set: Settings):
       # Create configuration object from settings
       from agent import AgentConfig, ModelConfig

       return AgentConfig(
           chat_model=ModelConfig(
               provider=set["chat_model_provider"],
               name=set["chat_model_name"],
               vision=set["chat_model_vision"],
               kwargs=set["chat_model_kwargs"],
           ),
           # ... configure other aspects from settings ...
       )
   ```

4. **Settings Application**: Applies changes to active system
   ```python
   def _apply_settings():
       # Apply settings to running system
       # ... update MCP servers ...
       # ... update model providers ...
       # ... apply other runtime changes ...
   ```

This comprehensive approach ensures that settings are properly validated, normalized, and applied throughout the system, while providing a clean interface for the UI.

## Tools System

The Tools System in Agent Zero provides a flexible framework for implementing agent capabilities that interact with external systems, process data, or provide structured responses. Tools are the primary mechanism through which agents interact with the world.

### Tool Base Class

All tools in Agent Zero inherit from the base `Tool` class defined in `python/helpers/tool.py`. The base class provides:

```python
class Tool:
    def __init__(self, agent, name, method, args, message):
        self.agent = agent  # Reference to the agent using the tool
        self.name = name    # Tool name
        self.method = method  # Method to call (for multi-method tools)
        self.args = args or {}  # Arguments passed to the tool
        self.message = message  # Original message that triggered the tool
        self.log = None  # Log object for tracking tool execution

    # Abstract methods that must be implemented
    async def execute(self, **kwargs):
        """Main execution method that performs the tool's function"""
        pass

    # Lifecycle hooks
    async def before_execution(self, **kwargs):
        """Called before execute() to set up logging and display info"""
        pass

    async def after_execution(self, response, **kwargs):
        """Called after execute() to handle response processing"""
        pass

    def get_log_object(self):
        """Returns a log object for tracking the tool execution"""
        pass
```

The Tool class provides a consistent interface for all tools, with hooks for the entire lifecycle of tool execution:

1. **Initialization**: Sets up the tool with agent context, name, method, and arguments
2. **Pre-execution**: Logging and preparation
3. **Execution**: The main tool functionality
4. **Post-execution**: Response handling and cleanup

Tools return standardized `Response` objects:

```python
@dataclass
class Response:
    message: str  # Response message to be shown to the user
    break_loop: bool = False  # Whether to break the agent's thinking loop
```

Setting `break_loop=True` indicates the agent should stop thinking and return the response to the user directly.

Tools may also update their log objects during execution:

```python
# Example from browser_open.py
self.update_progress("Taking screenshot...")
screenshot = await self.save_screenshot()
self.log.update(screenshot=screenshot)
```

These log updates provide rich context for the user interface.

### Creating Custom Tools

Custom tools can be created by inheriting from the `Tool` base class:

```python
from python.helpers.tool import Tool, Response

class MyCustomTool(Tool):
    async def execute(self, **kwargs):
        # Implementation logic
        result = self.process_data(self.args.get("input_data"))
        return Response(message=result, break_loop=False)

    async def before_execution(self, **kwargs):
        # Set up logging
        self.log = self.agent.context.log.log(
            type="custom_tool",
            heading=f"{self.agent.agent_name}: Using tool '{self.name}'",
            content="",
            kvps=self.args,
        )

    async def after_execution(self, response, **kwargs):
        # Add to history
        await self.agent.hist_add_tool_result(self.name, response.message)

    def process_data(self, input_data):
        # Custom processing logic
        return f"Processed: {input_data}"
```

To make a custom tool available to agents:

1. Add the tool to the appropriate directory (`python/tools/`)
2. Register the tool in the tool registry
3. Update prompt templates to include the new tool
4. Handle tool-specific response formatting

Custom tools should follow these best practices:

1. Provide clear documentation in prompts
2. Handle errors gracefully
3. Follow consistent response formatting
4. Use `before_execution` and `after_execution` hooks appropriately
5. Properly manage resources and state

## Logging System

The Logging System in Agent Zero provides a comprehensive framework for tracking and displaying the execution flow, tool interactions, user inputs, and system events. It serves both operational and UI purposes, enabling rich interactive displays and debugging capabilities.

### Log Architecture

The logging system is built around two core classes defined in `python/helpers/log.py`:

1. **Log**: The central logging manager that maintains a collection of log entries.
2. **LogItem**: Individual log entries with rich metadata.

Here's the architecture of the `Log` class:

```python
class Log:
    def __init__(self):
        self.guid: str = str(uuid.uuid4())  # Unique identifier for this log instance
        self.updates: list[int] = []        # Sequential list of update indices
        self.logs: list[LogItem] = []       # List of all log items
        self.set_initial_progress()         # Initialize progress tracking
```

The `Log` class provides these key methods:

- **log()**: Creates a new log entry
- **_update_item()**: Updates an existing log entry
- **set_progress()**: Updates the current progress state
- **output()**: Formats log entries for display
- **reset()**: Clears all log entries

Individual log entries are represented by the `LogItem` class:

```python
@dataclass
class LogItem:
    log: "Log"                                 # Reference to parent Log
    no: int                                    # Sequential number
    type: str                                  # Type of log entry
    heading: str                               # Main heading text
    content: str                               # Detailed content
    temp: bool                                 # Is temporary or permanent
    update_progress: Optional[ProgressUpdate] = "persistent"  # Progress behavior
    kvps: Optional[OrderedDict] = None         # Key-value pairs for structured data
    id: Optional[str] = None                   # Optional unique identifier
    guid: str = ""                             # Log instance ID
```

This structure enables:

1. **Hierarchical Logging**: Log entries track their parent `Log` instance
2. **Uniqueness Tracking**: GUIDs prevent updating stale log entries
3. **Structured Data**: Key-value pairs for extended metadata
4. **Progress Tracking**: Automatic progress state management
5. **UI State Management**: Temporary vs. permanent entries

### Log Entry Types

The logging system defines multiple log entry types, each with specific UI rendering:

```python
Type = Literal[
    "agent",     # Agent operations
    "browser",   # Browser interactions
    "code_exe",  # Code execution
    "error",     # Error messages
    "hint",      # Hints and suggestions
    "info",      # Informational messages
    "progress",  # Progress updates
    "response",  # Agent responses
    "tool",      # Tool usage
    "input",     # User input
    "user",      # User messages
    "util",      # Utility operations
    "warning",   # Warning messages
]
```

Each type has specialized rendering in the UI:

1. **agent**: Shows agent thinking process, typically with monospace formatting
2. **browser**: Shows browser state, may include screenshots
3. **code_exe**: Shows code execution with syntax highlighting and output
4. **error**: Shows error messages with distinctive red styling
5. **response**: Shows agent responses to the user
6. **tool**: Shows tool usage with argument formatting

### Streaming Updates

The logging system supports streaming updates to existing log entries, enabling real-time display of ongoing operations:

```python
def stream(
    self,
    heading: str | None = None,
    content: str | None = None,
    **kwargs,
):
    if heading is not None:
        self.update(heading=self.heading + heading)
    if content is not None:
        self.update(content=self.content + content)

    for k, v in kwargs.items():
        prev = self.kvps.get(k, "") if self.kvps else ""
        self.update(**{k: prev + v})
```

This streaming capability is used for:

1. **Tool Output**: Real-time updates of long-running tool executions
2. **Code Execution**: Live streaming of code execution results
3. **Agent Thinking**: Progressive display of agent reasoning
4. **Search Results**: Incremental display of search progress

The streaming implementation ensures that UI updates are efficient by only sending the changes rather than the full content.

### Progress Tracking

The logging system includes specialized progress tracking:

```python
ProgressUpdate = Literal["persistent", "temporary", "none"]

def set_progress(self, progress: str, no: int = 0, active: bool = True):
    self.progress = progress
    if not no:
        no = len(self.logs)
    self.progress_no = no
    self.progress_active = active
```

Progress updates can be:

1. **Persistent**: Remain as the current progress until explicitly changed
2. **Temporary**: Only show as progress while the operation is active
3. **None**: Do not affect the progress display

The system automatically updates progress from log entries:

```python
def _update_progress_from_item(self, item: LogItem):
    if item.heading and item.update_progress != "none":
        if item.no >= self.progress_no:
            self.set_progress(
                item.heading,
                (item.no if item.update_progress == "persistent" else -1),
            )
```

This enables a consistent progress indication in the UI, showing the current system state.

### UI Integration

Log entries are designed for direct integration with the UI:

```python
def output(self):
    return {
        "no": self.no,
        "id": self.id,
        "type": self.type,
        "heading": self.heading,
        "content": self.content,
        "temp": self.temp,
        "kvps": self.kvps,
    }
```

The `output()` method formats log entries for JSON serialization, enabling:

1. **API Responses**: Log entries are returned via API endpoints
2. **Frontend Rendering**: The UI renders entries based on their type
3. **Differential Updates**: The UI can efficiently update based on changes

The logging system is also integrated with persistence:

```python
def _serialize_log(log: Log):
    if not log:
        return None
    return {
        "guid": log.guid,
        "updates": log.updates,
        "logs": [
            {
                "no": item.no,
                "type": item.type,
                "heading": item.heading,
                "content": item.content,
                "temp": item.temp,
                "kvps": dict(item.kvps) if item.kvps else None,
                "id": item.id,
            }
            for item in log.logs
        ],
    }
```

This enables:
1. **Chat Persistence**: Logs are saved as part of chat persistence
2. **History Reconstruction**: Chat history includes visual context
3. **Debugging**: Complete execution flow can be reconstructed

The logging system forms a core part of the Agent Zero user experience, providing rich context for agent operations and tool usage.

## Frontend Implementation

### Web UI Structure

The web UI is implemented using HTML, CSS, and JavaScript with Alpine.js for reactivity:

- **Main Files**:
  - `webui/index.html`: Primary HTML template
  - `webui/index.js`: Core JavaScript functionality
  - `webui/index.css`: Global styling

- **Module Organization**:
  - `webui/js/*.js`: Feature-specific JavaScript modules
  - `webui/css/*.css`: Component-specific CSS styles

The UI is served by the Flask server defined in `run_ui.py`.

### UI Components

#### Message Display System

The message display system in `webui/js/messages.js` manages the rendering and formatting of different message types in the conversation:

```javascript
export function getHandler(type) {
  switch (type) {
    case "user":
      return drawMessageUser;
    case "agent":
      return drawMessageAgent;
    case "response":
      return drawMessageResponse;
    case "tool":
      return drawMessageTool;
    case "code_exe":
      return drawMessageCodeExe;
    case "browser":
      return drawMessageBrowser;
    case "warning":
      return drawMessageWarning;
    case "error":
      return drawMessageError;
    case "info":
      return drawMessageInfo;
    case "util":
      return drawMessageUtil;
    // ...
  }
}
```

This handler-based approach provides specialized rendering for different message types:

1. **User Messages** (`drawMessageUser`):
   - Displays user input with appropriate formatting
   - Renders images and attachments
   - Supports LaTeX formula rendering
   - Handles markdown formatting

2. **Agent Messages** (`drawMessageAgent`):
   - Displays AI responses with syntax highlighting for code
   - Handles complex nested content structures
   - Formats API responses and structured data

3. **Tool Messages** (`drawMessageTool`):
   - Displays tool usage with input parameters
   - Shows tool results with appropriate formatting
   - Provides visual distinction for different tools

4. **Code Execution Messages** (`drawMessageCodeExe`):
   - Formats code execution inputs and outputs
   - Provides syntax highlighting for various languages
   - Handles terminal output formatting

5. **Browser Messages** (`drawMessageBrowser`):
   - Displays browser interactions and screenshots
   - Formats web page content and navigation

The message display system also includes utility functions for:
- Copy-to-clipboard functionality
- LaTeX math rendering
- HTML sanitization and formatting
- File path and URL linkification
- Image and attachment handling

Every message component includes copy buttons for easy content copying:

```javascript
function createCopyButton() {
  const button = document.createElement("button");
  button.className = "copy-button";
  button.textContent = "Copy";

  button.addEventListener("click", async function (e) {
    e.stopPropagation();
    const container = this.closest(".msg-content, .kvps-row, .message-text");
    let textToCopy;
    // ...extract text content...
    await navigator.clipboard.writeText(textToCopy);
    // ...visual feedback...
  });

  return button;
}
```

#### Settings Management

The settings component in `webui/js/settings.js` provides a dynamic interface for configuring Agent Zero parameters:

```javascript
document.addEventListener('alpine:init', () => {
    Alpine.data('settingsModal', () => ({
        isOpen: false,
        activeTab: 'general',
        settings: {
            title: "Settings",
            buttons: [
                { "id": "save", "title": "Save", "classes": "btn btn-ok" },
                { "id": "cancel", "title": "Cancel", "type": "secondary", "classes": "btn btn-cancel" }
            ],
            sections: []
        },
        filteredSections: [],
        // ...
    }))
});
```

The settings modal uses Alpine.js for:
1. **Dynamic Form Generation**:
   - Sections and fields are generated from backend configuration
   - Different input types (text, select, range, etc.) are supported
   - Field validation and error handling

2. **Tab-Based Organization**:
   - Settings are organized into tabs for different categories
   - Tab state is preserved between sessions
   - Only relevant settings are shown for each tab

3. **Persistence**:
   - Settings are saved to the backend via the `/settings_set` endpoint
   - Successful saves are confirmed with toast notifications
   - Changes can be canceled without saving

The component handles different field types through conditional rendering:

```html
<!-- From index.html -->
<template x-if="field.type === 'text'">
    <input type="text" x-model="field.value" x-bind:placeholder="field.placeholder || ''" x-bind:readonly="field.readonly">
</template>
<template x-if="field.type === 'number'">
    <input type="number" x-model="field.value" x-bind:min="field.min" x-bind:max="field.max" x-bind:step="field.step || 1" x-bind:readonly="field.readonly">
</template>
<!-- Additional field types... -->
```

Settings persistence is handled through API communication:

```javascript
async handleButton(buttonId) {
    if (buttonId === 'save') {
        try {
            // Build a flat object of all field values
            const result = {};
            this.settings.sections.forEach(section => {
                section.fields.forEach(field => {
                    // Only include modifiable fields
                    if (field.readonly !== true) {
                        result[field.id] = field.value;
                    }
                });
            });

            // Send the settings to the backend
            const response = await window.sendJsonData("/settings_set", {
                settings: result
            });
            // ...
        } catch (e) {
            // ...error handling...
        }
    }
}
```

#### Task Scheduler Interface

The task scheduler interface in `webui/js/task_scheduler.js` enables:
- Creating one-time and scheduled tasks
- Managing task scheduling with cron expressions
- Monitoring task execution status
- Viewing task results
- Enabling/disabling tasks
- Deleting tasks

#### File Browser

The file browser in `webui/js/file_browser.js` provides:
- Directory navigation
- File preview
- Upload/download functionality
- File deletion
- Directory creation
- Path-based navigation

### Client-Server Communication

The frontend communicates with the backend using JSON API calls:

- `sendMessage()`: Sends a message to the agent and processes the response
- `poll()`: Periodically checks for updates
- `sendJsonData()`: General-purpose API communication

Responses are processed and rendered in the appropriate UI components based on the message type and content.

## Task Scheduler System

### Task Types

The task scheduler supports two types of tasks:

1. **AdHocTask**: One-time tasks that can be triggered manually with a token
2. **ScheduledTask**: Recurring tasks with a defined schedule using cron-like syntax

Both task types include:
- System prompt for initialization
- User prompt for instructions
- Context settings (planning, reasoning, deep search)
- State management (idle, running, disabled, error)
- Result tracking

### Scheduling Capabilities

The scheduling system uses a cron-like syntax for flexible scheduling:

- **Components**: minute, hour, day, month, weekday
- **Patterns**: Support for specific values, ranges, and steps
- **Presets**: Hourly, daily, weekly, monthly schedules
- **Human-Readable**: Conversions to readable descriptions

Example schedule: `"*/15 * * * *"` for every 15 minutes

### Task Management

Tasks are managed through the `SchedulerTaskList` class, which provides:

- Task storage and retrieval
- Due task identification
- Task execution tracking
- Persistence between sessions

The task execution process:
1. Creates a new agent context
2. Applies task parameters
3. Sends the task message to the agent
4. Records results and updates state
5. Optionally persists the chat for reference

### API Endpoints

The task scheduler system uses several dedicated API endpoints:

1. **scheduler_tick.py**: Periodic endpoint for checking and running scheduled tasks
   - Called automatically by system cron job
   - Checks all scheduled tasks to determine which are due to run
   - Only accessible from localhost (loopback)
   - Not intended for manual task execution

2. **scheduler_task_run.py**: Endpoint for manually running a specific task
   - Called through UI "Run" button
   - Takes a task UUID parameter
   - Triggers immediate execution of the specified task
   - Requires user authentication

3. **scheduler_tasks_list.py**: Lists all tasks with their metadata
   - Returns complete task information including type, status, and schedules
   - Used by both left panel and settings modal views

4. **scheduler_task_create.py**: Creates new tasks
   - Creates either scheduled or ad-hoc tasks
   - Handles setting up initial task state
   - Creates task context

5. **scheduler_task_update.py**: Updates existing task properties
   - Updates task name, schedule, prompts, etc.
   - Handles status transitions (enable/disable)

6. **scheduler_task_delete.py**: Deletes tasks and their associated contexts
   - Removes task from scheduler
   - Cleans up associated chat contexts

### Best Practices for Task Scheduler Development

1. **Use Correct API Endpoints**
   - Use `scheduler_task_run.py` for manual execution (NOT `scheduler_tick.py`)
   - Use appropriate endpoints for CRUD operations

2. **Follow UI Patterns**
   - Use "scheduler-" prefix for all CSS classes
   - Maintain consistent styling with other components
   - Follow tab selection patterns for settings modal integration

3. **Handle Alpine.js Reactivity**
   - Be aware of Alpine.js reactivity limitations
   - Use two-step process for tab switching when needed
   - Ensure proper data initialization before UI access

4. **Context Awareness**
   - Remember that task contexts are stored in a separate folder
   - Use auto-detection for accessing the correct context location
   - Ensure task associations are preserved during reset operations

5. **Tab Selection**
   - Use the established tab selection mechanism via `switchTab()`
   - Store tab state in localStorage for persistence
   - Handle initialization timing carefully

## Browser Agent System

### Browser Agent Implementation

The Browser Agent is a specialized agent that can interact with web content through automated browser control. It's implemented in `python/tools/browser_agent.py` and leverages the `browser_use` library for browser automation.

The Browser Agent is structured around a state management system:

```python
class State:
    @staticmethod
    async def create(agent: Agent):
        state = State(agent)
        return state

    def __init__(self, agent: Agent):
        self.agent = agent
        self.context = None
        self.task = None
        self.use_agent = None
        self.browser = None
        self.iter_no = 0
```

The `State` class manages:
- Browser context and initialization
- Task execution and tracking
- Agent association
- Iteration counting for intervention handling

The primary tool class `BrowserAgent` inherits from the base `Tool` class and implements the browser agent functionality:

```python
class BrowserAgent(Tool):
    async def execute(self, message="", **kwargs):
        # Implementation of browser agent logic
```

### Browser Context Management

The Browser Agent initializes and manages a browser context for web interaction:

```python
async def _initialize(self):
    if self.context:
        return

    self.browser = browser_use.Browser(
        config=browser_use.BrowserConfig(
            headless=True,
            disable_security=True,
        )
    )

    # Await the coroutine to get the browser context
    self.context = await self.browser.new_context()

    # override async methods to create hooks
    self.override_hooks()

    # Add init script to the context - applied to all new pages
    await self.context._initialize_session()
    pw_context = self.context.session.context
    js_override = files.get_abs_path("lib/browser/init_override.js")
    await pw_context.add_init_script(path=js_override)
```

This implementation:
1. Creates a headless browser instance
2. Initializes a new browser context for isolation
3. Adds JavaScript hooks for enhanced interaction
4. Sets up initialization scripts for every new page

### Browser Interactions

The Browser Agent supports complex web interactions through a controller pattern:

```python
# Initialize controller
controller = browser_use.Controller()

# Define action for task completion
@controller.registry.action("Done with task", param_model=DoneResult)
async def done(params: DoneResult):
    result = browser_use.ActionResult(
        is_done=True, extracted_content=params.model_dump_json()
    )
    return result
```

The controller provides a structured way to:
1. Define browser actions and commands
2. Handle results from browser interactions
3. Extract content from web pages
4. Complete tasks with formatted results

The Browser Agent uses a specialized system prompt for web interaction guidance:

```python
class CustomSystemPrompt(browser_use.SystemPrompt):
    def get_system_message(self) -> SystemMessage:
        existing_rules = super().get_system_message().text()
        new_rules = agent.read_prompt("prompts/browser_agent.system.md")
        return SystemMessage(content=f"{existing_rules}\n{new_rules}".strip())
```

This approach merges default browser interaction rules with application-specific guidance for optimal web navigation.

## Extension Framework In-Depth

### Extension Types

Agent Zero's extension system allows modifying agent behavior at different points in the message processing lifecycle. Extensions are organized into distinct types based on when they execute:

1. **Message Loop Start Extensions**:
   - Located in `python/extensions/message_loop_start/`
   - Execute before the message processing begins
   - Initialize iteration counting and other pre-processing tasks
   - Example: `_10_iteration_no.py` - Tracks conversation iterations

2. **Message Loop Prompts Extensions**:
   - Located in `python/extensions/message_loop_prompts/`
   - Modify and enhance the prompts used by the agent
   - Retrieve relevant memories and solutions
   - Examples:
     - `_50_recall_memories.py` - Recalls relevant memories
     - `_51_recall_solutions.py` - Recalls relevant solutions
     - `_90_organize_history_wait.py` - Manages conversation history

3. **Message Loop End Extensions**:
   - Located in `python/extensions/message_loop_end/`
   - Execute after message processing completes
   - Handle persistence and cleanup
   - Examples:
     - `_10_organize_history.py` - Compresses and organizes conversation history
     - `_90_save_chat.py` - Persists chat state
     - `_95_reset_agent_data.py` - Resets agent data

4. **Monologue Start/End Extensions**:
   - Located in `python/extensions/monologue_start/` and `python/extensions/monologue_end/`
   - Execute before and after the agent's monologue processing
   - Handle behavior updates and memory operations
   - Examples:
     - `_50_memorize_fragments.py` - Stores conversation fragments in memory
     - `_51_memorize_solutions.py` - Memorizes successful solutions

5. **System Prompt Extensions**:
   - Located in `python/extensions/system_prompt/`
   - Modify the system prompt construction
   - Add behavior guidance and special instructions
   - Example: `_20_behaviour_prompt.py` - Adds behavior directives

### Extension Lifecycle

All extensions follow a common lifecycle defined by the base `Extension` class in `python/helpers/extension.py`:

```python
class Extension:
    def __init__(self, agent: Agent, *args, **kwargs):
        self.agent = agent
        self.kwargs = kwargs

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass
```

Extensions are loaded and executed dynamically based on their location and filename order, with execution proceeding as follows:

1. Extension discovery and loading at agent initialization
2. Sequential execution based on filename ordering (numeric prefixes control order)
3. Data passing through the `LoopData` object between extensions
4. Results accumulation and application to agent behavior

### Key Extensions

#### Memory Recall Extensions

The `RecallMemories` extension in `_50_recall_memories.py` retrieves relevant memories based on the current conversation:

```python
class RecallMemories(Extension):
    INTERVAL = 3    # Execute every 3 iterations
    RESULTS = 3     # Retrieve top 3 results
    THRESHOLD = 0.6 # Minimum similarity threshold

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Execute memory recall on interval
        if loop_data.iteration % RecallMemories.INTERVAL == 0:
            task = asyncio.create_task(self.search_memories(loop_data=loop_data, **kwargs))
        else:
            task = None

        # Set to agent to be able to wait for it
        self.agent.set_data(DATA_NAME_TASK, task)
```

The memory recall process:
1. Analyzes recent conversation history
2. Generates a semantic search query using the utility LLM
3. Searches the vector database for relevant memories
4. Incorporates found memories into the agent's prompt

#### Memory Storage Extensions

The `MemorizeMemories` extension in `_50_memorize_fragments.py` stores important information from conversations:

```python
class MemorizeMemories(Extension):
    REPLACE_THRESHOLD = 0.9  # Replace memories above this similarity

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Start memorization in background
        asyncio.create_task(self.memorize(loop_data, log_item))
```

The memorization process:
1. Analyzes the full conversation history
2. Extracts key information using the utility LLM
3. Removes similar existing memories to prevent duplication
4. Stores new information in the memory database

#### History Management Extensions

The `OrganizeHistory` extension in `_10_organize_history.py` manages conversation history:

```python
class OrganizeHistory(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Start compression task if not already running
        task = asyncio.create_task(self.agent.history.compress())
        self.agent.set_data(DATA_NAME_TASK, task)
```

This process:
1. Compresses older parts of the conversation history
2. Maintains context while reducing token usage
3. Ensures efficient memory usage during long conversations

## Memory System In-Depth

### Vector Database Implementation

Agent Zero uses a custom implementation of FAISS (Facebook AI Similarity Search) for efficient similarity search. The implementation is extended in the `MyFaiss` class in `python/helpers/memory.py`:

```python
class MyFaiss(FAISS):
    # Override get_by_ids to handle both single IDs and lists
    def get_by_ids(self, ids: Sequence[str], /) -> List[Document]:
        return [self.docstore._dict[id] for id in (ids if isinstance(ids, list) else [ids]) if id in self.docstore._dict]

    async def aget_by_ids(self, ids: Sequence[str], /) -> List[Document]:
        return self.get_by_ids(ids)
```

The vector database supports:
- Embedding of text into vector representations
- Efficient similarity search using cosine distance
- Customizable similarity threshold filtering
- Document metadata for filtering and organization

### Memory Operations

The `Memory` class provides several key operations for memory management:

```python
class Memory:
    # Retrieve documents similar to a query
    async def search_similarity_threshold(
        self, query: str, limit: int, threshold: float, filter: str = ""
    ):
        # Implementation of similarity search with threshold

    # Delete documents similar to a query
    async def delete_documents_by_query(
        self, query: str, threshold: float, filter: str = ""
    ):
        # Implementation of document deletion by similarity

    # Insert new text into memory
    async def insert_text(self, text, metadata: dict = {}):
        # Implementation of text insertion

    # Insert multiple documents at once
    async def insert_documents(self, docs: list[Document]):
        # Implementation of bulk document insertion
```

These operations allow the agent to:
1. Store and retrieve information efficiently
2. Maintain a clean memory space by removing duplicates
3. Filter memory by different criteria and areas
4. Maintain metadata for advanced memory operations

### Memory Areas

The memory system organizes data into distinct areas through the `Area` enum:

```python
class Area(Enum):
    MAIN = "main"            # General purpose storage
    FRAGMENTS = "fragments"  # Conversation fragments
    SOLUTIONS = "solutions"  # Successful solutions
    INSTRUMENTS = "instruments"  # Available instruments
```

Each area serves a specific purpose:
- **MAIN**: Primary storage for direct user instructions and key facts
- **FRAGMENTS**: Automatically extracted information from conversations
- **SOLUTIONS**: Successful solutions to problems for future reference
- **INSTRUMENTS**: Information about available custom tools and scripts

### Memory Lifecycle

The memory system follows a lifecycle that includes:

1. **Initialization**:
   ```python
   @staticmethod
   async def get(agent: Agent):
       memory_subdir = agent.config.memory_subdir or "default"
       if Memory.index.get(memory_subdir) is None:
           # Initialize new vector database
           db = Memory.initialize(...)
           # Preload knowledge if configured
           await wrap.preload_knowledge(...)
       else:
           # Return existing memory instance
           return Memory(...)
   ```

2. **Knowledge Preloading**:
   ```python
   async def preload_knowledge(self, log_item: LogItem | None, kn_dirs: list[str], memory_subdir: str):
       # Load knowledge documents into memory
   ```

3. **Memory Operations** during conversation:
   - Memory recall through extension system
   - Memory storage of new information
   - Automatic deduplication and organization

4. **Persistence**:
   ```python
   def _save_db(self):
       # Save vector database to disk
   ```

This lifecycle ensures that:
- Memory persists between sessions
- Knowledge is accessible from the start
- New information is properly integrated
- Memory remains efficient and relevant over time

## History System

Agent Zero employs a sophisticated history management system in `python/helpers/history.py` that optimizes memory usage while preserving context for long conversations. The system dynamically compresses older parts of conversation history while maintaining important information.

### History Structure

The history system organizes messages into a hierarchical structure:

```python
class History(Record):
    def __init__(self, agent):
        self.bulks: list[Bulk] = []       # Oldest, most compressed messages
        self.topics: list[Topic] = []     # Older topics, may be summarized
        self.current = Topic(history=self) # Current active topic
        self.agent: Agent = agent
```

This three-tier structure provides:
- **Current Topic**: Active conversation segment with full detail
- **Topics**: Previous conversation segments that may be summarized
- **Bulks**: Oldest conversation parts, compressed into summaries

Messages are organized into `Topic` objects, which can be summarized and eventually merged into `Bulk` objects for maximum compression.

### Compression Algorithm

The history compression algorithm works in multiple stages:

```python
async def compress(self):
    compressed = False
    while True:
        curr, hist, bulk = (
            self.get_current_topic_tokens(),
            self.get_topics_tokens(),
            self.get_bulks_tokens(),
        )
        total = get_ctx_size_for_history()
        ratios = [
            (curr, CURRENT_TOPIC_RATIO, "current_topic"),
            (hist, HISTORY_TOPIC_RATIO, "history_topic"),
            (bulk, HISTORY_BULK_RATIO, "history_bulk"),
        ]
        ratios = sorted(ratios, key=lambda x: (x[0] / total) / x[1], reverse=True)
        # Proceed with compression based on which part exceeds its ratio
```

The algorithm:
1. Calculates token usage for each tier of history
2. Compares against configured ratio limits
3. Targets the most over-limit section for compression
4. Repeats until all sections are within limits or no further compression is possible

Compression follows a progressive strategy:
1. **Large Message Compression**: First, oversized individual messages are summarized
2. **Topic Summarization**: Entire topics are summarized into concise representations
3. **Bulk Merging**: Multiple bulk summaries are merged into a single summary
4. **Bulk Removal**: As a last resort, the oldest bulk is removed completely

### Message Organization

Messages in Agent Zero's history system are organized into different record types:

```python
class Message(Record):
    def __init__(self, ai: bool, content: MessageContent):
        self.ai = ai
        self.content = content
        self.summary: MessageContent = ""
```

```python
class Topic(Record):
    def __init__(self, history: "History"):
        self.messages: list[Message] = []
        self.summary = ""
        self.history = history
```

```python
class Bulk(Record):
    def __init__(self, history: "History"):
        self.records: list[Record] = []
        self.summary = ""
        self.history = history
```

This hierarchy creates a flexible system where:
- Individual messages can be summarized when they exceed size thresholds
- Groups of messages (topics) can be summarized into concise representations
- Summaries of topics can be further condensed into bulk summaries

### Token Management

The history system carefully manages token usage to optimize context window utilization:

```python
# Constants controlling the allocation of tokens
CURRENT_TOPIC_RATIO = 0.5    # Current topic can use 50% of the context
HISTORY_TOPIC_RATIO = 0.3    # Previous topics can use 30% of the context
HISTORY_BULK_RATIO = 0.2     # Bulk summaries can use 20% of the context
```

These ratios ensure that:
1. The current conversation receives the majority of context space
2. Recent topics receive substantial representation
3. Older, compressed history still provides background information

The system regularly checks token usage:

## Code Execution System

The Code Execution System in Agent Zero provides a secure and flexible environment for executing code in various runtimes, including Python, Node.js, and shell commands.

### Runtime Environments

The system supports multiple runtime environments:

```python
if runtime == "python":
    response = await self.execute_python_code(self.args["code"])
elif runtime == "nodejs":
    response = await self.execute_nodejs_code(self.args["code"])
elif runtime == "terminal":
    response = await self.execute_terminal_command(self.args["code"])
```

Each runtime environment is handled differently:

1. **Python Runtime**: Uses IPython to execute Python code with enhanced REPL capabilities
   ```python
   async def execute_python_code(self, code: str, reset: bool = False):
       escaped_code = shlex.quote(code)
       command = f"ipython -c {escaped_code}"
       return await self.terminal_session(command, reset)
   ```

2. **Node.js Runtime**: Uses a custom VM-based evaluator script for Node.js code execution
   ```python
   async def execute_nodejs_code(self, code: str, reset: bool = False):
       escaped_code = shlex.quote(code)
       command = f"node /exe/node_eval.js {escaped_code}"
       return await self.terminal_session(command, reset)
   ```

3. **Terminal Runtime**: Executes raw shell commands
   ```python
   async def execute_terminal_command(self, command: str, reset: bool = False):
       return await self.terminal_session(command, reset)
   ```

The Node.js evaluator (`node_eval.js`) provides a sandboxed environment with proper error handling:

```javascript
const wrappedCode = `
  (async function() {
    try {
      const __result__ = await eval(${JSON.stringify(code)});
      if (__result__ !== undefined) console.log('Out[1]:', __result__);
    } catch (error) {
      console.error(error);
    }
  })();
`;
```

### Shell Session Management

The code execution system manages shell sessions through two distinct implementations:

1. **LocalInteractiveSession**: For executing code in the local environment
   ```python
   class LocalInteractiveSession:
       def __init__(self):
           self.process = None
           self.full_output = ''

       async def connect(self):
           # Start a new subprocess with the appropriate shell for the OS
           if sys.platform.startswith('win'):
               # Windows
               self.process = subprocess.Popen(['cmd.exe'], ...)
           else:
               # macOS and Linux
               self.process = subprocess.Popen(['/bin/bash'], ...)
   ```

2. **SSHInteractiveSession**: For executing code in remote environments
   ```python
   class SSHInteractiveSession:
       def __init__(self, log, host, port, username, password):
           self.log = log
           self.host = host
           self.port = port
           self.username = username
           self.password = password
           self.client = None
           self.shell = None
           self.full_output = ''
   ```

Both session types implement a common interface:
- `connect()`: Establishes the shell session
- `close()`: Terminates the session
- `send_command(command)`: Sends a command to the shell
- `read_output(timeout, reset_full_output)`: Reads and returns output

### Docker Integration

For enhanced security, the code execution system can run within a Docker container:

```python
async def prepare_state(self, reset=False):
    # initialize docker container if execution in docker is configured
    if self.agent.config.code_exec_docker_enabled:
        docker = DockerContainerManager(
            logger=self.agent.context.log,
            name=self.agent.config.code_exec_docker_name,
            image=self.agent.config.code_exec_docker_image,
            ports=self.agent.config.code_exec_docker_ports,
            volumes=self.agent.config.code_exec_docker_volumes,
        )
        docker.start_container()
    else:
        docker = None
```

The `DockerContainerManager` handles container lifecycle:
```python
def start_container(self) -> None:
    # Check if container exists
    existing_container = None
    for container in self.client.containers.list(all=True):
        if container.name == self.name:
            existing_container = container
            break

    # Start existing or create new
    if existing_container:
        if existing_container.status != 'running':
            existing_container.start()
            self.container = existing_container
            time.sleep(2)  # Helps to get SSH ready
        else:
            self.container = existing_container
    else:
        self.container = self.client.containers.run(
            self.image,
            detach=True,
            ports=self.ports,
            name=self.name,
            volumes=self.volumes,
        )
        time.sleep(5)  # Helps to get SSH ready
```

### Code Execution Security

The system implements multiple security layers:

1. **Command Sanitization**: Shell commands are properly escaped
   ```python
   escaped_code = shlex.quote(code)
   ```

2. **Container Isolation**: Code can be executed in a Docker container
   ```python
   config.code_exec_docker_enabled = True
   ```

3. **Output Monitoring**: Long-running processes can be monitored and terminated
   ```python
   async def get_terminal_output(
       self, wait_with_output=5, wait_without_output=60
   ):
       # Implements timeout logic
   ```

4. **Reset Capability**: Runaway processes can be terminated
   ```python
   async def reset_terminal(self):
       # Implements process termination
   ```

## Knowledge System

The Knowledge System in Agent Zero provides a comprehensive framework for acquiring, storing, retrieving, and utilizing knowledge from various sources. It enables agents to access both internal knowledge bases and external information sources.

### Search Architecture

The knowledge system architecture consists of multiple layers:

1. **Vector Search**: FAISS-based similarity search for efficient retrieval
2. **Document Query**: System for analyzing and extracting information from documents
3. **Web Search**: Integration with external search providers
4. **Memory Integration**: Connection to the agent's memory system

These components work together to provide a unified knowledge retrieval mechanism:

```python
class DocumentQueryStore:
    """
    FAISS Store for document query results.
    Manages documents identified by URI for storage, retrieval, and searching.
    """

    # Default chunking parameters
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 100

    # Cache for initialized stores
    _stores: dict[str, "DocumentQueryStore"] = {}
```

### Document Query System

The Document Query System (`python/helpers/document_query.py`) provides capabilities for:

1. **Document Loading**: Loading documents from various sources
   ```python
   # Supports multiple document types
   from langchain_community.document_loaders import AsyncHtmlLoader
   from langchain_community.document_loaders.text import TextLoader
   from langchain_community.document_loaders.pdf import PyMuPDFLoader
   ```

2. **Text Processing**: Chunking and embedding text for efficient storage and retrieval
   ```python
   text_splitter = RecursiveCharacterTextSplitter(
       chunk_size=self.DEFAULT_CHUNK_SIZE,
       chunk_overlap=self.DEFAULT_CHUNK_OVERLAP
   )
   chunks = text_splitter.split_text(text)
   ```

3. **Document Storage**: Vector-based storage with metadata
   ```python
   def _initialize_new_vectorstore(self):
       """Initialize a new vector store."""
       dimension = len(self.embeddings.embed_query("test"))
       index = faiss.IndexFlatIP(dimension)
       self.vectorstore = FAISS(
           embedding_function=self.embeddings,
           index=index,
           docstore=InMemoryDocstore(),
           index_to_docstore_id={},
           distance_strategy=DistanceStrategy.COSINE,
       )
   ```

4. **Similarity Search**: Retrieving documents based on semantic similarity
   ```python
   async def search_documents(self, query: str, limit: int = 10, threshold: float = 0.5) -> List[Document]:
       # Implementation of similarity search with threshold filtering
   ```

The system includes specialized handling for different document types:
```python
def handle_pdf_document(self, document: str, scheme: str) -> str:
    # PDF-specific processing

def handle_html_document(self, document: str, scheme: str) -> str:
    # HTML-specific processing

def handle_image_document(self, document: str, scheme: str) -> str:
    # Image-specific processing using OCR
```

### Memory Integration

The Knowledge System integrates with the Memory System:

```python
async def document_qa(self, document_uri: str, questions: Sequence[str]) -> Tuple[bool, str]:
    """
    Extract information from a document by asking specific questions.
    Uses the agent's language model to generate answers based on document content.
    """
    # Retrieves document from memory
    # Processes document content
    # Uses LLM to answer questions about the document
```

This integration allows:
1. Knowledge to be stored in long-term memory
2. Relevant information to be retrieved based on the current context
3. New information to enhance the agent's knowledge base

### Search Providers

The system integrates with multiple search providers:

1. **SearxNG**: Self-hosted search engine
   ```python
   class SearxNGSearch:
       # Implementation of SearxNG search
   ```

2. **DuckDuckGo**: Privacy-focused search engine
   ```python
   class DuckDuckGoSearch:
       # Implementation of DuckDuckGo search
   ```

3. **Perplexity**: AI-powered search
   ```python
   class PerplexitySearch:
       # Implementation of Perplexity search
   ```

Each provider is wrapped in a consistent interface that handles:
- Query formatting
- Rate limiting
- Error handling
- Result parsing

## RFC (Remote Function Call) System

The RFC System enables secure remote execution of functions between different components of Agent Zero, allowing for distributed processing and secure API access.

### RFC Architecture

The RFC system follows a simple, secure architecture:

```python
import importlib
import inspect
import json
from typing import Any, TypedDict
import aiohttp
from python.helpers import crypto
from python.helpers import dotenv

# Remote Function Call library
# Call function via http request
# Secured by pre-shared key
```

The system is built around two core data structures:

```python
class RFCInput(TypedDict):
    module: str
    function_name: str
    args: list[Any]
    kwargs: dict[str, Any]

class RFCCall(TypedDict):
    rfc_input: str
    hash: str
```

These structures enable:
1. **Structured Function Calls**: Clear specification of function name and parameters
2. **Security**: Hash-based verification of call integrity
3. **Flexibility**: Support for any function in any module

### Function Call Flow

The RFC system implements a complete flow for remote function calls:

1. **Call Preparation**: Preparing the function call with inputs
   ```python
   async def call_rfc(
       url: str, password: str, module: str, function_name: str, args: list, kwargs: dict
   ):
       input = RFCInput(
           module=module,
           function_name=function_name,
           args=args,
           kwargs=kwargs,
       )
       call = RFCCall(
           rfc_input=json.dumps(input), hash=crypto.hash_data(json.dumps(input), password)
       )
       result = await _send_json_data(url, call)
       return result
   ```

2. **Call Verification**: Verifying the call's security hash
   ```python
   async def handle_rfc(rfc_call: RFCCall, password: str):
       if not crypto.verify_data(rfc_call["rfc_input"], rfc_call["hash"], password):
           raise Exception("Invalid RFC hash")
       # Process call
   ```

3. **Function Execution**: Dynamic loading and execution of the requested function
   ```python
   async def _call_function(module: str, function_name: str, *args, **kwargs):
       func = _get_function(module, function_name)
       if inspect.iscoroutinefunction(func):
           return await func(*args, **kwargs)
       else:
           return func(*args, **kwargs)
   ```

4. **Result Handling**: Packaging and returning results securely
   ```python
   async def _send_json_data(url: str, data):
       async with aiohttp.ClientSession() as session:
           async with session.post(url, json=data) as response:
               if response.status == 200:
                   result = await response.json()
                   return result
               else:
                   error = await response.text()
                   raise Exception(error)
   ```

### Security Mechanisms

The RFC system implements robust security mechanisms:

1. **Pre-shared Key Authentication**: Uses shared secrets for authentication
   ```python
   hash=crypto.hash_data(json.dumps(input), password)
   ```

2. **Hash Verification**: Verifies data integrity and authenticity
   ```python
   if not crypto.verify_data(rfc_call["rfc_input"], rfc_call["hash"], password):
       raise Exception("Invalid RFC hash")
   ```

3. **Module Access Control**: Controls which modules can be accessed
   ```python
   def _get_function(module: str, function_name: str):
       # import module
       imp = importlib.import_module(module)
       # get function by the name
       func = getattr(imp, function_name)
       return func
   ```

### Integration with MCP System

The RFC system integrates with the MCP (Model Control Protocol) system to provide secure access to model providers:

```python
class MCPConfig(BaseModel):
    servers: List[MCPServer] = Field(default_factory=list[MCPServer])

    # Singleton instance
    __instance: ClassVar[Any] = PrivateAttr(default=None)
    __initialized: ClassVar[bool] = PrivateAttr(default=False)
```

MCP provides:
1. Remote access to LLM providers
2. Tool execution across systems
3. Secure exchange of model inputs and outputs

The MCP system extends RFC with specialized protocols:
1. **SSE (Server-Sent Events)**: For streaming responses
   ```python
   sse_read_timeout: float = Field(default=60.0 * 5.0)
   ```

2. **StdIO**: For local binary communication
   ```python
   from mcp.client.stdio import stdio_client
   ```

## Development Guidelines

### Python Best Practices

The Agent Zero codebase follows a set of Python development practices to ensure maintainability, performance, and reliability:

1. **Type Annotations**: Extensive use of type hints for better IDE support and runtime checking
   ```python
   from typing import List, Dict, Optional, Any, Union, Literal, Annotated, ClassVar, cast
   ```

2. **Asynchronous Programming**: Structured async/await patterns for efficient I/O handling
   ```python
   async def execute(self, **kwargs):
       # Asynchronous implementation
   ```

3. **Error Handling**: Comprehensive exception management with contextual information
   ```python
   try:
       # Operation
   except Exception as e:
       # Structured error handling with context
   ```

4. **Resource Management**: Proper cleanup of resources using context managers
   ```python
   async with AsyncExitStack() as stack:
       # Resource management
   ```

5. **Singleton Pattern**: Efficient object reuse for expensive resources
   ```python
   @classmethod
   def get_instance(cls) -> "MCPConfig":
       if cls.__instance is None:
           cls.__instance = cls(servers_list=[])
       return cls.__instance
   ```

### API Development Conventions

The API development in Agent Zero follows a consistent pattern:

1. **Handler Registration**: All API handlers are registered in `run_ui.py`
   ```python
   # Register API endpoints
   api.register_blueprint(app)
   ```

2. **Handler Structure**: Each handler inherits from the base `ApiHandler` class
   ```python
   class Message(ApiHandler):
       async def process(self, input: dict, request: Request) -> dict | Response:
           # Implementation
   ```

3. **Authentication Control**: Handlers can specify authentication requirements
   ```python
   @classmethod
   def requires_auth(cls) -> bool:
       return True  # Requires authentication
   ```

4. **Input Processing**: Standardized input parsing and validation
   ```python
   # Extract parameters from request
   text = input.get("text", "")
   ctxid = input.get("context", "")
   ```

5. **Response Formatting**: Consistent response structure
   ```python
   return {
       "message": result,
       "context": context.id,
   }
   ```

### Frontend Development Conventions

When developing frontend components for Agent Zero, follow these conventions to ensure consistency and maintainability:

#### HTML/CSS/JavaScript Organization

1. **Component Isolation**
   - Each component should be self-contained with its JavaScript, CSS, and HTML grouped together
   - For Alpine.js components, register using `Alpine.data()` to create reusable components

2. **CSS Class Naming Conventions**
   - Use a BEM-like approach (Block, Element, Modifier) for CSS class naming
   - Prefix component-specific classes with the component name (e.g., `chat-message`, `settings-tab`)
   - Use kebab-case for class names (e.g., `chat-message-content` not `chatMessageContent`)

3. **Alpine.js Best Practices**
   - Keep Alpine.js component logic close to the HTML it manipulates
   - Use `x-init` for initialization code
   - Use `x-data` for component state management
   - Prefer declarative approaches over imperative when possible

#### Critical Styling Guidelines

1. **NEVER Modify Core UI Styles Without Approval**
   - DO NOT change the styling of core UI elements like sections, buttons, or modal dialogs without explicit design approval
   - The `.section` style should have a red border and NO background color that differs from the parent element
   - Modal buttons must maintain their established styling patterns across all dialog types
   - Any changes to global UI styles require UX team review and explicit approval

2. **Respect Established Visual Patterns**
   - New components must match the established visual language of the application
   - If you believe current styles are inadequate, consult with the UX team instead of making changes
   - Consistency across the UI is a higher priority than component-specific improvements

#### Tab System Integration Guidelines

When creating new tabs for the settings modal or other tabbed interfaces, strictly follow these guidelines:

1. **DOM Structure Consistency**
   - Each tab content MUST follow the same structural pattern as existing tabs
   - Use the standard `.section` class for main container elements, not custom container classes
   - Include both a `.section-title` and `.section-description` in each section
   - Example structure:
   ```html
   <div x-show="activeTab === 'your_tab_id'">
     <div id="section-your-tab-id" class="section">
       <div class="section-title">Your Tab Title</div>
       <div class="section-description">Your tab description text here.</div>
       <!-- Tab-specific content here -->
     </div>
   </div>
   ```

2. **CSS Namespacing**
   - All component-specific CSS classes MUST be prefixed with the component name
   - Example: For a "calendar" component, use `calendar-container`, `calendar-events`, etc.
   - This prevents naming conflicts and clarifies which styles belong to which component
   - NEVER use generic class names (like `container`, `list`, `item`) without a component prefix

3. **Avoiding Special Cases**
   - DO NOT create special styling rules that only apply to your component
   - DO NOT override or duplicate standard structural styles
   - DO NOT create conditional logic specifically targeting your component ID
   - Leverage existing styles and patterns whenever possible
   - Contact the UX team if standard patterns don't meet your requirements

4. **UI Component State Management**
   - Initialize component data in `x-data` or an Alpine.js component
   - Ensure proper initialization in both creation and edit scenarios
   - Handle loading states with consistent visual indicators
   - Follow the established pattern for form validation

#### JavaScript Code Style

1. **ES6+ Features**
   - Use ES6+ features such as arrow functions, destructuring, template literals, etc.
   - Avoid jQuery when native DOM methods will suffice

2. **Error Handling**
   - Implement proper try/catch blocks for API calls and error-prone operations
   - Display user-friendly error messages via the toast notification system
   - Log detailed errors to console for debugging purposes

3. **Performance Considerations**
   - Minimize DOM manipulations
   - Use event delegation where appropriate
   - Debounce or throttle event handlers for resource-intensive operations

#### Accessibility

1. **Semantic HTML**
   - Use appropriate HTML elements (`button` for actions, `a` for navigation, etc.)
   - Include proper ARIA attributes when necessary
   - Ensure proper heading hierarchy (h1, h2, h3, etc.)

2. **Keyboard Navigation**
   - Ensure all interactive elements are keyboard accessible
   - Implement proper focus management for modals and dialogs
   - Test tab order to ensure logical navigation

3. **Screen Reader Support**
   - Provide alt text for images
   - Use aria-live regions for dynamic content
   - Test with screen readers to ensure compatibility

#### Mobile Responsiveness

1. **Mobile-first Approach**
   - Design for mobile first, then enhance for larger screens
   - Use flexbox and CSS grid for layouts instead of absolute positioning
   - Ensure touch targets are at least 44×44 pixels

2. **Media Queries**
   - Use standard breakpoints defined in CSS variables
   - Adjust layouts at appropriate breakpoints
   - Test on various device sizes

#### Testing

1. **Cross-browser Testing**
   - Test on Chrome, Firefox, Safari, and Edge (latest versions)
   - Ensure layouts render correctly across browsers

2. **Responsive Testing**
   - Test on various screen sizes
   - Verify functionality in both portrait and landscape orientations

3. **Functionality Testing**
   - Verify all interactive elements work as expected
   - Test with keyboard navigation
   - Ensure proper error handling and edge cases

### API Authentication and Access Control

API endpoints in Agent Zero implement a layered authentication approach:

1. **Authentication Types**: Several authentication mechanisms are available:
   ```python
   @classmethod
   def requires_auth(cls) -> bool:
       return True  # Standard user authentication

   @classmethod
   def requires_api_key(cls) -> bool:
       return False  # API key-based authentication

   @classmethod
   def requires_loopback(cls) -> bool:
       return False  # Local-only access restriction
   ```

2. **Authentication Selection**: For web UI endpoints, prefer `requires_auth()` over `requires_loopback()`
   ```python
   # Correct pattern for UI-accessible API endpoints
   @classmethod
   def requires_auth(cls) -> bool:
       return True
   ```

3. **Loopback Restriction**: Only use `requires_loopback()` for internal system endpoints not meant for web UI access
   ```python
   # For internal system operations only
   @classmethod
   def requires_loopback(cls) -> bool:
       return True
   ```

4. **Authentication Decoration**: Authentication is applied in `run_ui.py` during handler registration:
   ```python
   def register_api_handler(app, handler: type[ApiHandler]):
       if handler.requires_loopback():
           @requires_loopback
           async def handle_request():
               return await instance.handle_request(request=request)
       elif handler.requires_auth():
           @requires_auth
           async def handle_request():
               return await instance.handle_request(request=request)
   ```

### Task Scheduler Implementation

The task scheduler system implements scheduled task execution for Agent Zero:

1. **Core Components**:
   - Backend task storage and execution system
   - Frontend UI for task management in settings modal
   - API endpoints for task operations

2. **API Endpoints**:
   ```python
   # Task management endpoints
   class SchedulerTasksList(ApiHandler):
       @classmethod
       def requires_auth(cls) -> bool:
           return True

   class SchedulerTaskSave(ApiHandler):
       @classmethod
       def requires_auth(cls) -> bool:
           return True

   class SchedulerTaskDelete(ApiHandler):
       @classmethod
       def requires_auth(cls) -> bool:
           return True
   ```

3. **UI Integration**: The task scheduler UI integrates with the settings modal using the standard section structure:
   ```html
   <!-- Task Scheduler Tab Integration - CORRECT IMPLEMENTATION -->
   <div x-show="activeTab === 'task_scheduler'">
     <div id="section-task-scheduler" class="section">
       <div class="section-title">Task Scheduler</div>
       <div class="section-description">Manage scheduled tasks and automated processes.</div>

       <div x-data="taskScheduler" x-init="$watch('activeTab', val => { if(val === 'task_scheduler') forceLoadTasks(); })">
         <!-- Task scheduler content with scheduler- prefixed classes -->
         <div class="scheduler-task-list-container">
           <!-- Task list content -->
         </div>

         <div class="scheduler-task-form">
           <!-- Task form content -->
         </div>
       </div>
     </div>
   </div>
   ```

4. **CRITICAL: DOM Structure Requirements**:
   - ALWAYS use the standard `.section` class for the main container, NOT custom container classes
   - Include both `.section-title` and `.section-description` elements
   - DO NOT create special styling that only applies to the task scheduler tab
   - The red border and other standard section styling will be applied automatically

5. **CSS Class Naming Convention**:
   - ALWAYS use the `scheduler-` prefix for all task scheduler specific CSS classes (e.g., `scheduler-task-list`, `scheduler-form-group`)
   - This prevents naming conflicts with other components
   - Examples of correct class naming:
     - `scheduler-task-controls`
     - `scheduler-left-controls`
     - `scheduler-task-filter`
     - `scheduler-status-badge`

6. **Alpine.js Component**: Task scheduler UI operations are managed by a dedicated component:
   ```javascript
   Alpine.data('taskScheduler', function() {
     return {
       // State management
       tasks: [],
       isLoading: true,
       showNewTaskForm: false,
       editingTask: null,

       // Data loading
       async loadTasks() {
         try {
           const response = await fetch('/api/scheduler_tasks_list');
           // Process response
         } catch (error) {
           // Handle errors properly
         }
       },

       // Task operations
       async submitForm() { /* Task creation/update */ },
       async deleteTask(task) { /* Task deletion */ }
     };
   });
   ```

7. **Common Integration Challenges**:
   - Properly integrate with parent component context using `x-show` and `$watch`
   - Use correct API endpoint paths with `/api/` prefix
   - Implement proper error handling for API responses
   - Avoid duplicate component initialization
   - Handle component visibility reactively rather than imperatively
   - Never create special-case HTML structure or styling specifically for the task scheduler tab

### Context Retention and Development Safeguards

#### Critical Context Tracking Requirements

1. **CONTAINERIZED ENVIRONMENT AWARENESS**
   - **ALWAYS ASSUME** the application runs in a containerized environment
   - All changes must account for container limitations and lifecycle
   - Container restarts will reset file changes not persisted to volumes
   - **NEVER** make changes outside mounted volumes without explicit user confirmation

2. **Development Context Persistence**
   - Create and maintain a `.context.md` file in the project root to track important context
   - Update this file with critical information about the application state, architecture, and recent changes
   - Before making any significant changes, ALWAYS review this file
   - Example structure:
   ```markdown
   # Development Context

   ## Environment
   - Running in container: YES
   - Persistent volumes: /app/data, /app/config
   - Container restarts: Files outside volumes will be lost

   ## Architecture Notes
   - Alpine.js is used for all UI components
   - CSS naming follows component-prefixed scheme
   - Custom dialog system depends on modal-controller.js

   ## Recent Changes
   - [Date] Modified authentication flow
   - [Date] Updated task scheduler component
   ```

3. **Change Tracking Discipline**
   - Document ALL changes in a standardized format in `.context.md`
   - Include rationale, affected components, and potential side effects
   - Use the phrase "CONTAINER SENSITIVE" to mark changes that interact with container boundaries

#### Safeguards Against Context Loss

1. **Required Pre-Action Checklist**
   - Before making any UI changes:
     - ✓ Verify if the application runs in a container
     - ✓ Check which paths are persistent vs ephemeral
     - ✓ Review the existing component structure before modifying it
     - ✓ Confirm whether components are isolated or share class names

2. **Warning Flags Protocol**
   - Create a `.warning-flags` file that contains critical facts to remember
   - Review this file before EVERY significant change
   - Implement a "fact-recall" step before modifying any structural elements
   - Example warning flags:
   ```
   CONTAINER_ENVIRONMENT=TRUE
   CSS_PREFIX_REQUIRED=TRUE
   ALPINE_COMPONENTS=TRUE
   PERSIST_ONLY_TO_VOLUMES=TRUE
   ```

3. **Side-Effect Documentation Requirement**
   - Document all potential side effects of changes:
   ```markdown
   ## Change: Modify task scheduler CSS

   ### Potential Side Effects
   - May affect other components using similar class names
   - Container restart will reset if not in persistent volume
   - May break mobile responsiveness if not tested
   ```

4. **Explicit Context Reminders**
   - Begin all development sessions by writing out critical facts about the system
   - Create visual reminders in dev environment about containerization
   - Use sticky notes (virtual or physical) for critical context that must not be forgotten

#### Memory Failure Prevention

1. **Progressive Disclosure Development**
   - Divide complex changes into small, documented steps
   - Document the purpose and impact of each step before executing it
   - Verify each step's completion before proceeding to the next
   - Maintain a trail of what was done and why

2. **Contextual Comments**
   - Add comments in code that explain WHY choices were made, not just WHAT was done
   - Include references to architectural decisions or constraints
   - Example:
   ```javascript
   // NOTE: This component uses Alpine.js for state management
   // CONTAINER: Files saved here will persist across restarts
   // WARNING: Shared class names with user-settings component
   ```

3. **Development Journal**
   - Maintain a chronological log of development decisions
   - Record assumptions made during development
   - Document the reasoning behind architectural choices
   - Link decisions to specific requirements or constraints

#### Emergency Response Protocol

1. **Context Restoration Process**
   - If context is lost, follow this restoration procedure:
     1. Review `.context.md` and `.warning-flags`
     2. Examine recent commits or changes
     3. Inspect affected components before modifying
     4. Consult with other developers if available

2. **Rollback Procedures**
   - Document clear steps to revert changes if they cause issues
   - Maintain backups of critical configuration files before changes
   - Test rollback procedures before implementing major changes

3. **Regular Context Validation**
   - Periodically review and verify critical context understanding
   - Challenge assumptions about the application architecture
   - Confirm environment details remain accurate

By rigorously following these safeguards, developers can prevent critical failures caused by context loss, especially in containerized environments where file persistence behaviors may differ from typical development workflows.

### AI Assistant Scratchpad Protocol

#### MANDATORY Scratchpad Maintenance

1. **Dedicated Scratchpad File**
   - AI assistants MUST maintain a dedicated scratchpad file at `.cursor/notebooks/ai_assistant_scratchpad.md`
   - This file MUST be updated during EVERY development session
   - The scratchpad serves as persistent memory to prevent critical context loss
   - AI assistants without access to this scratchpad MUST create it immediately

2. **Scratchpad Structure Requirements**
   - The scratchpad MUST contain the following sections:
     - **Active Context**: Current development focus and critical facts
     - **Recent Activity**: Chronological log of recent changes
     - **Pending Considerations**: Issues or ideas requiring future attention
     - **Component Structure Notes**: Details about components being modified
     - **Container Awareness**: Explicit notes about containerized environment
   - Example structure:
   ```markdown
   # AI Assistant Scratchpad

   ## Active Context
   - Application runs in CONTAINERIZED ENVIRONMENT
   - Working on: Task scheduler UI component
   - Critical files: index.html, settings.css, task_scheduler.js
   - Current issues: Schedule display showing undefined values

   ## Recent Activity
   - [Date/Time] Fixed task scheduler tab structure
   - [Date/Time] Restored left panel menu display
   - [Date/Time] Added safety checks to speech detection

   ## Pending Considerations
   - API endpoint response format may need validation
   - Mobile view requires testing after changes
   - Consider refactoring schedule display logic

   ## Component Structure Notes
   - Task scheduler uses standard section pattern
   - All CSS classes use scheduler- prefix
   - Alpine.js component manages state
   - Standard button styling must be preserved

   ## Container Awareness
   - Files in /app/data and /app/config persist after restart
   - UI changes in index.html and CSS files need persistence check
   - Container restart will reset non-persistent files
   ```

3. **Scratchpad Integration with Development Workflow**
   - Review scratchpad at the START of every development session
   - Update scratchpad BEFORE ending any development session
   - Reference scratchpad DURING complex implementation tasks
   - Cross-reference scratchpad with `.context.md` and `.warning-flags` files

4. **Scratchpad Update Requirements**
   - Document ALL meaningful changes made during development
   - Record reasoning behind architectural and implementation decisions
   - Note any discovered constraints or patterns in the codebase
   - Track issues encountered and their resolutions
   - Maintain awareness of containerized environment implications

#### CRITICAL Scratchpad Warning Protocol

1. **Memory Failure Prevention**
   - The scratchpad is the PRIMARY defense against AI assistant memory failures
   - AI assistants MUST assume they will lose context between sessions
   - The scratchpad should be written assuming a DIFFERENT AI assistant will continue the work
   - Use EXPLICIT, DETAILED notes rather than relying on recall

2. **Warning Section Requirements**
   - Include a dedicated WARNING section for critical facts
   - Use clear, unambiguous language for warnings
   - Highlight warnings visually using markdown formatting
   - Example:
   ```markdown
   ## ⚠️ CRITICAL WARNINGS ⚠️

   - **CONTAINER ENVIRONMENT**: Application runs in a container! Changes outside mounted volumes WILL BE LOST!
   - **CSS NAMING**: ALWAYS use scheduler- prefix for task scheduler CSS classes
   - **UI PATTERN**: NEVER modify the standard section structure
   - **BUTTON STYLING**: NEVER change global button styles without approval
   ```

3. **Failure Recovery Protocol**
   - If context is lost, AI assistants MUST:
     1. Immediately review the scratchpad file
     2. Cross-reference with `.context.md` and `.warning-flags`
     3. Acknowledge the context loss explicitly to the user
     4. Rebuild context from documented notes before proceeding
     5. Verify understanding with the user before making changes

#### Scratchpad Maintenance Schedule

1. **Regular Update Requirements**
   - Update scratchpad at the BEGINNING of each development session
   - Update scratchpad after EACH significant change or decision
   - Update scratchpad at the END of each development session
   - Perform COMPLETE scratchpad reviews weekly

2. **Critical Update Triggers**
   - ALWAYS update scratchpad when:
     - Making changes to UI structure or styling
     - Modifying containerized environment settings
     - Implementing features that span multiple components
     - Discovering new architectural patterns
     - Encountering unexpected behavior or bugs
     - Receiving clarification from the user about the system

3. **Scratchpad Review Protocol**
   - Begin each session with a thorough review of the scratchpad
   - Verify that all recorded facts remain accurate
   - Challenge assumptions documented in previous sessions
   - Update outdated information immediately
   - Sync scratchpad with `.context.md` when discrepancies are found

#### Implementation Reference Files

The following files established through this documentation MUST be used in conjunction with the scratchpad:

1. **`.context.md`**: Project-wide context file in root directory
   - Contains environment settings, architectural notes, and recent changes
   - Serves as authoritative source for application facts
   - Example: `/home/rafael/Workspace/Repos/rafael/a0-local/.context.md`

2. **`.warning-flags`**: Critical reminder flags in root directory
   - Contains boolean flags for critical facts to remember
   - Provides quick reference for essential guidelines
   - Example: `/home/rafael/Workspace/Repos/rafael/a0-local/.warning-flags`

3. **`ai_assistant_scratchpad.md`**: AI assistant's working notes
   - Contains detailed development logs and observations
   - Maintained by AI assistants across sessions
   - Located in `.cursor/notebooks/ai_assistant_scratchpad.md`

**IMPORTANT**: Failure to maintain these files, especially the scratchpad, is considered a CRITICAL ERROR. AI assistants MUST prioritize context retention above all other considerations to prevent destructive changes to the application.

## Deployment

### Docker Setup

Agent Zero is designed to be deployed as a Docker container:

```yaml
version: '3'
services:
  agent0:
    image: agent0:latest
    ports:
      - "8000:80"
      - "2222:22"
    volumes:
      - ./memory:/app/memory
      - ./knowledge:/app/knowledge
      - ./prompts:/app/prompts
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

The Docker setup provides:
1. **Isolated Environment**: Secure execution environment
2. **Port Mapping**: Accessible web UI and SSH
3. **Volume Mounting**: Persistent storage for memory, knowledge, and prompts
4. **Environment Configuration**: Easy configuration through environment variables

### Environment Configuration

Agent Zero can be configured through environment variables:

```bash
# Model Configuration
OPENAI_API_KEY=your_key_here
A0_CHAT_MODEL_PROVIDER=openai
A0_CHAT_MODEL_NAME=gpt-4o

# Authentication
A0_AUTH_LOGIN=admin
A0_AUTH_PASSWORD=password

# Code Execution
A0_CODE_EXEC_DOCKER_ENABLED=true
A0_CODE_EXEC_SSH_ENABLED=false

# Memory Configuration
A0_AGENT_MEMORY_SUBDIR=default
```

These variables can be:
1. Set in the `.env` file
2. Passed as Docker environment variables
3. Set in the system environment

The environment configuration provides a flexible way to adapt Agent Zero to different deployment scenarios and integrate with different model providers.

### API Development Conventions

#### Endpoint Structure
- **Backend API endpoints are implemented directly using the filename as the endpoint**, with no `/api/` prefix.
- For example, a Python file named `scheduler_tasks_list.py` in the `python/api` directory corresponds to the URL endpoint `/scheduler_tasks_list`.
- All API endpoints are registered automatically by the framework from files in the `python/api` directory.

#### Authentication
- API endpoints can require different types of authentication:
  - `requires_auth()`: Requires user authentication (default)
  - `requires_loopback()`: Requires local request (from the same machine)
  - `requires_api_key()`: Requires a valid API key

#### Implementation Pattern
API endpoints follow a consistent implementation pattern:

```python
from python.helpers.api import ApiHandler
from flask import Request, Response

class MyEndpoint(ApiHandler):
    @classmethod
    def requires_auth(cls):
        return True  # This endpoint requires authentication

    @classmethod
    def requires_loopback(cls):
        return False  # This endpoint allows non-local requests

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Process the request and return response
        return {"status": "success", "data": result}
```

#### Frontend API Access
When accessing API endpoints from frontend JavaScript:

```javascript
// Correct API endpoint access pattern
const response = await fetch('/scheduler_tasks_list');

// POST request example
const response = await fetch('/scheduler_task_save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task: taskData })
});
```

Do NOT use the `/api/` prefix in front of endpoint names. The endpoint URL should exactly match the filename of the API handler class.
