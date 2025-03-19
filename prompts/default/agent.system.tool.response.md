### Tools for "Communication with the user"

These response tools 'response:response' and 'response:notification' are both sending a message to the user directly.
!!! The 'response:response' tool is intended to respond and wait for user input.
!!! The 'response:notification' tool is intended for intermediate notifications to to user about current status of processing.
!!! The 'response:notification' tool does not wait for user to respond
!!! If you are expecting user response to your message or if this is the final message to the user, always use 'response:response'.

#### response:response
The response message to user is contained in the "text" argument
This response interrupts task processing allowing for user input.
!!! use this tool when you're done processing a task or when you need input from user.
Put the text (for example final task result) in text arg
Always write full file paths if local files are mentioned
Use full sentences and language matching the user's request
Consider any directions from the user about the form and contents of the response before answering

##### Arguments:
 *  text (type: str) - The response you want to give to the user and then wait for further user input.

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
    "tool_name": "response:response",
    "tool_args": {
        "text": "I need more input before I can continue with the task. Please provide....",
    }
}
~~~
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
    "tool_name": "response:response",
    "tool_args": {
        "text": "The final solution to your question is: ....",
    }
}
~~~

#### response:notification
The notification message to user is contained in the "text" argument
This type of notification does not end task processing
!!! use this tool when you're NOT DONE and have EITHER task active OR you need to continue work after giving the notification
!!! after this answer your task continues. If you want user to reply to your message, use response:response
Put the text (for example final task result) in text arg
Always write full file paths if local files are mentioned
Use full sentences and language matching the user's request
Consider any directions from the user about the form and contents of the notifications before answering

##### Arguments:
 *  text (type: str) - The notification you want to send to the user and immediately continue with your task.

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
    "tool_name": "response:notification",
    "tool_args": {
        "text": "I am now beginning the second phase of processing XYZ",
    }
}
~~~
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
    "tool_name": "response:notification",
    "tool_args": {
        "text": "A completed, moving on to B",
    }
}
~~~
