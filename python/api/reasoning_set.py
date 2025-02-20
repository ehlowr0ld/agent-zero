from python.helpers.api import ApiHandler
from flask import Request, Response
from typing import Any

class ReasoningSet(ApiHandler):
    async def process(
        self, input: dict[str, Any], request: Request
    ) -> dict[str, Any] | Response:
        # input data
        reasoning = True if input.get("reasoning", False) else False
        ctxid = input.get("context", "")

        # context instance - get or create
        context = self.get_context(ctxid)

        # Set reasoning state on context
        context.reasoning = reasoning

        # Return response with context id and state
        return {
            "message": "Reasoning enabled." if reasoning else "Reasoning disabled.",
            "reasoning": reasoning,
            "context": context.id
        }
