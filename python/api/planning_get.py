from python.helpers.api import ApiHandler
from flask import Request, Response
from typing import Any, Dict

class PlanningGet(ApiHandler):
    async def process(
        self, input: Dict[str, Any], request: Request
    ) -> Dict[str, Any] | Response:
        # Get context ID from input
        ctxid = input.get("context", "")

        # Get context instance
        context = self.get_context(ctxid)

        # Return current planning state
        return {
            "planning": context.planning if hasattr(context, "planning") else "auto",
            "context": context.id
        }
