import pytest
from kube_claw.core_v3.binding.fakes import InMemoryBindingTable


@pytest.mark.asyncio
async def test_in_memory_binding_table_jit():
    table = InMemoryBindingTable()

    # Test JIT provisioning
    context = await table.resolve_workspace("discord", "channel-1", "user-1")
    assert context.workspace_id == "workspace-discord-channel-1-user-1"

    # Test persistence in memory
    context2 = await table.resolve_workspace("discord", "channel-1", "user-1")
    assert context.workspace_id == context2.workspace_id


@pytest.mark.asyncio
async def test_update_binding():
    table = InMemoryBindingTable()
    from kube_claw.core_v3.binding.table import WorkspaceContext

    new_context = WorkspaceContext(workspace_id="manual-id", metadata={"foo": "bar"})
    await table.update_binding("slack", "C123", "U456", new_context)

    resolved = await table.resolve_workspace("slack", "C123", "U456")
    assert resolved.workspace_id == "manual-id"
    assert resolved.metadata["foo"] == "bar"
