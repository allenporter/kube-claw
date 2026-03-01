import pytest
from kube_claw.sandbox.fakes import FakeSandboxManager


@pytest.mark.asyncio
async def test_fake_sandbox_lifecycle():
    manager = FakeSandboxManager()
    workspace_id = "test-ws"

    # Test provisioning
    status = await manager.provision(workspace_id)
    assert status.is_running is True
    assert status.connection_endpoint == f"/tmp/claw-{workspace_id}.sock"

    # Test status
    current_status = await manager.get_status(workspace_id)
    assert current_status.is_running is True

    # Test listing
    active = await manager.list_active_sandboxes()
    assert workspace_id in active

    # Test termination
    await manager.terminate(workspace_id)
    status_after = await manager.get_status(workspace_id)
    assert status_after.is_running is False


@pytest.mark.asyncio
async def test_non_existent_sandbox():
    manager = FakeSandboxManager()
    status = await manager.get_status("does-not-exist")
    assert status.is_running is False
    assert status.last_known_status == "NOT_FOUND"
