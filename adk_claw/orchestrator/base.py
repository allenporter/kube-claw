"""
Orchestrator Interface

This module defines the central 'Brain' of the Claw Core v3 architecture.

The Orchestrator is responsible for:
1. Receiving inbound messages (intents) from a Gateway / ChannelAdapter.
2. Resolving the User/Channel to a Workspace via the BindingTable.
3. Invoking the embedded agent executor (ADK LlmAgent).
4. Streaming thoughts and results back to the caller as OrchestratorEvents.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from adk_claw.domain.models import InboundMessage, OrchestratorEvent


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
        - Resolve the workspace via the BindingTable.
        - Invoke the embedded agent executor.
        - Stream thoughts and results back as OrchestratorEvents.
        """
        pass

    @abstractmethod
    async def cancel_run(self, lane_key: str) -> None:
        """Cancel an in-progress agent run for the given lane."""
        pass
