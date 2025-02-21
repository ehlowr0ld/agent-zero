from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import settings
from python.helpers.print_style import PrintStyle
from python.helpers.mcp import parse_mcp_config, MCPConfig


class SetSettings(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        set = settings.convert_in(input)
        set = settings.set_settings(set)

        # DEBUG: Print the "mcp servers" settings
        mcp_servers = settings.get_settings()["mcp_servers"]
        mcp_config = parse_mcp_config(mcp_servers)
        PrintStyle(
            background_color="#6734C3", font_color="white", bold=True, padding=True
        ).print(f"Parsed MCP config:")
        PrintStyle(background_color="#334455", font_color="white", padding=False).print(mcp_config.model_dump_json())

        return {"settings": set}
