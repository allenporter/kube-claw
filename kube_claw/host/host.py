"""
KubeClaw Host Process — The Control Plane.

The host is the long-running process that:
- Manages the BindingTable (identity → workspace mapping).
- Manages sandboxes (provisioning workers as subprocesses).
- Runs the A2A Orchestrator (routing messages to workers).
- Hosts the MCP server (proxied tools with credential hydration).
- Provides an interface for channels (TUI, Discord, etc.) to connect.
"""

import logging
import tempfile
from collections.abc import AsyncIterator

from kube_claw.binding.fakes import InMemoryBindingTable
from kube_claw.domain.models import (
    ClawIdentity,
    InboundMessage,
    OrchestratorEvent,
    WorkspaceContext,
)
from kube_claw.sandbox.local import LocalSandboxManager
from kube_claw.orchestrator.orchestrator import A2AOrchestratorImpl

logger = logging.getLogger(__name__)


class ClawHost:
    """
    The KubeClaw Host process.

    Wires together the binding table, sandbox manager, and orchestrator.
    Provides a simple interface for channel clients (TUI, Discord, etc.).
    """

    def __init__(self, workspace_path: str | None = None) -> None:
        # Use a temp dir for all worker UDS sockets
        self._rpc_dir = tempfile.mkdtemp(prefix="kube_claw_")
        logger.info(f"RPC socket directory: {self._rpc_dir}")

        self._binding_table = InMemoryBindingTable()
        self._sandbox_manager = LocalSandboxManager(base_rpc_dir=self._rpc_dir)
        self._orchestrator = A2AOrchestratorImpl(
            binding_table=self._binding_table,
            sandbox_manager=self._sandbox_manager,
        )
        self._workspace_path = workspace_path

    async def setup_default_binding(
        self,
        protocol: str = "shell",
        channel_id: str = "local",
        author_id: str = "dev",
        workspace_path: str | None = None,
    ) -> None:
        """Pre-populate the binding table with a default workspace."""
        ws_path = workspace_path or self._workspace_path or "/tmp/kube_claw_workspace"
        context = WorkspaceContext(
            workspace_id=f"workspace-{channel_id}",
            metadata={
                "workspace_path": ws_path,
                "status": "provisioned",
            },
        )
        await self._binding_table.update_binding(
            protocol, channel_id, author_id, context
        )
        logger.info(f"Default binding: {protocol}:{channel_id}:{author_id} → {ws_path}")

    async def handle_message(
        self,
        text: str,
        protocol: str = "shell",
        channel_id: str = "local",
        author_id: str = "dev",
    ) -> AsyncIterator[OrchestratorEvent]:
        """Send a message through the full orchestration pipeline."""
        identity = ClawIdentity(
            protocol=protocol,
            author_id=author_id,
        )
        message = InboundMessage(
            identity=identity,
            channel_id=channel_id,
            content=text,
        )

        async for event in self._orchestrator.handle_message(message):
            yield event

    async def shutdown(self) -> None:
        """Clean up all sandboxes and resources."""
        active = await self._sandbox_manager.list_active_sandboxes()
        for wid in active:
            await self._sandbox_manager.terminate(wid)
        logger.info("Host shutdown complete.")

    @property
    def rpc_dir(self) -> str:
        return self._rpc_dir
