import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from adk_claw.gateway.github import GithubAdapter
from adk_claw.domain.models import OrchestratorEvent, EventType


@pytest.mark.asyncio
async def test_github_adapter_poll_new_comment():
    mock_host = MagicMock()
    mock_host.setup_default_binding = AsyncMock()

    # Mock return events from host
    async def mock_events(*args, **kwargs):
        yield OrchestratorEvent(type=EventType.TOKEN, content="Hello from agent")

    mock_host.handle_message = MagicMock(side_effect=mock_events)

    adapter = GithubAdapter(
        host=mock_host, pr_number=123, allowed_authors=["user1"], interval=1
    )

    # Set last_checked to past
    adapter._last_checked = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # Mock gh pr view
    mock_comments = {
        "comments": [
            {
                "author": {"login": "user1"},
                "body": "Test comment",
                "createdAt": "2023-01-01T00:00:00Z",
            }
        ]
    }

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock for gh pr view
        mock_process_view = AsyncMock()
        mock_process_view.communicate.return_value = (
            json.dumps(mock_comments).encode(),
            b"",
        )
        mock_process_view.return_code = (
            0  # Wait, it's returncode in subprocess but return_code in some mocks?
        )
        # Actually in asyncio.subprocess.Process it's returncode.
        mock_process_view.returncode = 0

        # Mock for gh pr comment
        mock_process_comment = AsyncMock()
        mock_process_comment.communicate.return_value = (b"", b"")
        mock_process_comment.returncode = 0

        mock_exec.side_effect = [mock_process_view, mock_process_comment]

        await adapter._poll()

        # Wait a bit for the async task to finish
        await asyncio.sleep(0.1)

        # Verify host was called
        mock_host.handle_message.assert_called_once()
        assert "Test comment" in mock_host.handle_message.call_args[1]["text"]

        # Verify gh pr comment was called
        assert mock_exec.call_count == 2
        args = mock_exec.call_args_list[1][0]
        assert "gh" in args
        assert "pr" in args
        assert "comment" in args
        assert "Hello from agent" in args
