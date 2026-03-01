import asyncio
import httpx
import logging
from collections.abc import AsyncIterator

from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import (
    Message,
    MessageSendParams,
    Task,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    Role,
    Part,
    TextPart,
)

from kube_claw.domain.models import InboundMessage, OrchestratorEvent
from kube_claw.binding.table import BindingTable
from kube_claw.sandbox.manager import SandboxManager
from kube_claw.mcp.transport import run_mcp_server_on_uds

from .base import Orchestrator

logger = logging.getLogger(__name__)


class A2AOrchestratorImpl(Orchestrator):
    """
    Concrete implementation of the A2A Orchestrator.
    Coordinatest Gateway, Binding Table, Sandbox, A2A, and MCP.
    """

    def __init__(
        self,
        binding_table: BindingTable,
        sandbox_manager: SandboxManager,
    ):
        self.binding_table = binding_table
        self.sandbox_manager = sandbox_manager
        self._mcp_tasks: dict[str, asyncio.Task] = {}

    async def handle_message(  # type: ignore[invalid-method-override]
        self, message: InboundMessage
    ) -> AsyncIterator[OrchestratorEvent]:
        # 1. Resolve Workspace
        context = await self.binding_table.resolve_workspace(
            message.identity.protocol, message.channel_id, message.identity.author_id
        )

        # 2. Provision Sandbox
        sandbox_status = await self.sandbox_manager.provision(
            context.workspace_id, context.metadata
        )

        if not sandbox_status.is_running:
            yield OrchestratorEvent(
                type="error",
                content=f"Failed to start sandbox: {sandbox_status.last_known_status}",
            )
            return

        # 3. Start Host MCP Server (if not already running for this lane)
        lane_id = message.lane_id
        if lane_id not in self._mcp_tasks:
            # We assume mcp_endpoint is a UDS path
            mcp_endpoint = sandbox_status.mcp_endpoint
            if mcp_endpoint:
                logger.info(f"Starting MCP server for lane {lane_id} at {mcp_endpoint}")
                # Mock workspace path for now, should come from context
                workspace_path = context.metadata.get(
                    "workspace_path", "/tmp/claw_default"
                )
                self._mcp_tasks[lane_id] = asyncio.create_task(
                    run_mcp_server_on_uds(mcp_endpoint, lane_id, workspace_path)
                )

        # 4. Connect to Worker A2A Server
        a2a_endpoint = sandbox_status.connection_endpoint
        if not a2a_endpoint:
            yield OrchestratorEvent(
                type="error", content="Sandbox started but no A2A endpoint provided."
            )
            return

        # Use httpx with UDS support
        transport = httpx.AsyncHTTPTransport(uds=a2a_endpoint)
        async with httpx.AsyncClient(transport=transport) as client:
            a2a_transport = JsonRpcTransport(
                httpx_client=client,
                url="http://localhost/",  # Hostname 'localhost' is ignored for UDS
            )

            # 5. Send Task to Worker
            # Convert InboundMessage to A2A Message
            a2a_message = Message(
                message_id=message.message_id or "",
                role=Role.user,
                parts=[Part(root=TextPart(kind="text", text=message.content))],
            )

            params = MessageSendParams(
                message=a2a_message,
                # Mapping lane_id to context_id for persistence
            )

            logger.info(f"Sending A2A task to worker for lane {lane_id}")

            async for event in a2a_transport.send_message_streaming(params):
                # Mapping A2A events back to OrchestratorEvents
                if isinstance(event, Message):
                    part = event.parts[0]
                    text = ""
                    if hasattr(part, "text"):
                        text = part.text
                    elif hasattr(part, "root") and hasattr(part.root, "text"):
                        text = part.root.text
                    yield OrchestratorEvent(type="result", content=text)
                elif isinstance(event, TaskStatusUpdateEvent):
                    # Could extract "thoughts" here if the worker sends them in status messages
                    if event.status.message:
                        part = event.status.message.parts[0]
                        text = ""
                        if hasattr(part, "text"):
                            text = part.text
                        elif hasattr(part, "root") and hasattr(part.root, "text"):
                            text = part.root.text
                        yield OrchestratorEvent(type="thought", content=text)
                elif isinstance(event, TaskArtifactUpdateEvent):
                    yield OrchestratorEvent(
                        type="artifact", content=event.artifact.model_dump()
                    )
                elif isinstance(event, Task):
                    # End of task?
                    pass

    async def shutdown_lane(self, channel_id: str) -> None:
        # In a real implementation, we'd need a map to find the workspace_id from channel_id
        # or require the caller to pass more info.
        pass
