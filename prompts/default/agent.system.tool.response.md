### response:
The final answer to user is contained in the "text" argument
Ends task processing - use this tool ONLY when done, no task active OR you need feedback from user
Put the text (for example final task result) in text arg
Always write full file paths if local files are mentioned

#### Usage:
~~~json
{
    "observations": [
        "...",
    ],
    "thoughts": [
        "...",
    ],
    "reflection": ["..."],
    "tool_name": "response",
    "tool_args": {
        "text": "Answer to the user",
    }
}
~~~
