"""
A2A Orchestrator Interface

This module defines the central 'Brain' of the Claw Core v3 architecture.
The Orchestrator is responsible for:
1. Receiving inbound messages (intents) from a Gateway.
2. Resolving the User/Channel to a Workspace via the BindingTable.
3. Provisioning/Resuming a Sandbox via the SandboxManager.
4. Managing the bidirectional RPC stream (A2A Protocol) between the Host and Worker.
5. Handling 'Tool Hydration' for host-proxied tools (Slack, GitHub, etc.).
6. Streaming thoughts and results back to the original Gateway.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class InboundMessage:
    """A normalized message from any protocol (Discord, Slack, etc.)."""

    protocol: str  # e.g., "discord"
    channel_id: str
    author_id: str
    content: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrchestratorEvent:
    """An event streamed from the Orchestrator back to the caller."""

    type: str  # "thought", "tool_call", "result", "status"
    content: Any
    metadata: dict[str, Any] | None = None


class A2AOrchestrator(ABC):
    """
    Abstract Base Class for the A2A Orchestrator.

    This component coordinates the domain logic and manages the lifecycle
    of an agent interaction.
    """

    @abstractmethod
    async def handle_message(
        self, message: InboundMessage
    ) -> AsyncIterator[OrchestratorEvent]:
        """
        The primary entrypoint for the orchestrator.

        This method should:
        - Resolve the workspace.
        - Start the sandbox.
        - Connect to the RPC socket.
        - Stream the worker's thoughts and tool results back as OrchestratorEvents.
        """
        pass

    @abstractmethod
    async def shutdown_lane(self, channel_id: str) -> None:
        """Forcefully shut down a persistent lane."""
        pass
