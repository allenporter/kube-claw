"""
adk-claw Host — The Control Plane.

The host is the long-running process that:
- Loads configuration from YAML (global + project).
- Manages the BindingTable (identity → workspace mapping).
- Routes messages to a Runtime backend for agent execution.
- Provides an interface for channel adapters (TUI, Discord, etc.).

See: ADR-004 (Embedded Executor Architecture)
"""

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from adk_claw.binding.fakes import InMemoryBindingTable
from adk_claw.config import ClawConfig, load_config
from adk_claw.domain.models import (
    ClawIdentity,
    InboundMessage,
    OrchestratorEvent,
    WorkspaceContext,
)
from adk_claw.runtime import Runtime
from adk_claw.runtime.embedded import EmbeddedRuntime
from adk_claw.host.queue.manager import QueueManager
from typing import Any

logger = logging.getLogger(__name__)


class ClawHost:
    """
    The adk-claw Host process.

    Wires together configuration, binding table, and runtime.
    Resolves workspaces, manages cancellation, and provides
    a simple interface for channel adapters.
    """

    def __init__(
        self,
        workspace_path: str | None = None,
        config: ClawConfig | None = None,
        runtime: Runtime | None = None,
    ) -> None:
        ws = Path(workspace_path) if workspace_path else None
        self._config = config or load_config(workspace_path=ws)
        self._binding_table = InMemoryBindingTable()
        self._runtime = runtime or EmbeddedRuntime(
            model=self._config.agent.model,
            permission_mode=self._config.agent.permission_mode,
        )
        self._workspace_path = workspace_path
        self._queue_manager = QueueManager(execute_fn=self._execute_message)

    @property
    def config(self) -> ClawConfig:
        """The active configuration."""
        return self._config

    async def setup_default_binding(
        self,
        protocol: str = "shell",
        channel_id: str = "local",
        author_id: str = "dev",
        workspace_path: str | None = None,
    ) -> None:
        """Pre-populate the binding table with a default workspace."""
        ws_path = workspace_path or self._workspace_path or "/tmp/adk_claw_workspace"
        context = WorkspaceContext(
            workspace_id=f"workspace-{channel_id}",
            metadata={
                "workspace_path": ws_path,
                "status": "ready",
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
        """Route message through the sequential lane queue."""
        identity = ClawIdentity(protocol=protocol, author_id=author_id)
        message = InboundMessage(
            identity=identity,
            channel_id=channel_id,
            content=text,
        )
        lane_key = message.lane_id

        async for event in self._queue_manager.handle_message(
            lane_key=lane_key, text=text
        ):
            yield event

    async def _execute_message(
        self, text: str, lane_key: str, **kwargs: Any
    ) -> AsyncIterator[OrchestratorEvent]:
        """Execute a message turn, resolving workspace and config."""
        # Split lane_key back into protocol, channel_id, author_id
        # lane_id is f"{self.identity.protocol}:{self.channel_id}:{self.identity.author_id}"
        parts = lane_key.split(":")
        if len(parts) != 3:
            # Fallback for unexpected lane keys
            protocol, channel_id, author_id = "unknown", "unknown", "unknown"
        else:
            protocol, channel_id, author_id = parts

        # Resolve workspace
        context = await self._binding_table.resolve_workspace(
            protocol, channel_id, author_id
        )
        workspace_path = context.metadata.get("workspace_path", os.getcwd())

        # Load workspace-specific config
        ws = Path(workspace_path)
        ws_config = load_config(workspace_path=ws)

        logger.info(
            f"Executing message for lane={lane_key}, workspace={workspace_path}"
        )

        # Execute via runtime
        async for event in self._runtime.execute(
            workspace_path=workspace_path,
            message=text,
            lane_key=lane_key,
            session_id=lane_key,
            env=ws_config.agent.env,
            mcp=ws_config.mcp_servers,
        ):
            yield event

    async def cancel_run(self, lane_key: str) -> None:
        """Cancel an in-progress agent run."""
        self._queue_manager.cancel_run(lane_key)

    async def shutdown(self) -> None:
        """Clean up resources."""
        await self._queue_manager.shutdown()
        logger.info("Host shutdown complete.")
