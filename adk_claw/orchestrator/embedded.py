"""
Embedded Orchestrator — In-Process Agent Executor.

Implements the Orchestrator interface using adk-coder's agent factory
to run the ADK LlmAgent directly in-process. Uses adk-coder's
build_runner() for session persistence, compaction, and security.

See: ADR-004 (Embedded Executor Architecture)
See: 12-agent-core.md (Agent Core Integration)
"""

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from google.genai import types as genai_types

from adk_coder.agent_factory import build_runner
from adk_coder.projects import find_project_root, get_project_id
from adk_coder.summarize import summarize_tool_call

from adk_claw.binding.table import BindingTable
from adk_claw.domain.models import EventType, InboundMessage, OrchestratorEvent

from .base import Orchestrator

logger = logging.getLogger(__name__)


class EmbeddedOrchestrator(Orchestrator):
    """
    Orchestrator that runs the agent embedded in-process.

    Uses adk-coder's build_runner() to create a fully-configured Runner
    with LlmAgent, SqliteSessionService, and EventsCompactionConfig.
    """

    def __init__(
        self,
        binding_table: BindingTable,
        model: str | None = None,
        permission_mode: str = "auto",
    ) -> None:
        self.binding_table = binding_table
        self._model = model
        self._permission_mode = permission_mode
        self._active_runs: dict[str, bool] = {}

    async def handle_message(  # type: ignore[override]
        self, message: InboundMessage
    ) -> AsyncIterator[OrchestratorEvent]:
        lane_key = message.lane_id

        # 1. Resolve workspace
        context = await self.binding_table.resolve_workspace(
            message.identity.protocol, message.channel_id, message.identity.author_id
        )
        workspace_path = context.metadata.get("workspace_path", os.getcwd())

        logger.info(f"Handling message for lane={lane_key}, workspace={workspace_path}")

        # 2. Build runner from adk-coder (agent + sessions + compaction + security)
        runner = build_runner(
            model=self._model,
            permission_mode=self._permission_mode,
            workspace_path=Path(workspace_path),
        )

        # 3. Derive stable user_id from workspace so sessions persist per-project
        project_root = find_project_root(Path(workspace_path))
        user_id = get_project_id(project_root)

        # Use lane_key as session_id so the same user+channel resumes conversation
        session_id = lane_key

        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=message.content)],
        )

        # 4. Run agent and stream events
        self._active_runs[lane_key] = True

        yield OrchestratorEvent(type=EventType.STATUS, content="Thinking...")

        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content,
            ):
                if not self._active_runs.get(lane_key, False):
                    logger.info(f"Run cancelled for lane {lane_key}")
                    break

                # Stream tool calls as thoughts
                for call in event.get_function_calls():
                    summary = summarize_tool_call(str(call.name), call.args or {})
                    yield OrchestratorEvent(type=EventType.THOUGHT, content=summary)

                # Stream final response
                if event.is_final_response():
                    if event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if p.text]
                        if text_parts:
                            yield OrchestratorEvent(
                                type=EventType.TOKEN, content="\n".join(text_parts)
                            )

        except Exception as e:
            logger.exception("Agent execution failed")
            yield OrchestratorEvent(type=EventType.ERROR, content=f"Agent error: {e}")
        finally:
            self._active_runs.pop(lane_key, None)

    async def cancel_run(self, lane_key: str) -> None:
        """Cancel an in-progress agent run."""
        if lane_key in self._active_runs:
            self._active_runs[lane_key] = False
            logger.info(f"Cancellation requested for lane {lane_key}")
