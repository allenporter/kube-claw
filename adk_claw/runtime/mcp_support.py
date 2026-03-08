"""
MCP Support for adk-claw.

Handles parsing and connecting to external MCP servers defined
in the workspace configuration.
"""

import logging
from typing import Any

from adk_coder.mcp import get_mcp_toolsets

logger = logging.getLogger(__name__)


class McpSupport:
    """
    Manages external MCP server connections.
    """

    def __init__(self, mcp_config: dict[str, Any]) -> None:
        self._config = mcp_config

    def get_toolset_args(self) -> dict[str, Any]:
        """
        Return arguments for adk-coder's toolset initialization.
        """
        # Load MCP toolsets using adk-coder's utility.
        # It expects a settings dict with 'mcpServers'.
        settings = {"mcpServers": self._config}
        toolsets = get_mcp_toolsets(settings)
        if toolsets:
            logger.info(f"Configured {len(toolsets)} MCP toolsets")
        return {"extra_tools": toolsets}
