import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from adk_claw.runtime.embedded import EmbeddedRuntime


@pytest.mark.asyncio
async def test_embedded_runtime_env_injection(tmp_path: Path):
    """Verify that env vars are injected during execute and restored after."""
    runtime = EmbeddedRuntime(model="test-model")

    workspace = tmp_path / "ws"
    workspace.mkdir()

    test_env = {"MY_TEST_VAR": "secret-value"}

    # Mock build_runner and find_project_root to avoid heavy initialization
    with (
        patch("adk_claw.runtime.embedded.build_runner") as mock_build_runner,
        patch("adk_claw.runtime.embedded.find_project_root") as mock_find_root,
        patch("adk_claw.runtime.embedded.get_project_id") as mock_get_id,
    ):
        mock_runner = MagicMock()

        # Mock an empty async iterator for run_async
        async def mock_run_async(**kwargs):
            # Check that env var is present DURING execution
            assert os.environ.get("MY_TEST_VAR") == "secret-value"
            if False:
                yield  # make it a generator

        mock_runner.run_async = mock_run_async
        mock_build_runner.return_value = mock_runner
        mock_find_root.return_value = workspace
        mock_get_id.return_value = "test-project"

        # Initial check
        assert "MY_TEST_VAR" not in os.environ

        events = []
        async for event in runtime.execute(
            workspace_path=str(workspace),
            message="hello",
            lane_key="test-lane",
            session_id="test-session",
            env=test_env,
        ):
            events.append(event)

        # Final check - restored
        assert "MY_TEST_VAR" not in os.environ
