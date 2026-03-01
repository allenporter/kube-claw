import subprocess
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types


class ClawMCPServer:
    """
    Host-side MCP server that exposes tools to the worker.
    Enables tool hydration by using host-side context (lane_id, workspace_path).
    """

    def __init__(self, lane_id: str, workspace_path: str):
        self.server = Server("claw-mcp-server")
        self.lane_id = lane_id
        self.workspace_path = workspace_path
        self._setup_tools()

    def _setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="git_info",
                    description="Get git status for the current workspace",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="read_secret",
                    description="Read a sensitive secret from the host",
                    inputSchema={
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name == "git_info":
                # Hydrated execution using host context
                res = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True,
                )
                branch = res.stdout.strip() or "No branch"
                return [
                    types.TextContent(
                        type="text",
                        text=f"Workspace: {self.workspace_path}, Branch: {branch}",
                    )
                ]

            elif name == "read_secret":
                key = arguments.get("key")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Secret [{key}] = (Host-only credentials for {self.lane_id})",
                    )
                ]

            raise ValueError(f"Unknown tool: {name}")

    async def run_server(self, read_stream, write_stream):
        await self.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="claw-mcp-server",
                server_version="0.1.0",
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
