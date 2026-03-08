"""Tests for the Runtime protocol and implementations."""

from adk_claw.domain.models import EventType, OrchestratorEvent
from adk_claw.runtime import Runtime


class FakeRuntime:
    """Minimal Runtime satisfying the protocol."""

    async def execute(
        self,
        workspace_path: str,
        message: str,
        lane_key: str,
        session_id: str,
    ):
        yield OrchestratorEvent(type=EventType.TOKEN, content="ok")


def test_runtime_protocol_check() -> None:
    """Classes implementing execute() satisfy the Runtime protocol."""
    assert isinstance(FakeRuntime(), Runtime)
