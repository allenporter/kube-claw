"""
GitHub Pull Request Adapter.

Polls for comments on Pull Requests using the `gh` CLI and routes
them through the adk-claw host.
"""

import asyncio
import json
import logging
import subprocess
from typing import Any

from adk_claw.domain.models import EventType
from adk_claw.host.host import ClawHost

logger = logging.getLogger(__name__)


class GithubAdapter:
    """
    Adapter that polls GitHub PR comments via the `gh` CLI.

    When a new comment is found that mentions the bot or is on a PR
    the bot is participating in, it routes the comment through
    `ClawHost.handle_message()` and posts the response back to GitHub.
    """

    def __init__(
        self,
        host: ClawHost,
        repository: str,
        poll_interval: int = 60,
        allowed_authors: list[str] | None = None,
    ) -> None:
        self._host = host
        self._repository = repository
        self._poll_interval = poll_interval
        self._allowed_authors = allowed_authors
        self._last_comment_id: dict[int, int] = {}  # PR ID -> Last seen comment ID
        self._running = False

    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        logger.info(f"GitHub adapter started for {self._repository}")
        while self._running:
            try:
                await self._poll_prs()
            except Exception:
                logger.exception("Error polling GitHub PRs")
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False

    async def _poll_prs(self) -> None:
        """Poll for new comments across all active PRs."""
        # Get list of open PRs for the repository
        try:
            prs = self._gh_exec(
                ["pr", "list", "--repo", self._repository, "--state", "open", "--json", "number"]
            )
        except Exception as e:
            logger.error(f"Failed to list PRs: {e}")
            return

        for pr in prs:
            pr_number = pr["number"]
            await self._poll_pr_comments(pr_number)

    async def _poll_pr_comments(self, pr_number: int) -> None:
        """Check for new comments on a specific PR."""
        try:
            comments = self._gh_exec(
                ["pr", "view", str(pr_number), "--repo", self._repository, "--json", "comments"]
            )["comments"]
        except Exception as e:
            logger.error(f"Failed to get comments for PR #{pr_number}: {e}")
            return

        if not comments:
            return

        # Sort comments by creation time/ID
        comments.sort(key=lambda c: c["id"])

        last_id = self._last_comment_id.get(pr_number)
        
        # If this is the first time we've seen this PR, initialize with the last comment
        if last_id is None:
            self._last_comment_id[pr_number] = comments[-1]["id"]
            return

        new_comments = [c for c in comments if c["id"] > last_id]
        
        for comment in new_comments:
            await self._handle_comment(pr_number, comment)
            self._last_comment_id[pr_number] = comment["id"]

    async def _handle_comment(self, pr_number: int, comment: dict[str, Any]) -> None:
        """Process a new comment and reply if necessary."""
        author = comment["author"]["login"]
        body = comment["body"]

        # Simple heuristic: ignore comments from "github-actions" or known bots
        if "[bot]" in author or author == "github-actions":
            return

        # If allowed_authors is configured, check that the author is in the list
        if self._allowed_authors and author not in self._allowed_authors:
            logger.debug(f"Ignoring comment from unauthorized author: {author}")
            return

        logger.info(f"New comment on PR #{pr_number} from {author}: {body[:50]}...")

        channel_id = f"pr-{pr_number}"
        author_id = author

        try:
            await self._host.setup_default_binding(
                protocol="github",
                channel_id=channel_id,
                author_id=author_id,
            )

            response_parts: list[str] = []
            async for event in self._host.handle_message(
                text=body,
                protocol="github",
                channel_id=channel_id,
                author_id=author_id,
            ):
                if event.type == EventType.TOKEN:
                    response_parts.append(event.content)
                elif event.type == EventType.ERROR:
                    response_parts.append(f"⚠️ {event.content}")

            if response_parts:
                full_response = "\n".join(response_parts)
                self._gh_exec(
                    ["pr", "comment", str(pr_number), "--repo", self._repository, "--body", full_response]
                )

        except Exception:
            logger.exception(f"Error handling GitHub comment on PR #{pr_number}")

    def _gh_exec(self, args: list[str]) -> Any:
        """Execute a `gh` command and return parsed JSON output."""
        cmd = ["gh"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
