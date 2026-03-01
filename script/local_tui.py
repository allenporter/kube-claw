#!/usr/bin/env python3
"""
KubeClaw Local TUI — Terminal User Interface.

A simple interactive console that connects to the KubeClaw Host process
and provides a local development loop:

  User types message → Host routes to Worker → Worker (LLM) responds → TUI displays

Usage:
  GOOGLE_API_KEY=... python3 script/local_tui.py [--workspace /path/to/workspace]
"""

import argparse
import asyncio
import logging
import sys
import os

from aioconsole import ainput

# Ensure kube_claw is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kube_claw.host.host import ClawHost

# --- Styling ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
MAGENTA = "\033[35m"

logging.basicConfig(
    level=logging.WARNING,
    format=f"{DIM}%(asctime)s [%(name)s] %(message)s{RESET}",
)
logger = logging.getLogger("claw.tui")


def print_banner() -> None:
    print(f"""
{CYAN}{BOLD}  🐾 KubeClaw Local Loop{RESET}
{DIM}  Milestone 1 — Single Worker + ADK + MCP
  Type a message to interact with the agent.
  Press Ctrl+C to quit.{RESET}
""")


def print_event(event_type: str, content: str) -> None:
    """Pretty-print an orchestrator event."""
    if event_type == "thought":
        print(f"  {YELLOW}💭 {content}{RESET}")
    elif event_type == "result":
        print(f"  {GREEN}🤖 {content}{RESET}")
    elif event_type == "artifact":
        print(f"  {MAGENTA}📦 Artifact: {content}{RESET}")
    elif event_type == "error":
        print(f"  {RED}❌ Error: {content}{RESET}")
    else:
        print(f"  {DIM}[{event_type}] {content}{RESET}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="KubeClaw Local TUI")
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace path for the agent (default: current directory)",
    )
    args = parser.parse_args()

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_GENAI_API_KEY"):
        print(f"{RED}Error: Set GOOGLE_API_KEY or GOOGLE_GENAI_API_KEY env var.{RESET}")
        sys.exit(1)

    print_banner()
    print(f"{DIM}  Workspace: {args.workspace}{RESET}")
    print(f"{DIM}  Initializing host...{RESET}")

    # Initialize the host
    host = ClawHost(workspace_path=args.workspace)
    await host.setup_default_binding(workspace_path=args.workspace)

    print(f"{DIM}  RPC dir: {host.rpc_dir}{RESET}")
    print(f"{DIM}  Ready!{RESET}\n")

    try:
        while True:
            try:
                user_input = await ainput(f"{BOLD}> {RESET}")
            except EOFError:
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                break

            print()
            try:
                async for event in host.handle_message(user_input):
                    print_event(event.type, str(event.content))
            except Exception as e:
                print_event("error", str(e))
                logger.exception("Error processing message")
            print()

    except KeyboardInterrupt:
        print(f"\n{DIM}Shutting down...{RESET}")
    finally:
        await host.shutdown()
        print(f"{DIM}Goodbye! 🐾{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
