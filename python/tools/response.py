from python.helpers.tool import Tool, Response
import time
import json


class ResponseTool(Tool):

    async def execute(self, **kwargs):
        valid_methods = ["notification", "response"]
        if self.method not in valid_methods:
            return Response(
                message=self.agent.read_prompt(
                    "fw.tool_call.invalid_method.md",
                    tool_name=self.name,
                    tool_method=self.method,
                    valid_methods=json.dumps(valid_methods, indent=4),
                ),
                break_loop=False,
            )

        return await getattr(self, self.method)()

    async def notification(self):
        return Response(message=self.args["text"], break_loop=False)

    async def response(self):
        return Response(message=self.args["text"], break_loop=True)

    async def before_execution(self, **kwargs):
        monolog_duration = time.strftime("%H:%M:%S", time.gmtime(time.time() - int(self.agent.get_data('monolog_start'))))
        heading = f"{self.agent.agent_name}: Response (Duration: {monolog_duration})"
        if self.method == "notification":
            heading = f"{self.agent.agent_name}: Notification (Elapsed: {monolog_duration})"

        self.log = self.agent.context.log.log(
            type="response",
            heading=heading,
            content=self.args.get("text", ""),
        )

    async def after_execution(self, response, **kwargs):
        pass  # do not add anything to the history or output
