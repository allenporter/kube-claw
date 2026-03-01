"""
Local Process Sandbox Manager (Infrastructure Implementation)

This Sandbox Manager implementation spawns the Worker Entrypoint as a local
subprocess. This is ideal for development, local testing, and environments
where Docker or Kubernetes is not available.

## Safety & Security:
- **No Isolation**: This does NOT provide security isolation. It runs as the
  current user on the host system.
- **UDS Socket**: Communicates via a Unix Domain Socket created in a temporary
  or specified directory.
- **Lifecycle**: Manages the subprocess life (start, status, stop).
"""

import asyncio
import os
import logging
import tempfile
from typing import Any
from pathlib import Path

from ..interfaces.sandbox_manager import SandboxManager, SandboxStatus

logger = logging.getLogger("claw.infrastructure.local_sandbox")


class LocalSandboxManager(SandboxManager):
    """
    Manages worker processes running as local subprocesses.
    """

    def __init__(self, base_rpc_dir: str | None = None) -> None:
        # Default to a temporary directory if not provided
        self.base_rpc_dir = Path(base_rpc_dir or tempfile.gettempdir()) / "claw_rpc"
        self.base_rpc_dir.mkdir(parents=True, exist_ok=True)

        # Map of workspace_id -> subprocess object
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        # Map of workspace_id -> UDS path
        self._sockets: dict[str, str] = {}

    async def provision(
        self, workspace_id: str, context: dict[str, Any]
    ) -> SandboxStatus:
        """
        Spawns a new worker process for the given workspace.
        """
        if workspace_id in self._processes:
            status = await self.get_status(workspace_id)
            if status.is_running:
                return status
            # If not running, cleanup and restart
            await self.terminate(workspace_id)

        socket_path = self.base_rpc_dir / f"{workspace_id}.sock"
        self._sockets[workspace_id] = str(socket_path)

        # Environment for the worker
        env = os.environ.copy()
        env["SOCKET_PATH"] = str(socket_path)
        env["WORKSPACE_ID"] = workspace_id

        # Command to run the worker entrypoint
        # In a real setup, we might use 'python -m kube_claw.core_v3.worker.entrypoint'
        cmd = ["python3", "-m", "kube_claw.core_v3.worker.entrypoint"]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._processes[workspace_id] = process
            logger.info(
                f"Spawned local worker for workspace '{workspace_id}' (PID: {process.pid})"
            )

            # Wait a moment for the socket to be created
            # In a production version, we'd use a more robust 'wait_for_file' or 'wait_for_socket'
            for _ in range(10):
                if socket_path.exists():
                    break
                await asyncio.sleep(0.1)

            return await self.get_status(workspace_id)

        except Exception as e:
            logger.error(f"Failed to spawn worker for workspace '{workspace_id}': {e}")
            return SandboxStatus(
                is_running=False,
                last_known_status=f"FAILED: {str(e)}",
                metadata={"error": str(e)},
            )

    async def get_status(self, workspace_id: str) -> SandboxStatus:
        """
        Checks if the process for the workspace is still running.
        """
        process = self._processes.get(workspace_id)
        socket_path = self._sockets.get(workspace_id)

        if not process:
            return SandboxStatus(is_running=False, last_known_status="NOT_FOUND")

        # Check if process is still alive
        if process.returncode is None:
            return SandboxStatus(
                is_running=True,
                last_known_status="RUNNING",
                connection_endpoint=socket_path,
                metadata={"pid": process.pid},
            )
        else:
            return SandboxStatus(
                is_running=False,
                last_known_status=f"EXITED({process.returncode})",
                metadata={"pid": process.pid},
            )

    async def terminate(self, workspace_id: str) -> None:
        """
        Kills the worker process and cleans up.
        """
        process = self._processes.pop(workspace_id, None)
        socket_path = self._sockets.pop(workspace_id, None)

        if process and process.returncode is None:
            logger.info(
                f"Terminating worker for workspace '{workspace_id}' (PID: {process.pid})"
            )
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        if socket_path and os.path.exists(socket_path):
            try:
                os.remove(socket_path)
            except OSError:
                pass

    async def list_active_sandboxes(self) -> list[str]:
        """
        Returns active workspace IDs.
        """
        active = []
        for wid in list(self._processes.keys()):
            status = await self.get_status(wid)
            if status.is_running:
                active.append(wid)
            else:
                # Cleanup dead processes
                self._processes.pop(wid, None)
                self._sockets.pop(wid, None)
        return active
