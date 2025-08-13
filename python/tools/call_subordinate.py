from agent import Agent, UserMessage, AgentContext, AgentContextType
from python.helpers.tool import Tool, Response
import asyncio
from python.helpers.defer import DeferredTask
from initialize import initialize_agent


class Delegation(Tool):

    async def execute(self, message: str = "", reset: str | bool = "", **kwargs):
        # Determine profile keys for subordinate(s)
        def parse_profiles(val) -> list[str]:
            if isinstance(val, list):
                return [str(p).strip() for p in val if str(p).strip() != ""]
            s = str(val or "").strip()
            if not s:
                return [""]
            if "," in s:
                return [p.strip() for p in s.split(",") if p.strip()]
            return [s]

        # Prefer new naming (settings_profile/settings_profiles), keep aliases
        profiles_input = (
            kwargs.get(
                "settings_profiles",
                kwargs.get(
                    "settings_profile",
                    kwargs.get(
                        "agent_profiles",
                        kwargs.get("agent_profile", ""),
                    ),
                ),
            )
        )
        agent_profiles: list[str] = parse_profiles(profiles_input)
        attachments = kwargs.get("attachments", []) or []
        reset_flag = str(reset).lower().strip() == "true" or bool(reset) is True

        # Retrieve or initialize subordinate mapping on the superior agent
        subordinates: dict[str, Agent] = self.agent.get_data(Agent.DATA_NAME_SUBORDINATE) or {}

        # Ensure subordinates exist per profile, apply reset as needed
        for settings_profile in agent_profiles:
            if reset_flag and settings_profile in subordinates:
                try:
                    existing = subordinates.pop(settings_profile)
                    if existing and getattr(existing, "context", None):
                        try:
                            existing.context.reset()
                            AgentContext.remove(existing.context.id)
                        except Exception:
                            pass
                finally:
                    self.agent.set_data(Agent.DATA_NAME_SUBORDINATE, subordinates)

            if settings_profile not in subordinates:
                # Create persistent background context for subordinate
                # Build config for the requested settings profile (or fall back to selected)
                sub_config = initialize_agent(profile=(settings_profile or None))
                sub_context = AgentContext(
                    config=sub_config,
                    type=AgentContextType.BACKGROUND,
                )
                new_subordinate: Agent = Agent(self.agent.number + 1, sub_config, sub_context)
                new_subordinate.set_data(Agent.DATA_NAME_SUPERIOR, self.agent)
                subordinates[settings_profile] = new_subordinate
                self.agent.set_data(Agent.DATA_NAME_SUBORDINATE, subordinates)

        # Launch monologues as background tasks and wait for completion
        task_pairs: list[tuple[str, DeferredTask]] = []
        for settings_profile in agent_profiles:
            sub = subordinates.get(settings_profile)
            if sub is None:
                continue
            # queue message
            sub.hist_add_user_message(UserMessage(message=message, attachments=attachments))
            # if task alive, reuse it; else start new
            if sub.context.task and sub.context.task.is_alive():
                task = sub.context.task
            else:
                task = sub.context.run_task(sub.monologue)
            task_pairs.append((settings_profile, task))

        if not task_pairs:
            return Response(message="Failed to initialize subordinate agent(s).", break_loop=False)

        # Wait for all backgrounds to finish and collect results
        async def await_result(t: DeferredTask):
            try:
                return await t.result()
            except Exception as e:
                return f"Error: {e}"

        results = await asyncio.gather(*[await_result(t) for _, t in task_pairs])

        # Aggregate with profile prefix
        formatted = []
        for (profile_key, _), resp in zip(task_pairs, results):
            profile_label = profile_key or "default"
            formatted.append(f"[{profile_label}]\n{resp}")

        return Response(message="\n\n".join(formatted), break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="tool",
            heading=f"icon://communication {self.agent.agent_name}: Calling Subordinate Agent",
            content="",
            kvps=self.args,
        )
