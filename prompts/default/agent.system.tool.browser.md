### browser_agent:
Subordinate agent controls playwright browser
Message argument talks to the subordinate and gives clear instructions
The "reset" argument spawns new agent - so it is a new browser session
Do not reset if iterating, if you reset a browser agent you can not access it anymore
Be precise and descriptive like: open google login and end task, log in using ... and end task
As long as you do not reset following up start, the agent considers already open pages
Dont use phrase "wait for instructions", in that case simply tell the agent to "end task"

#### Usage:

```json
{
  "thoughts": ["I need to log in to..."],
  "reflection": [
      "...",
  ],
  "tool_name": "browser_agent",
  "tool_args": {
    "message": "Open and log me into...",
    "reset": "true"
  }
}
```

```json
{
  "thoughts": ["I need to log in to..."],
  "reflection": ["..."],
  "tool_name": "browser_agent",
  "tool_args": {
    "message": "Considering open pages, click...",
    "reset": "false"
  }
}
```

```json
{
  "thoughts": ["I now have everything I need..."],
  "reflection": ["..."],
  "tool_name": "browser_agent",
  "tool_args": {
    "message": "end task",
    "reset": "false"
  }
}
```
