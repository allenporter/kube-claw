import pytest
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from kube_claw.core_v3.infrastructure.local_sandbox import LocalSandboxManager


@pytest.fixture
def temp_rpc_dir():
    """Provides a temporary directory for UDS sockets."""
    tmp_dir = tempfile.mkdtemp(prefix="claw_rpc_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
async def test_local_sandbox_provision_and_terminate(temp_rpc_dir):
    """
    Verifies that the LocalSandboxManager can spawn and kill a worker process.
    """
    manager = LocalSandboxManager(base_rpc_dir=temp_rpc_dir)
    workspace_id = "test_workspace_01"

    # 1. Provision (Spawns the worker entrypoint)
    status = await manager.provision(workspace_id, {})

    assert status.is_running is True
    assert status.last_known_status == "RUNNING"
    assert status.connection_endpoint is not None
    assert Path(status.connection_endpoint).exists()
    assert workspace_id in (await manager.list_active_sandboxes())

    # 2. Terminate
    await manager.terminate(workspace_id)

    # 3. Verify status after termination
    status_after = await manager.get_status(workspace_id)
    assert status_after.is_running is False
    assert workspace_id not in (await manager.list_active_sandboxes())
    assert not Path(status.connection_endpoint).exists()


@pytest.mark.asyncio
async def test_local_sandbox_multiple_workspaces(temp_rpc_dir):
    """
    Verifies that the manager can handle multiple isolated worker processes.
    """
    manager = LocalSandboxManager(base_rpc_dir=temp_rpc_dir)

    ws1 = "ws_1"
    ws2 = "ws_2"

    status1 = await manager.provision(ws1, {})
    status2 = await manager.provision(ws2, {})

    assert status1.is_running is True
    assert status2.is_running is True
    assert status1.connection_endpoint != status2.connection_endpoint

    active = await manager.list_active_sandboxes()
    assert ws1 in active
    assert ws2 in active

    await manager.terminate(ws1)
    await manager.terminate(ws2)


@pytest.mark.asyncio
async def test_worker_bootstrap_and_rpc(temp_rpc_dir):
    """
    Verifies that we can connect to a spawned worker and perform an A2A handshake.
    """
    manager = LocalSandboxManager(base_rpc_dir=temp_rpc_dir)
    workspace_id = "test_rpc_workspace"

    # 1. Spawn worker
    status = await manager.provision(workspace_id, {})
    assert status.is_running is True
    socket_path = status.connection_endpoint

    # 2. Connect to the UDS as the "Host"
    reader, writer = await asyncio.open_unix_connection(socket_path)

    try:
        # 3. Send Bootstrap message
        bootstrap_msg = {
            "id": 1,
            "method": "bootstrap",
            "params": {
                "session_id": "test_session_123",
                "workspace_path": "/tmp/fake_workspace",
            },
        }
        writer.write(json.dumps(bootstrap_msg).encode() + b"\n")
        await writer.drain()

        # 4. Read response
        raw_response = await reader.readline()
        response = json.loads(raw_response.decode().strip())

        assert response["id"] == 1
        assert response["result"] == "ok"

        # 5. Test another method (execute_task stub)
        task_msg = {
            "id": 2,
            "method": "execute_task",
            "params": {"prompt": "Hello Worker"},
        }
        writer.write(json.dumps(task_msg).encode() + b"\n")
        await writer.drain()

        raw_response = await reader.readline()
        response = json.loads(raw_response.decode().strip())
        assert response["id"] == 2
        assert "Stub" in response["result"]

    finally:
        writer.close()
        await writer.wait_closed()
        await manager.terminate(workspace_id)
