### Category: Notepad management
This tool enables the agent to manage a notepad by taking and deleting notes as well as displaying the notepad.
Useful to retain information beyond the context window limitation of the underlying LLM.
The order of notes is fixed.

An example notepad looks like this:
~~~json
[
  {
      "uid": "35dee229-037f-47a6-b7c3-73c23ee0c253",
      "content": "...Content of note 1...",
      "timestamp": "2025-01-02 11:32:50"
  },
  {
      "uid": "35dee229-037f-47a6-b7c3-73c23ef0c254",
      "content": "...Content of note 2...",
      "timestamp": "2025-01-02 11:32:50"
  }
]
~~~

#### notepad:add_note
Append a new note to the notepad.

##### Arguments:
 *  content (type: str) : The entire content of the note

##### Usage:
~~~json
{
    "topic": "...",
    "observations": ["...", "..."],
    "thoughts": ["...", "..."],
    "reflection": ["...", "..."],
    "tool_name": "notepad:add_note",
    "tool_args": {
        "content": "...The entire content of the note..."
    }
}
~~~

#### notepad:delete_note
Delete the note with specified 'uid' from the notepad.

##### Arguments:
 *  uid (type: str) : The uid of note to be deleted.

##### Usage:
~~~json
{
    "topic": "...",
    "observations": ["...", "..."],
    "thoughts": ["...", "..."],
    "reflection": ["...", "..."],
    "tool_name": "notepad:delete_note",
    "tool_args": {
        "uid": "...The uid of note to be deleted..."
    }
}
~~~

#### notepad:update_note
Update the note specified by 'uid' with content specified in 'content'.

##### Arguments:
 *  uid (type: str) : The uid of note to be updated.
 *  content (type: str) : The new content of the note

##### Usage:
~~~json
{
    "topic": "...",
    "observations": ["...", "..."],
    "thoughts": ["...", "..."],
    "reflection": ["...", "..."],
    "tool_name": "notepad:update_note",
    "tool_args": {
        "uid": "...The uid of note to be updated...",
        "content": "...The new content of the note..."
    }
}
~~~

#### notepad:clear
Clear the entire notepad effectively emptying it.

##### Arguments:
None.

##### Usage:
~~~json
{
    "topic": "...",
    "observations": ["...", "..."],
    "thoughts": ["...", "..."],
    "reflection": ["...", "..."],
    "tool_name": "notepad:clear",
    "tool_args": {}
}
~~~

#### notepad:display
Display the entire notepad with all notes.

##### Arguments:
None.

##### Usage:
~~~json
{
    "topic": "...",
    "observations": ["...", "..."],
    "thoughts": ["...", "..."],
    "reflection": ["...", "..."],
    "tool_name": "notepad:display",
    "tool_args": {}
}
~~~
