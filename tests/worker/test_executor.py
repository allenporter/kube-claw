"""Tests for ClawAgentExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from kube_claw.worker.executor import ClawAgentExecutor, _load_workspace_prompt


# --- Prompt loading ---


def test_load_workspace_prompt_default() -> None:
    """No workspace path → default prompt."""
    prompt = _load_workspace_prompt(None)
    assert "KubeClaw worker agent" in prompt


def test_load_workspace_prompt_missing_agents_md(tmp_path) -> None:
    """Workspace exists but no AGENTS.md → default prompt."""
    prompt = _load_workspace_prompt(str(tmp_path))
    assert "KubeClaw worker agent" in prompt


def test_load_workspace_prompt_with_agents_md(tmp_path) -> None:
    """Workspace with AGENTS.md → prompt includes its content."""
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# My Project\nUse Python 3.14.\n")
    prompt = _load_workspace_prompt(str(tmp_path))
    assert "My Project" in prompt
    assert "Python 3.14" in prompt
    assert str(tmp_path) in prompt


# --- Executor cancel ---


@pytest.mark.asyncio
async def test_executor_cancel() -> None:
    """Cancel should emit a canceled event."""
    executor = ClawAgentExecutor()
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    event_queue = AsyncMock()

    await executor.cancel(context, event_queue)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]
    assert event.status.state.value == "canceled"
