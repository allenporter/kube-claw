"""
ClawAgentExecutor — ADK-powered Worker Brain.

This executor runs inside the sandbox and uses ADK's LlmAgent with McpToolset
to perform reasoning with real Gemini LLM calls and host-proxied MCP tools.

Phase 1 (Init):
  - Reads AGENTS.md from the workspace to build the system prompt.
  - Connects to the Host's MCP server via McpToolset for tool discovery.

Phase 2 (Reasoning Loop):
  - Runs the LlmAgent with the user's message.
  - Streams status events (thoughts) and the final result back via A2A.
"""

import logging
import os
from pathlib import Path

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

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# Default system prompt if AGENTS.md is not found.
_DEFAULT_INSTRUCTION = (
    "You are a KubeClaw worker agent. You help the user with coding tasks. "
    "You have access to host-side tools via MCP for git operations, "
    "GitHub API calls, and requesting user approval for destructive actions. "
    "Use these tools when appropriate."
)


def _load_workspace_prompt(workspace_path: str | None) -> str:
    """Load the system prompt from AGENTS.md in the workspace."""
    if not workspace_path:
        return _DEFAULT_INSTRUCTION

    agents_md = Path(workspace_path) / "AGENTS.md"
    if agents_md.exists():
        content = agents_md.read_text()
        logger.info(f"Loaded system prompt from {agents_md}")
        return (
            f"You are a KubeClaw worker agent operating in workspace: {workspace_path}\n\n"
            f"## Workspace Instructions\n{content}\n\n"
            "You have access to host-side tools via MCP. Use them when the user's "
            "request requires git operations, GitHub API calls, or other host-proxied actions."
        )

    logger.info(f"No AGENTS.md found at {agents_md}, using default prompt.")
    return _DEFAULT_INSTRUCTION


class ClawAgentExecutor(AgentExecutor):
    """
    ADK-powered AgentExecutor for KubeClaw v3.

    Uses LlmAgent with Gemini for reasoning and McpToolset for
    host-proxied tool calls.
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Run the ADK agent reasoning loop for a single user message."""

        # --- Phase 1: Init ---
        workspace_path = os.getenv("CLAW_WORKSPACE")
        instruction = _load_workspace_prompt(workspace_path)

        # Build ADK agent (without MCP for now — will be wired in when
        # the host MCP server is connected via McpToolset).
        agent = LlmAgent(
            model="gemini-2.5-flash",
            name="claw_worker",
            instruction=instruction,
        )

        # --- Phase 2: Extract user message ---
        user_message = context.message
        prompt = ""
        if user_message and user_message.parts:
            part = user_message.parts[0]
            if hasattr(part, "text"):
                prompt = str(part.text)
            elif hasattr(part, "root") and hasattr(part.root, "text"):
                prompt = str(part.root.text)
            elif isinstance(part, dict):
                prompt = str(part.get("text", ""))

        logger.info(f"Executing task for prompt: {prompt!r}")

        # Send a "thinking" status update
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
                                    text="Reasoning with Gemini...",
                                )
                            )
                        ],
                    ),
                ),
            )
        )

        # --- Phase 3: Run ADK Agent ---
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="kube_claw_worker",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="kube_claw_worker",
            user_id=context.context_id or "default_user",
        )

        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt)],
        )

        result_text = ""
        try:
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=user_content,
            ):
                # Collect the final agent response
                if event.is_final_response():
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                result_text += part.text
        except Exception as e:
            logger.exception("ADK Runner failed")
            result_text = f"Error during LLM execution: {e}"

        if not result_text:
            result_text = "I processed your request but have no additional output."

        # --- Send final result ---
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
                            text=result_text,
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
