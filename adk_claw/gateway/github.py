"""
GitHub Pull Request Adapter.

Polls GitHub for new comments on a specific PR using the GitHub CLI (gh)
and routes them to the adk-claw host.
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any

from adk_claw.domain.models import EventType
from adk_claw.host.host import ClawHost

logger = logging.getLogger(__name__)


class GithubAdapter:
    """
    Adapter that polls GitHub PR comments and responds to them.
    """

    def __init__(
        self,
        host: ClawHost,
        pr_number: int,
        allowed_authors: list[str] | None = None,
        interval: int = 60,
    ) -> None:
        self._host = host
        self._pr_number = pr_number
        self._allowed_authors = allowed_authors or []
        self._interval = interval
        self._last_checked = datetime.now(timezone.utc)
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        logger.info(
            f"Starting GitHub adapter for PR #{self._pr_number} "
            f"(authors={self._allowed_authors}, interval={self._interval}s)"
        )
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("GitHub adapter stopped.")

    async def _run(self) -> None:
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                logger.exception(f"Error polling GitHub: {e}")
            await asyncio.sleep(self._interval)

    async def _poll(self) -> None:
        # Fetch PR comments using gh CLI
        cmd = ["gh", "pr", "view", str(self._pr_number), "--json", "comments"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
        except Exception as e:
            logger.error(f"Failed to execute gh CLI: {e}")
            return

        if process.returncode != 0:
            logger.error(f"gh pr view failed: {stderr.decode()}")
            return

        try:
            data = json.loads(stdout.decode())
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from gh CLI")
            return

        comments = data.get("comments", [])
        newest_timestamp = self._last_checked

        for comment in comments:
            created_at_str = comment["createdAt"]
            # createdAt is ISO 8601 like "2023-01-01T00:00:00Z"
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            if created_at > self._last_checked:
                author = comment["author"]["login"]
                
                # Check if author is allowed
                if self._allowed_authors and author not in self._allowed_authors:
                    logger.debug(f"Ignoring comment from unauthorized author: {author}")
                    continue

                body = comment["body"]
                logger.info(f"Processing GitHub comment from {author}: {body[:80]}")
                
                # Update temporary newest timestamp
                if created_at > newest_timestamp:
                    newest_timestamp = created_at
                
                # Handle the comment asynchronously
                asyncio.create_task(self._handle_comment(author, body))

        self._last_checked = newest_timestamp

    async def _handle_comment(self, author: str, body: str) -> None:
        """Route message to host and post response back to PR."""
        channel_id = f"pr-{self._pr_number}"
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
                    response_parts.append(f"⚠️ **Error:** {event.content}")

            if response_parts:
                full_response = "\n".join(response_parts)
                await self._post_comment(full_response)
            else:
                logger.warning("No response generated for GitHub comment.")

        except Exception:
            logger.exception("Error handling GitHub comment")
            await self._post_comment("⚠️ An error occurred while processing your request.")

    async def _post_comment(self, body: str) -> None:
        """Post a comment back to the PR using gh CLI."""
        cmd = ["gh", "pr", "comment", str(self._pr_number), "--body", body]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error(f"gh pr comment failed: {stderr.decode()}")
            else:
                logger.info(f"Posted response to PR #{self._pr_number}")
        except Exception as e:
            logger.error(f"Failed to post comment to GitHub: {e}")
