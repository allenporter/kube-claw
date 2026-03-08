"""Tests for ClawHost."""

import pytest

from adk_claw.host.host import ClawHost


@pytest.fixture
def host(tmp_path) -> ClawHost:
    return ClawHost(workspace_path=str(tmp_path))


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
