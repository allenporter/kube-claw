import asyncio
import logging
import uvicorn

from starlette.applications import Starlette
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from .executor import ClawAgentExecutor

logger = logging.getLogger(__name__)


class WorkerServer:
    """
    UDS Server for Worker-Host communication using the A2A SDK.
    """

    def __init__(self, socket_path: str) -> None:
        self.socket_path = socket_path
        self.app = self._build_app()

    def _build_app(self) -> Starlette:
        # 1. Define Agent Capabilities
        card = AgentCard(
            name="ClawWorker",
            description="KubeClaw Sandboxed Worker",
            version="0.3.0",
            url="http://localhost/",
            capabilities=AgentCapabilities(streaming=True, push_notifications=True),
            skills=[
                AgentSkill(
                    id="reasoning-01",
                    name="reasoning",
                    description="General reasoning skill",
                    tags=["reasoning", "general"],
                )
            ],
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
        )

        # 2. Setup A2A Infrastructure
        task_store = InMemoryTaskStore()
        executor = ClawAgentExecutor()
        handler = DefaultRequestHandler(executor, task_store)

        a2a_app = A2AStarletteApplication(agent_card=card, http_handler=handler)
        return a2a_app.build()

    async def start(self) -> None:
        """Starts the UDS server using uvicorn."""
        config = uvicorn.Config(self.app, uds=self.socket_path, log_level="info")
        server = uvicorn.Server(config)
        # Run in background
        asyncio.create_task(server.serve())
        logger.info(f"WorkerServer listening on {self.socket_path}")

    async def stop(self) -> None:
        """Stops the server."""
        # Uvicorn stop is handled by the process exit or signal handlers in entrypoint
        pass
