from python.helpers.api import ApiHandler
from flask import Request, Response

from agent import AgentContext
from python.api.chat_rename import ChatNames
from python.helpers import persist_chat


class Poll(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", None)
        from_no = input.get("log_from", 0)

        # context instance - get or create
        context = self.get_context(ctxid)
        logs = context.log.output(start=from_no)

        # Get chat names instance
        chat_names = ChatNames.get_instance()

        # loop AgentContext._contexts and number unnamed chats
        ctxs = []
        tasks = []
        processed_contexts = set()  # Track processed context IDs
        chat_count = 1

        # First, identify all tasks
        for ctx in AgentContext._contexts.values():
            # Skip if already processed
            if ctx.id in processed_contexts:
                continue

            name = chat_names.get_name(ctx.id)
            # If it's a default name (Chat #xxxxx), replace with sequential number
            if name.startswith("Chat #"):
                name = f"Chat {chat_count}"
            chat_count += 1

            context_data = {
                "id": ctx.id,
                "no": ctx.no,
                "name": name,
                "log_guid": ctx.log.guid,
                "log_version": len(ctx.log.updates),
                "log_length": len(ctx.log.logs),
                "paused": ctx.paused,
                "reasoning": ctx.reasoning,
                "planning": ctx.planning,
                "deep_search": getattr(ctx, "deep_search", False),
            }

            # Determine if this is a task using multiple methods
            ctx_path = persist_chat.get_chat_folder_path(ctx.id)
            is_task = (ctx_path and persist_chat.TASKS_FOLDER in ctx_path) or name.startswith("TASK: ")

            # Add to the appropriate list
            if is_task:
                tasks.append(context_data)
            else:
                ctxs.append(context_data)

            # Mark as processed
            processed_contexts.add(ctx.id)

        # data from this server
        return {
            "context": context.id,
            "contexts": ctxs,
            "tasks": tasks,
            "logs": logs,
            "log_guid": context.log.guid,
            "log_version": len(context.log.updates),
            "log_progress": context.log.progress,
            "log_progress_active": context.log.progress_active,
            "paused": context.paused,
            "reasoning": context.reasoning,
            "planning": context.planning,
            "deep_search": getattr(context, "deep_search", False),
        }
