"""
# InMemoryBindingTable (Fake Implementation)

A simple, in-memory implementation of the `BindingTable` interface for local
testing and development.

## Implementation Details:
- **Storage**: Uses a Python dictionary mapping (Protocol, Channel, Author) triplets to
  `WorkspaceContext` objects.
- **JIT Logic**: Implements a simple heuristic where a new workspace is auto-created
  based on IDs if not found.
- **Persistence**: Data is ephemeral and lost when the process terminates.

## Best Practices:
Use this implementation for:
- Unit testing the `A2AOrchestrator`.
- Local development without a database or K8s.
"""

from kube_claw.binding.table import BindingTable, WorkspaceContext


class InMemoryBindingTable(BindingTable):
    """
    A simple in-memory implementation of the BindingTable for testing.
    """

    def __init__(self) -> None:
        # Key: (protocol, channel_id, author_id)
        self._table: dict[tuple[str, str, str], WorkspaceContext] = {}

    async def resolve_workspace(
        self, protocol: str, channel_id: str, author_id: str
    ) -> WorkspaceContext:
        key = (protocol, channel_id, author_id)

        # If not found, return a default workspace context (JIT logic)
        if key not in self._table:
            # Simple heuristic: workspace_id is author_id or channel_id
            workspace_id = f"workspace-{protocol}-{channel_id}-{author_id}"
            self._table[key] = WorkspaceContext(
                workspace_id=workspace_id, metadata={"status": "provisioned_jit"}
            )

        return self._table[key]

    async def update_binding(
        self, protocol: str, channel_id: str, author_id: str, context: WorkspaceContext
    ) -> None:
        key = (protocol, channel_id, author_id)
        self._table[key] = context
