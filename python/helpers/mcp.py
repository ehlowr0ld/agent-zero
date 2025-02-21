from pydantic import BaseModel, Field, Discriminator, Tag
from typing import List, Dict, Optional, Any, Union, Literal, Annotated
import dirtyjson
from python.helpers.dirty_json import DirtyJson

class MCPServerRemote(BaseModel):
    name: str
    url: str
    headers: dict[str, Any] | None = Field(default_factory=dict[str, Any])
    timeout: float = 5.0
    sse_read_timeout: float = 60.0 * 5.0

class MCPServerLocal(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    encoding: str = "utf-8"
    encoding_error_handler: Literal["strict", "ignore", "replace"] = "strict"

MCPServer = Annotated[
    Union[
      Annotated[MCPServerRemote, Tag('MCPServerRemote')],
      Annotated[MCPServerLocal, Tag('MCPServerLocal')]
    ],
    Discriminator(lambda v: "MCPServerRemote" if "url" in v else "MCPServerLocal")
]

class MCPConfig(BaseModel):
    servers: List[MCPServer]

def parse_mcp_config(config_str: str) -> MCPConfig:
    """Parse the MCP config string into a MCPConfig object."""
    try:
      servers = dirtyjson.loads(config_str)
    except Exception:
      try:
        servers = DirtyJson.parse_string(config_str)
      except Exception as e:
        raise ValueError(f"Failed to parse MCP config: {e}")
    return MCPConfig(servers=servers)
