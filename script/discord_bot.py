#!/usr/bin/env python3
"""
adk-claw Discord Bot.

Connects the DiscordAdapter to ClawHost so the agent responds
to @mentions and DMs in Discord.

Usage:
  GOOGLE_API_KEY=... DISCORD_TOKEN=... python3 script/discord_bot.py [--workspace .]
"""

import argparse
import asyncio
import logging
import os
import sys

from adk_claw.host.host import ClawHost
from adk_claw.gateway.discord import DiscordAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("claw.discord")


async def main() -> None:
    parser = argparse.ArgumentParser(description="adk-claw Discord Bot")
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace path for the agent (default: current directory)",
    )
    args = parser.parse_args()

    # Validate env vars
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
    discord_token = os.getenv("DISCORD_TOKEN")

    if not api_key:
        print("Error: Set GOOGLE_API_KEY or GOOGLE_GENAI_API_KEY env var.")
        sys.exit(1)
    if not discord_token:
        print("Error: Set DISCORD_TOKEN env var.")
        sys.exit(1)

    # Set up host and adapter
    host = ClawHost(workspace_path=args.workspace)
    adapter = DiscordAdapter(host=host, token=discord_token)

    logger.info("Starting Discord bot (workspace: %s)", args.workspace)

    try:
        await adapter.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await adapter.stop()
        await host.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
