from python.helpers.tool import Tool, Response

class NoopTool(Tool):

    async def execute(self,**kwargs):
        response =  self.agent.read_prompt("fw.noop_tool.md")
        return Response(message=response, break_loop=False)

    async def before_execution(self, **kwargs):
        self.agent.context.log.log(
                type="hint",
                content=f"Agent {self.agent.agent_name} is performing a noop operation",
            )


    async def after_execution(self, response, **kwargs):
        pass # do not add anything to the history or output
