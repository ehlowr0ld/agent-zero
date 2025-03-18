### "Reponse" family of tools
These response tools 'response:final' and 'response:feedback' are both sending a message to the user directly.
The 'response:final' tool is intended for the absolute end of task processing. Use when you just report for the final report about final results.
The 'response:feedback' tool is intended for intermediate feedback to user. Use When you just want to give headsup and right away continue your work.

#### response:feedback
The feedback message to user is contained in the "text" argument
This type of answer does not end task processing
!!! use this tool when you're NOT DONE and have EITHER task active OR you need to continue work after the answer
Put the text (for example final task result) in text arg
Always write full file paths if local files are mentioned
Use full sentences and language matching the user's request
Consider any directions from the user about the form and contents of the response before answering

##### Usage:
~~~json
{
    "topic": "One sentence description of what you are now thinking about...",
    "observations": [
        "...",
    ],
    "thoughts": [
        "...",
    ],
    "reflection": ["..."],
    "tool_name": "response:feedback",
    "tool_args": {
        "text": "Final answer to the user",
    }
}
~~~

#### response:final
The final answer to user is contained in the "text" argument
Ends task processing
!!! use this tool ONLY when you're done and have NEITHER task active NOR you need to continue work after the answer
Put the text (for example final task result) in text arg
Always write full file paths if local files are mentioned
Use full sentences and language matching the user's request
Consider any directions from the user about the form and contents of the response before answering

##### Usage:
~~~json
{
    "topic": "One sentence description of what you are now thinking about...",
    "observations": [
        "...",
    ],
    "thoughts": [
        "...",
    ],
    "reflection": ["..."],
    "tool_name": "response:final",
    "tool_args": {
        "text": "Final answer to the user",
    }
}
~~~
