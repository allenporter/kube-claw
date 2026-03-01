"""Tests for the Claw MCP server tools (FastMCP pattern)."""

import os

import pytest
from unittest.mock import AsyncMock

from kube_claw.mcp.server import create_mcp_server


@pytest.fixture
def workspace_path() -> str:
    """Return the project root (a real git repo)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mcp_server(workspace_path: str):
    """Create a FastMCP server with test-lane context."""
    return create_mcp_server(lane_id="test-lane", workspace_path=workspace_path)


# --- git_info ---


@pytest.mark.asyncio
async def test_git_info_returns_branch(mcp_server) -> None:
    result = await mcp_server.call_tool("git_info", {})
    text = str(result)
    assert "Branch:" in text
    assert "Recent commits:" in text
    assert "Status:" in text


@pytest.mark.asyncio
async def test_git_info_with_non_git_dir() -> None:
    server = create_mcp_server(lane_id="test", workspace_path="/tmp")
    result = await server.call_tool("git_info", {})
    text = str(result)
    # /tmp is not a git repo, so we get fallback values
    assert "Branch:" in text


# --- read_secret ---


@pytest.mark.asyncio
async def test_read_secret_via_call_tool(mcp_server) -> None:
    result = await mcp_server.call_tool("read_secret", {"key": "MY_TOKEN"})
    text = str(result)
    assert "MY_TOKEN" in text
    assert "test-lane" in text


@pytest.mark.asyncio
async def test_read_secret_unknown_key(mcp_server) -> None:
    result = await mcp_server.call_tool("read_secret", {"key": "unknown"})
    assert "unknown" in str(result)


# --- github_api ---


@pytest.mark.asyncio
async def test_github_api_repo_info(mcp_server) -> None:
    result = await mcp_server.call_tool(
        "github_api", {"action": "repo_info", "repo": "owner/repo"}
    )
    assert "owner/repo" in str(result)


@pytest.mark.asyncio
async def test_github_api_list_prs(mcp_server) -> None:
    result = await mcp_server.call_tool(
        "github_api", {"action": "list_prs", "repo": "owner/repo"}
    )
    text = str(result)
    assert "owner/repo" in text
    assert "credential hydration" in text


@pytest.mark.asyncio
async def test_github_api_list_issues(mcp_server) -> None:
    result = await mcp_server.call_tool(
        "github_api", {"action": "list_issues", "repo": "owner/repo"}
    )
    assert "owner/repo" in str(result)


@pytest.mark.asyncio
async def test_github_api_resolves_current_repo(mcp_server) -> None:
    """When repo='current', should resolve from git remote."""
    result = await mcp_server.call_tool(
        "github_api", {"action": "repo_info", "repo": "current"}
    )
    assert "Repository:" in str(result)


@pytest.mark.asyncio
async def test_github_api_unknown_action(mcp_server) -> None:
    result = await mcp_server.call_tool(
        "github_api", {"action": "delete_repo", "repo": "x/y"}
    )
    assert "Unknown" in str(result)


# --- host_approve ---


@pytest.mark.asyncio
async def test_host_approve_denied_by_default() -> None:
    """Without a callback, approval should be denied (safe default)."""
    server = create_mcp_server(lane_id="test", workspace_path="/tmp")
    result = await server.call_tool(
        "host_approve", {"action": "delete branch", "risk_level": "high"}
    )
    assert "denied" in str(result)


@pytest.mark.asyncio
async def test_host_approve_with_callback_approved() -> None:
    callback = AsyncMock(return_value=True)
    server = create_mcp_server(
        lane_id="test", workspace_path="/tmp", approval_callback=callback
    )
    result = await server.call_tool(
        "host_approve", {"action": "delete branch", "risk_level": "high"}
    )
    assert "approved" in str(result)
    callback.assert_called_once_with("delete branch", "high")


@pytest.mark.asyncio
async def test_host_approve_with_callback_denied() -> None:
    callback = AsyncMock(return_value=False)
    server = create_mcp_server(
        lane_id="test", workspace_path="/tmp", approval_callback=callback
    )
    result = await server.call_tool(
        "host_approve", {"action": "force push", "risk_level": "high"}
    )
    assert "denied" in str(result)


@pytest.mark.asyncio
async def test_host_approve_callback_error() -> None:
    callback = AsyncMock(side_effect=RuntimeError("connection lost"))
    server = create_mcp_server(
        lane_id="test", workspace_path="/tmp", approval_callback=callback
    )
    result = await server.call_tool("host_approve", {"action": "test"})
    text = str(result)
    assert "failed" in text
    assert "connection lost" in text


# --- tool registration ---


def test_server_has_all_tools(mcp_server) -> None:
    """Verify all 4 tools are registered on the FastMCP instance."""
    tool_names = {name for name in mcp_server._tool_manager._tools}
    assert tool_names >= {"git_info", "read_secret", "github_api", "host_approve"}
