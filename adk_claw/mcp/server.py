"""
Host-side MCP Server — Tool Hydration Layer.

Exposes tools to the Worker that require host-side context:
- git_info: Runs git commands on the host's real workspace.
- read_secret: Reads credentials from the host's auth profile.
- github_api: Proxied GitHub API calls with credential hydration.
- host_approve: Blocking approval gate for destructive actions.

Uses the FastMCP decorator pattern so that tool names, descriptions,
and input schemas are inferred automatically from Python functions.
"""

import subprocess
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.server.fastmcp import FastMCP


def create_mcp_server(
    lane_id: str,
    workspace_path: str,
    approval_callback: Callable[[str, str], Coroutine[Any, Any, bool]] | None = None,
) -> FastMCP:
    """Create a configured MCP server with host-side tool hydration.

    Tools close over ``lane_id``, ``workspace_path``, and
    ``approval_callback`` so no mutable global state is required.
    """
    mcp = FastMCP("claw-mcp-server")

    # ------------------------------------------------------------------
    # Tools — each is auto-registered by @mcp.tool() and the SDK infers
    # the input schema from the function signature and description from
    # the docstring.
    # ------------------------------------------------------------------

    @mcp.tool()
    async def git_info() -> str:
        """Get git status for the current workspace (branch, recent commits)."""
        branch_res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
        )
        branch = branch_res.stdout.strip() or "detached HEAD"

        log_res = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
        )
        recent = log_res.stdout.strip() or "No commits"

        status_res = subprocess.run(
            ["git", "status", "--short"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
        )
        status = status_res.stdout.strip() or "Clean"

        return f"Branch: {branch}\nRecent commits:\n{recent}\nStatus:\n{status}"

    @mcp.tool()
    def read_secret(key: str) -> str:
        """Read a sensitive secret from the host's credential store."""
        # In production, this would read from a real secret store.
        return f"Secret [{key}] = (Host-only credentials for lane {lane_id})"

    @mcp.tool()
    async def github_api(
        action: str,
        repo: str = "current",
    ) -> str:
        """Make a GitHub API call using host-side credentials.

        The host injects GITHUB_TOKEN automatically.
        Use repo='current' to target the current workspace repo.
        """
        resolved_repo = repo

        # Resolve "current" repo from workspace git remote
        if resolved_repo == "current":
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
            )
            remote_url = res.stdout.strip()
            # Parse owner/repo from git URL
            if "github.com" in remote_url:
                # Handle both SSH and HTTPS URLs
                resolved_repo = (
                    remote_url.split("github.com")[-1].strip(":/").removesuffix(".git")
                )
            else:
                resolved_repo = "unknown/unknown"

        # In production, this would use GITHUB_TOKEN from the auth profile
        # and make real API calls. For milestone 1, we simulate.
        if action == "list_prs":
            return (
                f"GitHub PRs for {resolved_repo}: (credential hydration demo — "
                f"GITHUB_TOKEN would be injected by host for lane {lane_id}). "
                f"No real API call made in milestone 1."
            )
        elif action == "list_issues":
            return (
                f"GitHub Issues for {resolved_repo}: (credential hydration demo — "
                f"host would inject token). No real API call in milestone 1."
            )
        elif action == "repo_info":
            return f"Repository: {resolved_repo} (resolved from workspace remote)"

        return f"Unknown github_api action: {action}"

    @mcp.tool()
    async def host_approve(
        action: str,
        risk_level: str = "medium",
    ) -> str:
        """Request user approval for a potentially destructive action.

        The host will prompt the user and return 'approved' or 'denied'.
        Use this before deleting branches, force-pushing, etc.
        """
        if approval_callback:
            # The host/TUI will handle prompting the user
            try:
                approved = await approval_callback(action, risk_level)
            except Exception as e:
                return f"Approval request failed: {e}"
            status = "approved" if approved else "denied"
        else:
            # No callback registered — deny by default (safe)
            status = "denied (no approval handler registered)"

        return f"Action '{action}' (risk: {risk_level}): {status}"

    return mcp
