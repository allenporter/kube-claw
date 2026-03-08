"""Tests for ClawHost."""

import pytest

from adk_claw.config import AgentConfig, ClawConfig
from adk_claw.domain.models import EventType, OrchestratorEvent
from adk_claw.host.host import ClawHost


class FakeRuntime:
    """A fake runtime for testing the host without adk-coder."""

    async def execute(
        self,
        workspace_path: str,
        message: str,
        lane_key: str,
        session_id: str,
    ):
        yield OrchestratorEvent(type=EventType.TOKEN, content=f"Echo: {message}")


@pytest.fixture
def host(tmp_path) -> ClawHost:
    return ClawHost(workspace_path=str(tmp_path), runtime=FakeRuntime())


@pytest.mark.asyncio
async def test_host_setup_default_binding(host: ClawHost) -> None:
    """Should be able to set up a default binding without errors."""
    await host.setup_default_binding(
        protocol="shell",
        channel_id="test",
        author_id="dev",
        workspace_path="/tmp/test_ws",
    )


@pytest.mark.asyncio
async def test_host_shutdown(host: ClawHost) -> None:
    """Shutdown should work cleanly."""
    await host.shutdown()


def test_host_uses_config(tmp_path) -> None:
    """Host should accept and use injected config."""
    config = ClawConfig(
        agent=AgentConfig(model="gemini-2.5-pro", permission_mode="plan")
    )
    host = ClawHost(workspace_path=str(tmp_path), config=config, runtime=FakeRuntime())
    assert host.config.agent.model == "gemini-2.5-pro"
    assert host.config.agent.permission_mode == "plan"


def test_host_default_config(tmp_path) -> None:
    """Host with no injected config uses defaults."""
    host = ClawHost(workspace_path=str(tmp_path), runtime=FakeRuntime())
    assert host.config.agent.model is None
    assert host.config.agent.permission_mode == "auto"


@pytest.mark.asyncio
async def test_host_handle_message(host: ClawHost) -> None:
    """Messages should flow through to the runtime."""
    await host.setup_default_binding()

    events = []
    async for event in host.handle_message("hello"):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == EventType.TOKEN
    assert events[0].content == "Echo: hello"


@pytest.mark.asyncio
async def test_host_cancel_run_no_active(host: ClawHost) -> None:
    """Cancel should be a no-op when no run is active."""
    await host.cancel_run("shell:local:dev")
