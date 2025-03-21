from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers.chat_names import ChatNames


class RenameChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        chat_id = input.get("chat_id", "")
        new_name = input.get("name", "")

        if not chat_id or not new_name:
            raise Exception("Chat ID and new name are required")

        chat_names = ChatNames.get_instance()
        chat_names.set_name(chat_id, new_name)

        return {
            "message": "Chat renamed successfully",
            "chat_id": chat_id,
            "name": new_name
        }
