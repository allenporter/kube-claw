"""Tests for EmbeddedOrchestrator."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from adk_claw.binding.fakes import InMemoryBindingTable
from adk_claw.domain.models import (
    ClawIdentity,
    InboundMessage,
    WorkspaceContext,
)
from adk_claw.orchestrator.embedded import EmbeddedOrchestrator


@pytest.fixture
def binding_table() -> InMemoryBindingTable:
    return InMemoryBindingTable()


@pytest.fixture
def orchestrator(binding_table: InMemoryBindingTable) -> EmbeddedOrchestrator:
    return EmbeddedOrchestrator(binding_table=binding_table)


async def _setup_binding(table: InMemoryBindingTable) -> None:
    await table.update_binding(
        "shell",
        "local",
        "dev",
        WorkspaceContext(
            workspace_id="ws-test",
            metadata={"workspace_path": "/tmp/test"},
        ),
    )


def _make_message(text: str = "hello") -> InboundMessage:
    return InboundMessage(
        identity=ClawIdentity(protocol="shell", author_id="dev"),
        channel_id="local",
        content=text,
    )


@pytest.mark.asyncio
async def test_orchestrator_init(orchestrator: EmbeddedOrchestrator) -> None:
    """Orchestrator should initialize without errors."""
    assert orchestrator.binding_table is not None


@pytest.mark.asyncio
async def test_orchestrator_cancel_run_no_active(
    orchestrator: EmbeddedOrchestrator,
) -> None:
    """Cancel should be a no-op if no run is active."""
    await orchestrator.cancel_run("shell:local:dev")


@pytest.mark.asyncio
async def test_orchestrator_yields_status_event(
    orchestrator: EmbeddedOrchestrator,
    binding_table: InMemoryBindingTable,
) -> None:
    """Orchestrator should yield at least a status event before running agent."""
    await _setup_binding(binding_table)
    message = _make_message("test")

    # Mock the ADK event
    mock_event = MagicMock()
    mock_event.get_function_calls.return_value = []
    mock_event.is_final_response.return_value = True
    mock_event.content = MagicMock()
    mock_event.content.parts = []

    async def mock_run_async(**kwargs):
        yield mock_event

    mock_runner = MagicMock()
    mock_runner.run_async = mock_run_async

    with (
        patch("adk_claw.orchestrator.embedded.build_runner", return_value=mock_runner),
        patch(
            "adk_claw.orchestrator.embedded.find_project_root",
            return_value=Path("/tmp/test"),
        ),
        patch("adk_claw.orchestrator.embedded.get_project_id", return_value="test123"),
    ):
        events = []
        async for event in orchestrator.handle_message(message):
            events.append(event)

        # Should have at least the "Thinking..." status event
        assert len(events) >= 1
        assert events[0].type == "status"
        assert events[0].content == "Thinking..."
