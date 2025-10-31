# Quickstart: InteractiveResponse + PromptBuilder

This guide shows how an agent can emit an InteractiveResponse (IR) that renders controls in a chat bubble and, on submit, either posts a Jinja-rendered prompt or dispatches a server-side tool call.

## Example A: Prompt callback (auto)

IR payload (returned by a tool):

```json
{
  "elements": [
    { "type": "text", "content": "Choose tone and length." },
    {
      "type": "select",
      "id": "tone",
      "label": "Tone",
      "options": [
        { "id": "t1", "label": "Professional", "value": "professional" },
        { "id": "t2", "label": "Friendly", "value": "friendly" }
      ]
    },
    { "type": "input_number", "id": "length", "label": "Length (words)", "value": 200, "min": 50, "max": 1000, "step": 50 },
    { "type": "checkbox", "id": "include_examples", "label": "Include examples", "value": true },
    { "type": "button", "id": "submit_main", "label": "Generate", "role": "submit", "submit_action_id": "generate" }
  ],
  "submit_behavior": "auto",
  "callback": { "kind": "prompt", "template": "Write a {{ tone }} summary (~{{ length }} words){% if include_examples %} with 2 examples{% endif %}." }
}
```

## Example C: No callback (default prompt fallback)

IR payload (no callback provided):

```json
{
  "elements": [
    { "type": "text", "content": "Choose options." },
    { "type": "select", "id": "tone", "options": [
      { "id": "t1", "label": "Professional", "value": "professional" },
      { "id": "t2", "label": "Friendly", "value": "friendly" }
    ]},
    { "type": "button", "id": "submit_main", "label": "Apply", "role": "submit" }
  ],
  "submit_behavior": "auto"
}
```

Behavior:
- Backend renders default template `prompts/iresponse/default.md.jinja`.
- `{{ variables }}` receives a fenced JSON block of the collected IR values.
- The surrounding text briefly explains these are the user’s choices from the IR dialog.
- Result is routed according to `submit_behavior` (auto/prefill).

Behavior:
- User submits → backend renders Jinja → new user message posted.
- Synthetic vars available: `tone_t1`, `tone_t2`, and `tone_selected` map.

## Example B: Tool callback

IR payload:

```json
{
  "elements": [
    { "type": "text", "content": "Refactor target and safety options." },
    {
      "type": "checklist",
      "id": "fixes",
      "options": [
        { "id": "imports", "label": "Fix imports" },
        { "id": "types", "label": "Fix types" },
        { "id": "dead", "label": "Remove dead code" }
      ]
    },
    { "type": "button", "id": "submit_tool", "label": "Refactor", "role": "submit", "submit_action_id": "refactor" }
  ],
  "callback": {
    "kind": "tool",
    "tool_name": "code_refactor",
    "args_template": "{\n  \"path\": \"src/\",\n  \"apply\": {\n    \"imports\": {{ fixes_selected.imports | default(false) | tojson }},\n    \"types\": {{ fixes_selected.types | default(false) | tojson }},\n    \"dead\": {{ fixes_selected.dead | default(false) | tojson }}\n  }\n}"
  }
}
```

Behavior:
- User submits → backend renders `args_template` → parses JSON → dispatches `code_refactor` tool with parsed args → logs result in history.
- IR freezes after successful dispatch; on parse/tool-not-found errors, stays interactive.

## Submission contract
 - POST `/iresponse/submit` (see `contracts/iresponse.yaml`)
 - Headers: `X-Idempotency-Key: <uuidv4>`
 - Body: `{ ir, values, submit_action_id }`
- For prompt+auto: returns `{ status: "posted", message_id }`
- For prompt+prefill: returns `{ status: "prefilled" }`
- For tool: returns `{ status: "dispatched", tool_name }`
- Errors: `{ status: "error", error: { code, message, details? } }`

Prefill UX: The rendered text is appended to any existing input content, focus moves to the input, and the caret is placed at the end (no selection).

## Jinja tips
- Synthetic booleans: `<id>_<optionId>` are convenient for `if` checks.
- Compound map: `<id>_selected[optionId]` allows direct lookups.
- Always validate presence with `|default(...)` where appropriate.
