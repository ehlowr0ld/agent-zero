### Operator Tools

you can use operator tools to interact with the desktop
view the desktop, move mouse, click, input text, etc.

#### operator:annotated_screenshot

view the desktop with annotations of interactive elements
the annotations are in the format of a json object

##### Annotations Examples

icon 0: {'type': 'text',
    'bbox': [0.0, 0.0, 0.0572916679084301, 0.025925925001502037],
    'interactivity': False,
    'content': ' Applications :',
    'source': 'box_ocr_content_ocr'
}
icon 1: {'type': 'icon',
    'bbox': [0.0038082837127149105, 0.025409793481230736, 0.06452322006225586, 0.12717387080192566],
    'interactivity': True,
    'content': 'Home ',
    'source': 'box_yolo_content_ocr'
}

##### Example Usage

~~~json
{
    "thoughts": [
        "I need to find the home icon",
    ],
    "tool_name": "operator:annotated_screenshot",
    "tool_args": {
        "method": "annotated_screenshot",
    }
}
~~~
