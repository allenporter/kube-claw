#!/usr/bin/env python3
"""
GitHub PR Bot for adk-claw.

Polls a GitHub PR for comments and responds to them.
Requires gh CLI to be authenticated.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from adk_claw.config import load_config
from adk_claw.host.host import ClawHost
from adk_claw.gateway.github import GithubAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Run adk-claw GitHub PR bot.")
    parser.add_argument("--pr", type=int, required=True, help="PR number to monitor")
    parser.add_argument("--workspace", type=str, help="Path to workspace")
    parser.add_argument(
        "--interval", type=int, default=60, help="Polling interval in seconds"
    )
    parser.add_argument(
        "--authors", type=str, help="Comma-separated list of allowed authors"
    )

    args = parser.parse_args()

    workspace_path = args.workspace or str(Path.cwd())
    config = load_config(workspace_path=Path(workspace_path))

    host = ClawHost(workspace_path=workspace_path, config=config)

    allowed_authors = args.authors.split(",") if args.authors else []

    adapter = GithubAdapter(
        host=host,
        pr_number=args.pr,
        allowed_authors=allowed_authors,
        interval=args.interval,
    )

    logger.info(f"Monitoring PR #{args.pr} in {workspace_path}")

    try:
        await adapter.start()
        # Keep the script running
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await adapter.stop()
        await host.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
