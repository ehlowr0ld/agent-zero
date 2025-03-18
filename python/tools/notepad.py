import json

from python.helpers.tool import Tool, Response
from python.helpers.notepad import Note


class NotepadTool(Tool):

    async def execute(self, **kwargs):
        if self.method == "add_note":
            return await self.add_note()
        elif self.method == "delete_note":
            return await self.delete_note()
        elif self.method == "update_note":
            return await self.update_note()
        elif self.method == "clear":
            return await self.clear()
        elif self.method == "display":
            return await self.display()
        else:
            valid_methods = ["add_note", "delete_note", "update_note", "clear", "display"]
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.invalid_method.md",
                    tool_name=self.name,
                    tool_method=self.method,
                    valid_methods=json.dumps(valid_methods, indent=4),
                ),
                break_loop=False,
            )

    async def add_note(self):
        if "content" not in self.args:
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.missing_tool_arg.md",
                    tool_name=self.name,
                    missing_arg="content",
                    tool_args=json.dumps(self.args, indent=4),
                ), break_loop=False)

        note = Note(content=self.args["content"])
        self.agent.notepad.add_note(note)
        message = self.agent.parse_prompt(
            "fw.notepad.add_note.md",
            uid=note.uid,
            all_notes=json.dumps(self.agent.notepad.get_notes_for_rendering(), indent=4),
        )
        return Response(message=message, break_loop=False)

    async def update_note(self):
        if "uid" not in self.args:
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.missing_tool_arg.md",
                    tool_name=self.name,
                    missing_arg="uid",
                    tool_args=json.dumps(self.args, indent=4),
                ), break_loop=False)

        if "content" not in self.args:
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.missing_tool_arg.md",
                    tool_name=self.name,
                    missing_arg="content",
                    tool_args=json.dumps(self.args, indent=4),
                ), break_loop=False)

        self.agent.notepad.update_note(uid=self.args["uid"], new_content=self.args["content"])
        message = self.agent.parse_prompt(
            "fw.notepad.update_note.md",
            uid=self.args["uid"],
            all_notes=json.dumps(self.agent.notepad.get_notes_for_rendering(), indent=4),
        )
        return Response(message=message, break_loop=False)

    async def delete_note(self):
        if "uid" not in self.args:
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.missing_tool_arg.md",
                    tool_name=self.name,
                    missing_arg="uid",
                    tool_args=json.dumps(self.args, indent=4),
                ), break_loop=False)
        if not self.agent.notepad.get_note(self.args["uid"]):
            return Response(
                message=self.agent.read_prompt(
                    "fw.notepad.note_not_found.md",
                    uid=self.args["uid"],
                ), break_loop=False)

        self.agent.notepad.delete_note(self.args["uid"])
        message = self.agent.parse_prompt(
            "fw.notepad.delete_note.md",
            uid=self.args["uid"],
            all_notes=json.dumps(self.agent.notepad.get_notes_for_rendering(), indent=4),
        )
        return Response(message=message, break_loop=False)

    async def clear(self):
        self.agent.notepad.clear()
        message = self.agent.parse_prompt(
            "fw.notepad.clear.md",
            all_notes=json.dumps(self.agent.notepad.get_notes_for_rendering(), indent=4),
        )
        return Response(message=message, break_loop=False)

    async def display(self):
        message = self.agent.parse_prompt(
            "fw.notepad.display.md",
            all_notes=json.dumps(self.agent.notepad.get_notes_for_rendering(), indent=4),
        )
        return Response(message=message, break_loop=False)
