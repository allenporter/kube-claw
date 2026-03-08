"""
adk-claw Host Process — The Control Plane.

The host is the long-running process that:
- Loads configuration from YAML (global + project).
- Manages the BindingTable (identity → workspace mapping).
- Runs the Embedded Orchestrator (in-process agent execution).
- Provides an interface for channel adapters (TUI, Discord, etc.).

See: ADR-004 (Embedded Executor Architecture)
"""

import logging
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
from adk_claw.orchestrator.embedded import EmbeddedOrchestrator

logger = logging.getLogger(__name__)


class ClawHost:
    """
    The adk-claw Host process.

    Wires together configuration, binding table, and embedded orchestrator.
    Provides a simple interface for channel adapters (TUI, Discord, etc.).
    """

    def __init__(
        self,
        workspace_path: str | None = None,
        config: ClawConfig | None = None,
    ) -> None:
        ws = Path(workspace_path) if workspace_path else None
        self._config = config or load_config(workspace_path=ws)
        self._binding_table = InMemoryBindingTable()
        self._orchestrator = EmbeddedOrchestrator(
            binding_table=self._binding_table,
            model=self._config.agent.model,
            permission_mode=self._config.agent.permission_mode,
        )
        self._workspace_path = workspace_path

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
        """Clean up resources."""
        logger.info("Host shutdown complete.")
