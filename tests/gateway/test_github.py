import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from adk_claw.gateway.github import GithubAdapter
from adk_claw.domain.models import OrchestratorEvent, EventType


@pytest.mark.asyncio
async def test_github_adapter_poll_review_comment():
    mock_host = MagicMock()
    mock_host.setup_default_binding = AsyncMock()

    async def mock_events(*args, **kwargs):
        yield OrchestratorEvent(type=EventType.TOKEN, content="Thread reply")

    mock_host.handle_message = MagicMock(side_effect=mock_events)

    adapter = GithubAdapter(
        host=mock_host, pr_number=123, allowed_authors=["user1"], interval=1
    )
    adapter._last_checked = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # Mock gh pr view with a review comment
    mock_data = {
        "state": "OPEN",
        "comments": [],
        "reviews": [
            {
                "comments": [
                    {
                        "id": "comment_456",
                        "author": {"login": "user1"},
                        "body": "Review comment",
                        "createdAt": "2023-01-01T00:00:00Z",
                    }
                ]
            }
        ],
    }

    with patch("asyncio.create_subprocess_exec") as mock_exec, patch(
        "subprocess.run"
    ) as mock_run:
        # Mock repo info
        mock_run_result = MagicMock()
        mock_run_result.returncode = 0
        mock_run_result.stdout = json.dumps({"owner": {"login": "owner"}, "name": "repo"})
        mock_run.return_value = mock_run_result

        # Mock for gh pr view
        mock_process_view = AsyncMock()
        mock_process_view.communicate.return_value = (
            json.dumps(mock_data).encode(),
            b"",
        )
        mock_process_view.returncode = 0

        # Mock for gh api reply
        mock_process_reply = AsyncMock()
        mock_process_reply.communicate.return_value = (b"", b"")
        mock_process_reply.returncode = 0

        mock_exec.side_effect = [mock_process_view, mock_process_reply]

        await adapter._poll()
        await asyncio.sleep(0.1)

        # Verify host was called
        mock_host.handle_message.assert_called_once()

        # Verify gh api reply was called
        assert mock_exec.call_count == 2
        args = mock_exec.call_args_list[1][0]
        assert "gh" in args
        assert "api" in args
        assert "comments/comment_456/replies" in args[2]
        assert "body=Thread reply" in args[4]
