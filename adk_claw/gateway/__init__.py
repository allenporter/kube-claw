"""
Channel Adapter Protocol.

Defines the contract for adapting external channels (Discord, CLI, GitHub, etc.)
to the KubeClaw gateway. Each adapter normalizes its channel's input format
into InboundMessage and routes OrchestratorEvent back to the user.

See: 12-agent-core.md §Q2 (Gateway Extensibility)
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChannelAdapter(Protocol):
    """
    Adapts a specific channel to the KubeClaw gateway.

    Each adapter is responsible for:
    - Listening to its channel (Discord, CLI, GitHub webhooks, etc.)
    - Normalizing incoming messages into InboundMessage
    - Calling the host's handle_message()
    - Routing OrchestratorEvent back to the user's channel
    """

    async def start(self) -> None:
        """Start listening on the channel."""
        ...

    async def stop(self) -> None:
        """Stop listening and clean up resources."""
        ...
