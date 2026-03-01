import asyncio
import json
import logging
from typing import Any

from kube_claw.core_v3.worker.session import SessionManager

logger = logging.getLogger(__name__)


class WorkerServer:
    """
    UDS Server for Worker-Host communication.
    Implements the 'Worker as Server' pattern listening for the Host.
    Handles the JSON-RPC request/response cycle over the A2A protocol.
    """

    def __init__(self, socket_path: str, session_manager: SessionManager) -> None:
        self.socket_path = socket_path
        self.session_manager = session_manager
        self.server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        """Starts the Unix Domain Socket server."""
        self.server = await asyncio.start_unix_server(
            self.handle_client, path=self.socket_path
        )
        logger.info(f"WorkerServer listening on {self.socket_path}")

    async def stop(self) -> None:
        """Stops the server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WorkerServer stopped.")

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming A2A connection."""
        addr = writer.get_extra_info("peername")
        logger.info(f"Accepted connection from Host: {addr}")

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                request = json.loads(line.decode().strip())
                response = await self._process_request(request)

                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except asyncio.IncompleteReadError:
            logger.info("Host disconnected prematurely.")
        except Exception as e:
            logger.error(f"Error handling request: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Routes the A2A request to the appropriate method."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        logger.info(f"Processing request: {method}")

        try:
            if method == "bootstrap":
                await self.session_manager.bootstrap(params)
                return {"id": request_id, "result": "ok"}

            if not self.session_manager.is_bootstrapped:
                return {"id": request_id, "error": "Worker not bootstrapped"}

            if method == "execute_task":
                # Entrypoint for running a prompt/task via the worker's LLM agent.
                # result = await self.agent.run(params['prompt'])
                return {"id": request_id, "result": "Task executed (Stub)"}

            if method == "call_tool":
                # Tools are now handled via ADK's internal loop or MCP proxying.
                # Direct 'call_tool' from Host is no longer supported in v3.
                return {
                    "id": request_id,
                    "error": "Direct tool calls are deprecated. Use execute_task.",
                }

            if method == "soft_reset":
                await self.session_manager.soft_reset()
                return {"id": request_id, "result": "ok"}

            return {"id": request_id, "error": f"Method {method} not found"}

        except Exception as e:
            logger.error(f"Method {method} failed: {e}")
            return {"id": request_id, "error": str(e)}
