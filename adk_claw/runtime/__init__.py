"""
Runtime Protocol — Agent Execution Backend.

Defines the contract for running an agent in a workspace. Concrete
implementations handle where and how the agent executes:

- ``EmbeddedRuntime``: In-process, same event loop.
- ``SubprocessRuntime``: Isolated subprocess with its own CWD (future).
- ``KubeJobRuntime``: K8s Job with PVC-mounted workspace (future).
"""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from adk_claw.domain.models import OrchestratorEvent


@runtime_checkable
class Runtime(Protocol):
    """
    Executes an agent turn in an isolated workspace.

    Implementations control *where* the agent runs (in-process,
    subprocess, container, K8s Job) while the host handles
    routing, cancellation, and event dispatch.
    """

    def execute(
        self,
        workspace_path: str,
        message: str,
        lane_key: str,
        session_id: str,
    ) -> AsyncIterator[OrchestratorEvent]:
        """Run one agent turn, yielding events as they occur.

        Args:
            workspace_path: Absolute path to the workspace root.
            message: The user's message text.
            lane_key: Unique lane identifier for cancellation.
            session_id: Stable session ID for conversation persistence.
        """
        ...
