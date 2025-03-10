from python.helpers.extension import Extension
from agent import LoopData


class ResetAgentData(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        self.agent.set_data('thinking_topic', "...")
        self.agent.set_data('response_ttft', '00:00:00')
        self.agent.set_data('response_duration', '00:00:00')
