"""
Orchestrator Interface

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
from collections.abc import AsyncIterator
from kube_claw.core_v3.domain.models import InboundMessage, OrchestratorEvent


class Orchestrator(ABC):
    """
    Abstract Base Class for the Orchestrator.

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
