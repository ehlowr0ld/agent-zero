from agent import Agent, UserMessage, AgentContext, AgentContextType
from python.helpers.tool import Tool, Response
from initialize import initialize_agent


class Delegation(Tool):

    async def execute(self, message="", reset="", **kwargs):
        # Create temporary context for subordinate execution
        temp_context = AgentContext(
            config=self.agent.config,
            type=AgentContextType.BACKGROUND
        )

        try:
            # create subordinate agent using the data object on this agent and set superior agent to his data object
            if (
                self.agent.get_data(Agent.DATA_NAME_SUBORDINATE) is None
                or str(reset).lower().strip() == "true"
            ):
                # Create subordinate agent in temporary context
                subordinate: Agent = Agent(self.agent.number + 1, self.agent.config, temp_context)

                # Set subordinate prompt profile if provided, otherwise use default
                agent_profile = kwargs.get("agent_profile", "")
                subordinate.config.profile = agent_profile

                # register superior/subordinate
                subordinate.set_data(Agent.DATA_NAME_SUPERIOR, self.agent)
                self.agent.set_data(Agent.DATA_NAME_SUBORDINATE, subordinate)

            subordinate: Agent = self.agent.get_data(Agent.DATA_NAME_SUBORDINATE)
            # Add user message to subordinate agent
            subordinate.hist_add_user_message(UserMessage(message=message, attachments=[]))
            # Run subordinate monologue in isolated context
            result = await subordinate.monologue()

            # Return result (context will be cleaned up in finally block)
            return Response(message=result, break_loop=False)

        finally:
            # Always clean up temporary context
            try:
                temp_context.reset()
                AgentContext.remove(temp_context.id)
            except Exception as cleanup_error:
                from python.helpers.print_style import PrintStyle
                PrintStyle(font_color="red", padding=True).print(
                    f"Warning: Failed to clean up subordinate context {temp_context.id}: {cleanup_error}"
                )

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://communication {self.agent.agent_name}: Calling Subordinate Agent",
            content="",
            kvps=self.args,
        )
