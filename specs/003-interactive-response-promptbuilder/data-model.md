# Data Model: InteractiveResponse + PromptBuilder

Date: 2025-10-30
Branch: 003-interactive-response-promptbuilder

## Entities

### InteractiveResponse
- fields:
  - elements: Element[]
  - callback?: PromptCallback | ToolCallback
  - submit_behavior?: "auto" | "prefill"
- invariants:
  - Element ids unique within bubble
  - At least one `button` with `role="submit"`

### Element (base)
- fields: { type: string, id?: string, label?: string, value?: any, disabled?: boolean, required?: boolean, tooltip?: string, default?: any }

### Container
- fields: { type: "container", layout?: "horizontal"|"vertical", collapsed?: boolean, children: Element[] }
- note: layouts children only; does not change submission ordering

### Text
- fields: { type: "text", html?: boolean, content: string }
- constraints: safe HTML subset only (see spec FR-020)

### Button (submit)
- fields: { type: "button", id: string, label?: string, role: "submit", submit_action_id?: string, value?: "clicked" }

### Checkbox
- fields: { type: "checkbox", id: string, label?: string, value: boolean }

### Checklist
- fields: { type: "checklist", options: [ { id: string, label: string, value?: boolean, tooltip?: string } ] }
- submission:
  - variables: one per option (id→bool)
  - synthetic: `<id>_selected` map `{ [optionId]: bool }`

### Select
- fields: { type: "select", id: string, label?: string, options: [ { id: string, label: string, value: any, selected?: boolean } ], multi?: boolean }
- submission:
  - canonical `<id>`: scalar if single, array if multi
  - synthetic: `<id>_<optionId>` booleans; `<id>_selected` map

### Inputs
- input_text: { type: "input_text", id: string, value: string }
- input_number: { type: "input_number", id: string, value: number, min?: number, max?: number, step?: number }
- toggle: { type: "toggle", id: string, value: boolean }
- slider: { type: "slider", id: string, value: number, min?: number, max?: number, step?: number }

### PromptBuilder
- input: { template: string, variables: Record<string, any> }
- output: { text: string }
- errors: MissingVariableError (lists missing ids), TemplateSyntaxError

### Callback (union)
- PromptCallback: { kind: "prompt", template: string }
- ToolCallback: { kind: "tool", tool_name: string, args_template: string /* renders to JSON */ }

### SubmitRequest (API)
- fields:
  - ir: InteractiveResponse (as provided)
  - values: Record<string, any> (leaf control state)
  - submit_action_id?: string (from the button)
 - headers:
  - X-Idempotency-Key: string (UUIDv4)

### SubmitResponse (API)
- for kind=prompt + auto: { status: "posted", message_id: string }
- for kind=prompt + prefill: { status: "prefilled" }
- for kind=tool: { status: "dispatched", tool_name: string }
- for error: { status: "error", error: { code: string, message: string, details?: any } }

### Default Prompt Template (fallback)
- location: `prompts/iresponse/default.md.jinja` (configurable)
- required placeholder: `{{ variables }}`
- injection format: fenced JSON block of IR values (keys = element IDs and synthetic variables), preceded by one concise sentence explaining these are the user’s choices from the InteractiveResponse dialog.

## Validation Rules
- unique element ids within IR
- required fields enforced on client and server
- numeric ranges and steps validated
- safe HTML subset for text
- args_template must render to valid JSON object (tool callbacks)
- tool_name must exist in server tool registry

## State Transitions
- interactive → (submit success) → frozen (read-only)
- interactive → (submit error) → interactive + inline error(s)
