from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers import persist_chat
from python.helpers.tasklist import TaskList
from python.helpers.notepad import Notepad
from agent import AgentContext


class RemoveChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")

        # context instance - get or create
        AgentContext.remove(ctxid)
        persist_chat.remove_chat(ctxid)

        # delete tasklist of this context
        TaskList.delete_instance(ctxid)

        # delete notepad of this context
        Notepad.delete_instance(ctxid)

        return {
            "message": "Context removed.",
        }
