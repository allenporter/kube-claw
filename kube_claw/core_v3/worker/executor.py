import logging
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    Message,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
    Role,
    Part,
    TextPart,
)
from .mcp_client import WorkerMCPClient
import os

logger = logging.getLogger(__name__)


class ClawAgentExecutor(AgentExecutor):
    """
    Concrete AgentExecutor for KubeClaw v3.
    Uses ADK reasoning and interacts with host-side tools via MCP.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # 1. Setup MCP Client
        mcp_socket = os.getenv("MCP_SOCKET_PATH")
        mcp_client = None
        if mcp_socket:
            mcp_client = WorkerMCPClient(mcp_socket)
            logger.info(f"Worker connected to Host MCP at {mcp_socket}")

        # 2. Extract Task/Message
        user_message = context.message
        prompt = ""
        if user_message and user_message.parts:
            part = user_message.parts[0]
            if hasattr(part, "text"):
                prompt = part.text
            elif hasattr(part, "root") and hasattr(part.root, "text"):
                prompt = part.root.text
            elif isinstance(part, dict):
                prompt = part.get("text", "")

        # 3. Simulate Reasoning Loop (Hydrating with Git Info)
        # In the future, this would use a real ADK agent.
        logger.info(f"Executing task for prompt: {prompt}")

        # Send a "thought" update
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=False,
                status=TaskStatus(
                    state=TaskState.working,
                    message=Message(
                        message_id="thought-1",
                        role=Role.agent,
                        parts=[
                            Part(
                                root=TextPart(
                                    kind="text",
                                    text="I'm checking the current git state...",
                                )
                            )
                        ],
                    ),
                ),
            )
        )

        # Call host tool if available
        if mcp_client:
            try:
                res = await mcp_client.call_tool("git_info", {})
                if res and res.content:
                    git_info = res.content[0].text
                    await event_queue.enqueue_event(
                        TaskStatusUpdateEvent(
                            task_id=context.task_id or "",
                            context_id=context.context_id or "",
                            final=False,
                            status=TaskStatus(
                                state=TaskState.working,
                                message=Message(
                                    message_id="thought-2",
                                    role=Role.agent,
                                    parts=[
                                        Part(
                                            root=TextPart(
                                                kind="text",
                                                text=f"Found git info: {git_info}",
                                            )
                                        )
                                    ],
                                ),
                            ),
                        )
                    )
            except Exception as e:
                logger.error(f"MCP Call failed: {e}")

        # Final Result
        await event_queue.enqueue_event(
            Message(
                message_id="final-result",
                role=Role.agent,
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                parts=[
                    Part(
                        root=TextPart(
                            kind="text",
                            text=f"I've completed your request: {prompt}. All look good!",
                        )
                    )
                ],
            )
        )

        # Close task
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=True,
                status=TaskStatus(state=TaskState.completed),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.info(f"Cancellation requested for task {context.task_id}")
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=True,
                status=TaskStatus(state=TaskState.canceled),
            )
        )
