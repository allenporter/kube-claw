"""Tests for ClawHost."""

import pytest
import tempfile

from kube_claw.host.host import ClawHost


@pytest.fixture
def host(tmp_path) -> ClawHost:
    return ClawHost(workspace_path=str(tmp_path))


def test_host_creates_temp_rpc_dir(host: ClawHost) -> None:
    """Host should create a temp directory for UDS sockets."""
    assert host.rpc_dir.startswith(tempfile.gettempdir())
    assert "kube_claw_" in host.rpc_dir


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
async def test_host_shutdown_no_sandboxes(host: ClawHost) -> None:
    """Shutdown should work cleanly even with no active sandboxes."""
    await host.shutdown()
