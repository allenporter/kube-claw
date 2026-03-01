"""
Worker Entrypoint (The "Hand" inside the Sandbox)

This is the main process that runs within the execution sandbox (Docker/K8s).
Its primary responsibilities are:
1. Initialize the Unix Domain Socket (UDS) server.
2. Handle OS signals (SIGTERM/SIGINT) for graceful shutdown.
3. Manage the A2A Orchestrator lifecycle (IDLE -> BOOTSTRAPPED -> WORKING).
4. Route tool calls and agent reasoning via ADK.
"""

import asyncio
import signal
import os
import logging

from kube_claw.worker.server import WorkerServer

# Setup basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("claw.worker")


class WorkerEntrypoint:
    """
    Coordinates the lifecycle of the sandboxed worker process.
    """

    def __init__(self, socket_path: str | None = None) -> None:
        self.socket_path = socket_path or os.getenv("SOCKET_PATH", "/rpc/worker.sock")
        self.stop_event = asyncio.Event()
        self._server: WorkerServer | None = None

    async def run(self) -> None:
        """
        Starts the UDS server and waits for the stop signal.
        """
        logger.info(f"Starting Worker Entrypoint on {self.socket_path}...")

        # Ensure directory exists for UDS
        socket_dir = os.path.dirname(self.socket_path)
        if socket_dir and not os.path.exists(socket_dir):
            os.makedirs(socket_dir, exist_ok=True)

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        # Initialize and start the WorkerServer
        self._server = WorkerServer(self.socket_path)
        await self._server.start()

        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop)

        logger.info("Worker is ready and listening.")
        await self.stop_event.wait()
        await self.shutdown()

    def stop(self) -> None:
        """Signals the worker to stop."""
        logger.info("Shutdown signal received.")
        self.stop_event.set()

    async def shutdown(self) -> None:
        """Gracefully shuts down the worker."""
        logger.info("Cleaning up resources...")
        if self._server:
            await self._server.stop()

        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass

        logger.info("Worker shutdown complete.")


if __name__ == "__main__":
    worker = WorkerEntrypoint()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        pass
