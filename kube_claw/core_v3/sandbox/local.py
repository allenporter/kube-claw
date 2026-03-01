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
import sys
import logging
import tempfile
from typing import Any
from pathlib import Path

from .manager import SandboxManager, SandboxStatus

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
        # Map of workspace_id -> (a2a_socket, mcp_socket)
        self._sockets: dict[str, tuple[str, str]] = {}

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

        a2a_socket = self.base_rpc_dir / f"{workspace_id}_a2a.sock"
        mcp_socket = self.base_rpc_dir / f"{workspace_id}_mcp.sock"
        self._sockets[workspace_id] = (str(a2a_socket), str(mcp_socket))

        # Environment for the worker
        env = os.environ.copy()
        env["SOCKET_PATH"] = str(a2a_socket)  # A2A Socket
        env["MCP_SOCKET_PATH"] = str(mcp_socket)  # MCP Socket
        env["WORKSPACE_ID"] = workspace_id

        # Command to run the worker entrypoint
        cmd = [sys.executable, "-m", "kube_claw.core_v3.worker.entrypoint"]

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

            # Wait for A2A socket to be available (Worker is the server)
            for i in range(20):
                if a2a_socket.exists():
                    break

                if process.returncode is not None:
                    # Process died early!
                    stdout, stderr = await process.communicate()
                    logger.error(f"Worker died with code {process.returncode}")
                    logger.error(f"Worker Stderr: {stderr.decode()}")
                    return SandboxStatus(
                        is_running=False,
                        last_known_status=f"CRASHED({process.returncode})",
                        metadata={"stderr": stderr.decode()},
                    )
                await asyncio.sleep(0.5)

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
        sockets = self._sockets.get(workspace_id)

        if not process:
            return SandboxStatus(is_running=False, last_known_status="NOT_FOUND")

        # Check if process is still alive
        if process.returncode is None:
            a2a_path, mcp_path = sockets if sockets else (None, None)
            return SandboxStatus(
                is_running=True,
                last_known_status="RUNNING",
                connection_endpoint=a2a_path,
                mcp_endpoint=mcp_path,
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
        sockets = self._sockets.pop(workspace_id, None)

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

        if sockets:
            for socket_path in sockets:
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
                self._processes.pop(wid, None)
                self._sockets.pop(wid, None)
        return active
