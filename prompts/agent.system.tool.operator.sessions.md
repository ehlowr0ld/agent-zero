## Active VNC Session Tools

**Note: These tools are only available during an active VNC desktop control session.**

#### Session Management

##### operator:declare_intent

Declare your high-level intention before performing actions. This helps track and organize your desktop automation workflow.

~~~json
{
    "tool_name": "operator:declare_intent",
    "tool_args": {
        "intent": "Click on the Firefox icon to open the browser",
        "reasoning": "I need to open Firefox to navigate to the requested website"
    }
}
~~~

##### operator:update_screen

Capture a fresh screenshot and update desktop state information.

~~~json
{
    "tool_name": "operator:update_screen",
    "tool_args": {}
}
~~~

##### operator:exit_session

End the VNC session and return to normal context. Always call this when your desktop task is complete.

~~~json
{
    "tool_name": "operator:exit_session",
    "tool_args": {}
}
~~~

#### Mouse Operations

All mouse operations support both fractional coordinates (0.0-1.0, default) and pixel coordinates.

##### operator:move_mouse

Move the mouse cursor to specified coordinates.

~~~json
{
    "tool_name": "operator:move_mouse",
    "tool_args": {
        "x": 0.5,
        "y": 0.3,
        "coordinate_type": "fraction"
    }
}
~~~

##### operator:click

Click at specified coordinates. Supports left, right, and middle mouse buttons.

~~~json
{
    "tool_name": "operator:click",
    "tool_args": {
        "x": 0.1,
        "y": 0.05,
        "button": "left",
        "coordinate_type": "fraction"
    }
}
~~~

##### operator:double_click

Double-click at specified coordinates.

~~~json
{
    "tool_name": "operator:double_click",
    "tool_args": {
        "x": 0.5,
        "y": 0.5,
        "button": "left"
    }
}
~~~

##### operator:drag

Drag from start coordinates to end coordinates.

~~~json
{
    "tool_name": "operator:drag",
    "tool_args": {
        "start_x": 0.2,
        "start_y": 0.3,
        "end_x": 0.8,
        "end_y": 0.7,
        "button": "left"
    }
}
~~~

##### operator:scroll

Scroll at specified coordinates.

~~~json
{
    "tool_name": "operator:scroll",
    "tool_args": {
        "x": 0.5,
        "y": 0.5,
        "direction": "up",
        "amount": 3
    }
}
~~~

#### Keyboard Operations

##### operator:type_text

Type a text string.

~~~json
{
    "tool_name": "operator:type_text",
    "tool_args": {
        "text": "Hello World!"
    }
}
~~~

##### operator:press_key

Press a single key. Use exact key names.

~~~json
{
    "tool_name": "operator:press_key",
    "tool_args": {
        "key": "Return"
    }
}
~~~

##### operator:key_combination

Press key combinations for shortcuts.

~~~json
{
    "tool_name": "operator:key_combination",
    "tool_args": {
        "keys": ["Ctrl", "c"]
    }
}
~~~

## Key Names Reference

- **Modifiers**: "Ctrl", "Alt", "Shift", "Super" (Windows/Cmd key)
- **Special Keys**: "Return", "Escape", "Tab", "BackSpace", "Delete", "Insert", "Home", "End", "Page_Up", "Page_Down"
- **Arrow Keys**: "Up", "Down", "Left", "Right"
- **Function Keys**: "F1", "F2", "F3", etc.
- **Regular Characters**: Use exact character ("a", "A", "1", "!", "@", etc.)

## Best Practices

1. **Always declare intent** before performing actions to maintain clear workflow tracking
2. **Use fractional coordinates** from annotations directly - they're already in the correct format
3. **Update screen regularly** after significant actions to see results
4. **Exit sessions** when tasks are complete to return to normal context
5. **Handle focus carefully** - ensure the right window/application is active
6. **Plan action sequences** - complex tasks may require multiple steps with screen updates

## Session Workflow Example

**Note: This workflow assumes you've already called `operator:enter_session` from the basic tools.**

~~~json
// 1. Declare intent
{
    "tool_name": "operator:declare_intent",
    "tool_args": {
        "intent": "Find and click the calculator application",
        "reasoning": "Need to locate the calculator in the applications menu or taskbar"
    }
}

// 2. Perform actions
{
    "tool_name": "operator:click",
    "tool_args": {
        "x": 0.1,
        "y": 0.9
    }
}

// 3. Update screen to see results
{
    "tool_name": "operator:update_screen",
    "tool_args": {}
}

// 4. Continue with more actions...
// 5. Exit when done
{
    "tool_name": "operator:exit_session",
    "tool_args": {}
}
~~~
