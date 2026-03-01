"""
# Sandbox Manager Interface (Strategy Pattern)

The Sandbox Manager is the infrastructure-agnostic gateway for managing the
lifecycle of the agent's execution environment (or "Lane").

## Key Responsibilities:
- **Provisioning**: Initializing and starting a sandbox (e.g., a Kubernetes Pod,
  Docker Container, or local process).
- **Status Monitoring**: Tracking if a sandbox is RUNNING, INITIALIZING, or FAILED.
- **Connection Management**: Providing the endpoint (UDS path or TCP address)
  for the `Orchestrator` to connect to the Worker.
- **Cleanup**: Terminating and garbage-collecting sandboxes when tasks are complete
  or the "Warm Lane" timeout is reached.

## Architectural Role:
This component acts as a **Strategy** in the Infrastructure layer, allowing the Core
to run in various environments (local, Kubernetes, etc.) by swapping the concrete
implementation.
"""

from typing import Any
from abc import ABC, abstractmethod
from ..domain.models import SandboxStatus


class SandboxManager(ABC):
    """
    Lifecycle manager for worker environments (Lanes).
    """

    @abstractmethod
    async def provision(
        self, workspace_id: str, context: dict[str, Any]
    ) -> SandboxStatus:
        """
        Creates or updates a sandbox/lane for a given workspace.
        """
        pass

    @abstractmethod
    async def get_status(self, workspace_id: str) -> SandboxStatus:
        """
        Queries the current status of the sandbox for a given workspace.
        """
        pass

    @abstractmethod
    async def terminate(self, workspace_id: str) -> None:
        """
        Shuts down the sandbox for a given workspace.
        """
        pass

    @abstractmethod
    async def list_active_sandboxes(self) -> list[str]:
        """
        Returns a list of all workspace IDs with active sandboxes.
        """
        pass
