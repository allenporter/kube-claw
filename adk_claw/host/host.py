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
        self._active_runs: dict[str, bool] = {}

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
        """Send a message through the full pipeline: resolve → execute → stream."""
        identity = ClawIdentity(protocol=protocol, author_id=author_id)
        message = InboundMessage(
            identity=identity,
            channel_id=channel_id,
            content=text,
        )

        lane_key = message.lane_id

        # Resolve workspace
        context = await self._binding_table.resolve_workspace(
            protocol, channel_id, author_id
        )
        workspace_path = context.metadata.get("workspace_path", os.getcwd())

        # Load workspace-specific config
        ws = Path(workspace_path)
        ws_config = load_config(workspace_path=ws)

        logger.info(
            f"Handling message for lane={lane_key}, workspace={workspace_path}, "
            f"env_keys={list(ws_config.agent.env.keys())}"
        )

        # Execute via runtime
        self._active_runs[lane_key] = True
        session_id = lane_key

        try:
            async for event in self._runtime.execute(
                workspace_path=workspace_path,
                message=text,
                lane_key=lane_key,
                session_id=session_id,
                env=ws_config.agent.env,
                mcp=ws_config.mcp_servers,
            ):
                if not self._active_runs.get(lane_key, False):
                    logger.info(f"Run cancelled for lane {lane_key}")
                    break
                yield event
        finally:
            self._active_runs.pop(lane_key, None)

    async def cancel_run(self, lane_key: str) -> None:
        """Cancel an in-progress agent run."""
        if lane_key in self._active_runs:
            self._active_runs[lane_key] = False
            logger.info(f"Cancellation requested for lane {lane_key}")

    async def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Host shutdown complete.")
