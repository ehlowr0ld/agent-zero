from python.helpers.api import ApiHandler
from flask import Request, Response
from typing import Any


class PlanningSet(ApiHandler):
    async def process(
        self, input: dict[str, Any], request: Request
    ) -> dict[str, Any] | Response:
        # input data
        planning = input.get("planning", "auto")
        if isinstance(planning, bool):
            # Handle legacy boolean input
            planning = "on" if planning else "off"
        elif planning not in ["off", "on", "auto"]:
            planning = "auto"
        ctxid = input.get("context", "")

        # context instance - get or create
        context = self.get_context(ctxid)

        # Set planning state on context
        context.planning = planning

        # Return response with context id and state
        state_messages = {
            "off": "Planning set to OFF",
            "on": "Planning set to ON",
            "auto": "Planning set to AUTO (dynamic choice by model)"
        }
        return {
            "message": state_messages[planning],
            "planning": planning,
            "context": context.id
        }
