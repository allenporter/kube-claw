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
from typing import Any

from google.genai import types as genai_types

from adk_coder.agent_factory import build_runner
from adk_coder.projects import find_project_root, get_project_id
from adk_coder.summarize import summarize_tool_call
from adk_claw.domain.models import EventType, OrchestratorEvent
from adk_claw.memory import FileMemoryStore
from adk_claw.mcp.memory_tool import MemoryToolSet
from adk_claw.runtime.mcp_support import McpSupport

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
        self._runners: dict[str, Any] = {}

        # Initialize memory store in ~/.adk-claw/memory
        base_memory_path = Path.home() / ".adk-claw" / "memory"
        self._memory_store = FileMemoryStore(base_memory_path)

    async def execute(
        self,
        workspace_path: str,
        message: str,
        lane_key: str,
        session_id: str,
        env: dict[str, str] | None = None,
        mcp: dict[str, Any] | None = None,
    ) -> AsyncIterator[OrchestratorEvent]:
        """Run one agent turn in-process."""
        ws = Path(workspace_path).resolve()

        # Update environment with workspace-specific variables
        original_env = os.environ.copy()
        if env:
            os.environ.update(env)

        # Wire external MCP servers
        mcp_support = McpSupport(mcp or {})
        mcp_args = mcp_support.get_toolset_args()

        # Change CWD so agent tools operate in the workspace
        original_cwd = os.getcwd()
        os.chdir(ws)

        try:
            runner = self._runners.get(session_id)
            if not runner:
                logger.info(f"Building new runner for session {session_id}")

                # Gather all extra tools
                extra_tools = list(mcp_args.get("extra_tools") or [])

                # Add Memory tools
                memory_tools = MemoryToolSet(
                    self._memory_store, workspace_id=session_id
                )
                extra_tools.extend(memory_tools.get_tools())

                runner = build_runner(
                    model=self._model,
                    permission_mode=self._permission_mode,
                    workspace_path=ws,
                    extra_tools=extra_tools,
                )
                self._runners[session_id] = runner
            else:
                logger.debug(f"Reusing cached runner for session {session_id}")

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
            os.environ.clear()
            os.environ.update(original_env)
