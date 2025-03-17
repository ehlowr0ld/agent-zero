from datetime import datetime
from python.helpers.extension import Extension
from agent import Agent, LoopData


class SystemPrompt(Extension):

    async def execute(self, system_prompt: list[str]=[], loop_data: LoopData = LoopData(), **kwargs):
        # append main system prompt and tools
        main = get_main_prompt(self.agent)
        tools = get_tools_prompt(self.agent)
        system_prompt.append(main)
        system_prompt.append(tools)


def get_main_prompt(agent: Agent):
    system_prompt = ""
    if agent.context.deep_search:
        system_prompt += get_prompt("deepsearch.system.main.md", agent)
    else:
        system_prompt += get_prompt("agent.system.main.md", agent)
    if agent.context.planning != "off":
        system_prompt += '\n' + get_prompt("agent.system.main.planning.no_include.md", agent)
    return system_prompt


def get_tools_prompt(agent: Agent):
    prompt = get_prompt("agent.system.tools.md", agent)
    if agent.context.reasoning != "off":
        prompt += '\n' + get_prompt("agent.system.tools_reasoning.md", agent)
    if agent.context.planning != "off":
        prompt += '\n' + get_prompt("agent.system.tools_planning.md", agent)
    return prompt


def get_prompt(file: str, agent: Agent):
    # variables for system prompts
    # TODO: move variables to the end of chain
    # variables in system prompt would break prompt caching, better to add them to the last message in conversation
    vars = {
        "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent_name": agent.agent_name,
    }
    return agent.read_prompt(file, **vars)
