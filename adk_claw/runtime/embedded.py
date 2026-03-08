"""
Embedded Runtime — In-Process Agent Execution.

Runs the adk-coder agent directly in the current process.
Suitable for single-user, single-workspace setups.
Changes CWD to the workspace before execution for tool isolation.
"""

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from google.genai import types as genai_types

from adk_coder.agent_factory import build_runner
from adk_coder.projects import find_project_root, get_project_id
from adk_coder.summarize import summarize_tool_call

from adk_claw.domain.models import EventType, OrchestratorEvent

logger = logging.getLogger(__name__)


class EmbeddedRuntime:
    """
    Runtime that runs the agent embedded in-process.

    Uses ``build_runner()`` from adk-coder and changes CWD to
    the workspace so that agent tools (bash, file editing) operate
    in the correct directory.
    """

    def __init__(
        self,
        model: str | None = None,
        permission_mode: str = "auto",
    ) -> None:
        self._model = model
        self._permission_mode = permission_mode

    async def execute(
        self,
        workspace_path: str,
        message: str,
        lane_key: str,
        session_id: str,
    ) -> AsyncIterator[OrchestratorEvent]:
        """Run one agent turn in-process."""
        ws = Path(workspace_path).resolve()

        # Change CWD so agent tools operate in the workspace
        original_cwd = os.getcwd()
        os.chdir(ws)

        try:
            runner = build_runner(
                model=self._model,
                permission_mode=self._permission_mode,
                workspace_path=ws,
            )

            project_root = find_project_root(ws)
            user_id = get_project_id(project_root)

            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=message)],
            )

            yield OrchestratorEvent(type=EventType.STATUS, content="Thinking...")

            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content,
            ):
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
                                type=EventType.TOKEN,
                                content="\n".join(text_parts),
                            )

        except Exception as e:
            logger.exception("Agent execution failed")
            yield OrchestratorEvent(type=EventType.ERROR, content=f"Agent error: {e}")
        finally:
            os.chdir(original_cwd)
