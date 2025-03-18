from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers import tokens


class GetNotepad(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", [])
        context = self.get_context(ctxid)
        notepad = context.agent0.notepad.get_notes_for_rendering()
        size = tokens.approximate_tokens(str(notepad))

        return {"content": notepad, "tokens": size}
