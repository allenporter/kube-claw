import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from adk_claw.runtime.embedded import EmbeddedRuntime


@pytest.mark.asyncio
async def test_embedded_runtime_fresh_runner_each_turn(tmp_path: Path):
    """Verify that a fresh runner is built for every execution turn."""
    runtime = EmbeddedRuntime(model="test-model")
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Mock dependencies
    with (
        patch("adk_claw.runtime.embedded.build_runner") as mock_build_runner,
        patch("adk_claw.runtime.embedded.find_project_root") as mock_find_root,
        patch("adk_claw.runtime.embedded.get_project_id") as mock_get_id,
        patch("adk_claw.runtime.embedded.initialize_global_brain"),
        patch("adk_claw.runtime.embedded.initialize_session_workspace"),
        patch("adk_claw.runtime.embedded.load_memory_context", return_value=""),
        patch("adk_claw.runtime.embedded.assemble_instructions", return_value=""),
    ):
        mock_runner = MagicMock()

        # Mock an empty async iterator for run_async
        async def mock_run_async(**kwargs):
            if False:
                yield

        mock_runner.run_async = mock_run_async
        mock_build_runner.return_value = mock_runner
        mock_find_root.return_value = workspace
        mock_get_id.return_value = "test-project"

        # Execute first time
        async for event in runtime.execute(
            workspace_path=str(workspace),
            message="turn 1",
            lane_key="lane-1",
            session_id="session-1",
        ):
            print(f"EVENT: {event}")

        assert mock_build_runner.call_count == 1

        # Execute second time with same session_id
        async for _ in runtime.execute(
            workspace_path=str(workspace),
            message="turn 2",
            lane_key="lane-1",
            session_id="session-1",
        ):
            pass

        # Should call build_runner AGAIN for the second turn
        assert mock_build_runner.call_count == 2
