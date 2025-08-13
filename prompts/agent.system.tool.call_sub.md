### call_subordinate

#### Description
Use this tool to delegate work to one or more specialized subordinates identified by their settings profiles. Each subordinate runs in its own persistent background context. When you call this tool, it will start (or reuse) each subordinate’s background job, wait for all to complete, and return their results, each prefixed with the profile key.

- Maintains a mapping of spawned subordinates on the superior agent: `{ settings_profile -> subordinate_agent }`
- Spawns a subordinate for any settings profile that does not exist yet
- Optionally resets a settings profile to start a fresh subordinate
- Queues your message to each target subordinate and runs their monologues in background
- Waits for all tasks to complete and aggregates their responses as:
  - `[settings_profile]\n<response>`

#### Arguments
- `message` (string, required): What to send to the subordinate(s)
- `agent_profile` (string, optional): Single target settings profile. If omitted and `agent_profiles` not provided, defaults to the empty profile "" (default subordinate)
- `agent_profiles` (string|list, optional): Multiple target settings profiles as a comma-separated string or list of strings
- `attachments` (list[string], optional): Attachment URIs to pass along
- `reset` (boolean|string, optional): Set to `true` to replace the subordinate(s) for the given profile(s)

#### Guidance
- Describe the role, task, constraints, and expected output clearly in `message`.
- Delegate specific subtasks, not the entire project.
- Prefer the specialized settings profiles when appropriate; leave empty for the default profile.
- Subordinates should call the `subordinate_finish` tool when done to remove themselves from the registry and clean up their context.

#### Usage Examples

##### Single profile
```json
{
  "thoughts": [
    "I need a coder to refactor the module while I plan the integration."
  ],
  "tool_name": "call_subordinate",
  "tool_args": {
    "agent_profile": "coder",
    "message": "Refactor the payment service: extract DB ops, add retries, write a smoke test.",
    "attachments": [],
    "reset": false
  }
}
```

##### Multiple profiles
```json
{
  "thoughts": [
    "I will ask both the scientist and the coder for parallel inputs."
  ],
  "tool_name": "call_subordinate",
  "tool_args": {
    "agent_profiles": "scientist,coder",
    "message": "Scientist: outline evaluation metrics. Coder: implement metrics stub and tests.",
    "attachments": [],
    "reset": false
  }
}
```

##### Reset a profile
```json
{
  "tool_name": "call_subordinate",
  "tool_args": {
    "agent_profile": "coder",
    "message": "Start a fresh take: re-derive the module structure and list open risks.",
    "reset": true
  }
}
```

#### Available settings profiles
{{agent_profiles}}
