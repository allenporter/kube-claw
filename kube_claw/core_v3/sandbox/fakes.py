"""
# FakeSandboxManager (Fake Implementation)

A fake implementation of the `SandboxManager` interface for local testing
and development.

## Implementation Details:
- **Execution**: Does NOT actually launch containers (Docker/K8s).
- **Simulations**: Mimics a "Warm Lane" status, providing a mock UDS endpoint
  (`/tmp/claw-{workspace_id}.sock`).
- **Lifecycle**: Keeps track of "active" workspaces in an internal dictionary.

## Best Practices:
Use this implementation for:
- Testing the `Orchestrator`'s lifecycle logic.
- Developing the A2A handshake protocol without infrastructure dependencies.
"""

from typing import Any

from kube_claw.core_v3.sandbox.manager import SandboxManager, SandboxStatus


class FakeSandboxManager(SandboxManager):
    """
    A fake implementation of the SandboxManager for testing.
    Does not actually launch containers.
    """

    def __init__(self) -> None:
        self._sandboxes: dict[str, SandboxStatus] = {}

    async def provision(
        self, workspace_id: str, context: dict[str, Any] | None = None
    ) -> SandboxStatus:
        # Simulate provisioning
        status = SandboxStatus(
            is_running=True,
            last_known_status="RUNNING",
            connection_endpoint=f"/tmp/claw-{workspace_id}.sock",
            metadata={"type": "fake"},
        )
        self._sandboxes[workspace_id] = status
        return status

    async def get_status(self, workspace_id: str) -> SandboxStatus:
        return self._sandboxes.get(
            workspace_id, SandboxStatus(is_running=False, last_known_status="NOT_FOUND")
        )

    async def terminate(self, workspace_id: str) -> None:
        if workspace_id in self._sandboxes:
            del self._sandboxes[workspace_id]

    async def list_active_sandboxes(self) -> list[str]:
        return list(self._sandboxes.keys())
