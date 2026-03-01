import os
import pytest
import shutil
import tempfile
import httpx
from pathlib import Path
from typing import Generator

from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import Message, MessageSendParams, Role, Part, TextPart

from kube_claw.sandbox.local import LocalSandboxManager


@pytest.fixture
def temp_rpc_dir() -> Generator[str, None, None]:
    """Provides a temporary directory for UDS sockets."""
    tmp_dir = tempfile.mkdtemp(prefix="claw_rpc_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.mark.asyncio
async def test_local_sandbox_provision_and_terminate(temp_rpc_dir) -> None:
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
    assert status.mcp_endpoint is not None
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
@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_GENAI_API_KEY"),
    reason="Requires GOOGLE_API_KEY for ADK LlmAgent",
)
async def test_worker_a2a_handshake(temp_rpc_dir) -> None:
    """
    Verifies that we can connect to a spawned worker and perform an A2A handshake.
    """
    manager = LocalSandboxManager(base_rpc_dir=temp_rpc_dir)
    workspace_id = "test_a2a_workspace"

    # 1. Spawn worker
    status = await manager.provision(workspace_id, {})
    assert status.is_running is True
    a2a_endpoint = status.connection_endpoint

    # 2. Connect to the A2A Server over UDS
    transport = httpx.AsyncHTTPTransport(uds=a2a_endpoint)
    async with httpx.AsyncClient(transport=transport) as client:
        a2a_transport = JsonRpcTransport(httpx_client=client, url="http://localhost/")

        # 3. Send a message to the worker
        # (This triggers the ClawAgentExecutor logic with real LLM)
        a2a_message = Message(
            message_id="test-msg-1",
            role=Role.user,
            parts=[Part(root=TextPart(kind="text", text="Say hello"))],
        )
        params = MessageSendParams(message=a2a_message)

        responses = []
        async for event in a2a_transport.send_message_streaming(params):
            if isinstance(event, Message):
                part = event.parts[0]
                if hasattr(part, "text"):
                    responses.append(part.text)
                elif hasattr(part, "root") and hasattr(part.root, "text"):
                    responses.append(part.root.text)

        # 4. Verify we got any response from the worker (LLM output varies)
        assert len(responses) > 0

    await manager.terminate(workspace_id)
