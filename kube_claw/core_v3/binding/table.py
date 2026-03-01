"""
# Binding Table Interface (Repository Pattern)

The Binding Table is the primary identity-to-workspace resolver for Claw Core.
Its responsibility is to map external protocol identities (e.g., a Discord User ID
within a specific Channel) to a persistent "Workspace" and "Auth Profile".

## Key Responsibilities:
- **Identity Resolution**: Translating (Protocol, Channel, Author) triplets into a `WorkspaceContext`.
- **JIT Provisioning**: Dynamically creating new workspace mappings when an unknown identity
  first interacts with the system.
- **Context Management**: Storing the current session state and credentials (e.g., GitHub tokens)
  associated with a workspace.

## Architectural Role:
This component acts as a **Repository** in the Domain layer, decoupling the specific storage
(e.g., SQLite, PostgreSQL, K8s CRDs) from the orchestration logic.
"""

from abc import ABC, abstractmethod

from kube_claw.core_v3.domain.models import WorkspaceContext


class BindingTable(ABC):
    """
    Repository for mapping inbound protocol identities to workspace contexts.
    """

    @abstractmethod
    async def resolve_workspace(
        self, protocol: str, channel_id: str, author_id: str
    ) -> WorkspaceContext:
        """
        Maps a (Protocol, Channel, Author) triplet to a WorkspaceContext.
        Should handle JIT provisioning if no binding exists.
        """
        pass

    @abstractmethod
    async def update_binding(
        self, protocol: str, channel_id: str, author_id: str, context: WorkspaceContext
    ) -> None:
        """
        Updates or creates a binding.
        """
        pass
