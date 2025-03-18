from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers import tokens


class GetTaskList(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", [])
        context = self.get_context(ctxid)
        tasklist = context.agent0.tasklist.get_tasks_for_rendering(include_logs=True)
        size = tokens.approximate_tokens(str(tasklist))

        return {"content": tasklist, "tokens": size}
