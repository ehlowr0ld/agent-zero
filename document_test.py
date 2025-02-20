import dirtyjson
from python.helpers.dirty_json import DirtyJson as dirty_json

json = """
{
    "title": "one",
    "observations": [
        "observation1",
        "observation2",
        "..."
    ],
    "thoughts": [
        "thought1",
        "thought2",
        "..."
    ],
    "reflection": [
        "reflection on thoughts or revision of plan",
        "self-critical assessment of the thoughts"
        "...",
    ],
    "tool_name": "tool_to_use1",
    "tool_args": {
        "arg1": "val11",
        "arg2": "val12"
    }
}
...
{
    "title": "two",
    "observations": [
        "observation1",
        "observation2",
        "..."
    ],
    "thoughts": [
        "thought1",
        "thought2",
        "..."
    ],
    "reflection": [
        "reflection on thoughts or revision of plan",
        "self-critical assessment of the thoughts"
        "...",
    ],
    "tool_name": "tool_to_use2",
    "tool_args": {
        "arg1": "val21",
        "arg2": "val22"
    }
}
"""

print(dirty_json.parse_string(json))
