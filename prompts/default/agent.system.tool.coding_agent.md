### coding_agent:

#### Manual
this tool controls an autonomous coding agent capable of large project development
the underlying framework of this tool is the "aider" ai development framework
each task for the coding agent is a new tool call
the history of conversation and cache are managed on a per-project basis and are stored in the root_path of the project
you can give the agent development tasks he will complete in one go, further requests for same project must simply point to the projects root_path
always provide a very comprehensive and exhaustive context in the task text
give the agent a persona + provide all necessary background info + formulate the task in an actionable way = provide this info formatted in the task argument
always ensure the root_folder exists for new development without existig codebase
to first test what agent would do and examine outpt without actual changes use the dry_run boolean parameter
if you want the agent to edit files in the root_folder you must pass the list of editable files in the files parameter. the items in the files list can be wildcards, they are relative paths from root_folder location
!!! if you dont add any files to the chat the agent will not edit any files.

#### Arguments:
* *task* (string, mandatory) - The task description including persona and background information
* *root_path* (string, mandatory) - The full path to the folder the agent will work in. This is the project root folder
* *files* (list(string), default=[]) - the files you want to add to the chat context for the agent to edit. Can contain wildcards. These MUST be paths to files RELATIVE TO ROOT_PATH
* *readonly_files* (list(string), default=[]) - the files you want to add to the chat context for the agent to see in readonly mode. Gives the agent hints which files to read for the task. Can contain wildcards. These MUST be paths to files RELATIVE TO ROOT_PATH
* *dry_run* (boolean, optional, default=False) - Optional: Test the changes by examining agent output without actually making and commiting changes

#### Usage:
```json
{
  "thoughts": ["I need to develop a..."],
  "tool_name": "coding_agent",
  "tool_args": {
    "task": "You are a ..... \n\nThis project is .... \n\nPlease implement .... and make sure that .... in the attached files ...",
    "root_path": "/path/to/project/folder",
    "files": ["main.py", "pyhton/settings.py"],
    "dry_run": false
  }
}
```

```json
{
  "thoughts": ["I need to develop a..."],
  "tool_name": "coding_agent",
  "tool_args": {
    "task": "You are a ..... \n\n\nThis project is .... \n\nPlease implement .... ",
    "root_path": "/path/to/another/project/folder",
    "files": [],
    "dry_run": false
  }
}
```

```json
{
  "thoughts": ["Let's see what the agent would do if ..."],
  "tool_name": "coding_agent",
  "tool_args": {
    "task": "You are a ..... \n\n\nThis project is .... \n\nPlease implement .... ",
    "root_path": "/path/to/another/project/folder",
    "dry_run": true
  }
}
```
