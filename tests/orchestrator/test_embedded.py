"""Tests for EmbeddedOrchestrator."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from kube_claw.binding.fakes import InMemoryBindingTable
from kube_claw.domain.models import (
    ClawIdentity,
    InboundMessage,
    WorkspaceContext,
)
from kube_claw.orchestrator.embedded import EmbeddedOrchestrator


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

    # Mock build_adk_agent to avoid actual LLM calls
    mock_agent = MagicMock()
    mock_event = MagicMock()
    mock_event.get_function_calls.return_value = []
    mock_event.is_final_response.return_value = True
    mock_event.content = MagicMock()
    mock_event.content.parts = []

    async def mock_run_async(**kwargs):
        yield mock_event

    with (
        patch(
            "kube_claw.orchestrator.embedded.build_adk_agent", return_value=mock_agent
        ),
        patch("kube_claw.orchestrator.embedded.Runner") as mock_runner_cls,
    ):
        mock_runner = MagicMock()
        mock_runner.run_async = mock_run_async
        mock_runner_cls.return_value = mock_runner

        mock_session = MagicMock()
        mock_session.user_id = "test"
        mock_session.id = "session-1"

        with patch(
            "kube_claw.orchestrator.embedded.InMemorySessionService"
        ) as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.create_session = AsyncMock(return_value=mock_session)
            mock_svc_cls.return_value = mock_svc

            events = []
            async for event in orchestrator.handle_message(message):
                events.append(event)

            # Should have at least the "Thinking..." status event
            assert len(events) >= 1
            assert events[0].type == "status"
            assert events[0].content == "Thinking..."
