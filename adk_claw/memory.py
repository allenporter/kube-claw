"""
Cross-session memory store for adk-claw agents.
"""

import logging
from datetime import date as dt_date, timedelta
from pathlib import Path

from adk_claw.config import GLOBAL_CONFIG_DIR

logger = logging.getLogger(__name__)


def _read_summary(path: Path, max_chars: int = 500) -> str:
    """Reads the beginning of a file to provide a quick summary."""
    try:
        content = path.read_text().strip()
        if not content:
            return ""
        # Get first few lines or characters
        summary = content[:max_chars].replace("\n", " ")
        if len(content) > max_chars:
            summary += "..."
        return summary
    except Exception:
        return ""


async def load_memory_context(workspace_path: Path) -> str:
    """
    Returns a guidance block for the agent about available memory files
    with brief summaries of their content.
    Combines Tier 1 Global Brain and Tier 2 Session Workspace files.
    """
    sections = []

    # 1. Tier 1: Check for Global Memory files
    stable_files = ["USER.md", "SOUL.md", "MEMORY.md"]
    found_global = []
    for filename in stable_files:
        path = GLOBAL_CONFIG_DIR / filename
        if path.exists():
            summary = _read_summary(path)
            # Use absolute path so the agent can interact with it across workspaces
            found_global.append(
                f"- `{path.absolute()}`: {summary}"
                if summary
                else f"- `{path.absolute()}`"
            )

    if found_global:
        sections.append("### Tier 1: Global Brain\n" + "\n".join(found_global))

    # 2. Check for recent journals in Tier 1
    today = dt_date.today()
    yesterday = today - timedelta(days=1)

    found_journals = []
    for d in [yesterday, today]:
        journal_path = GLOBAL_CONFIG_DIR / "memory" / f"{d.isoformat()}.md"
        if journal_path.exists():
            summary = _read_summary(journal_path)
            found_journals.append(
                f"- `{journal_path.absolute()}`: {summary}"
                if summary
                else f"- `{journal_path.absolute()}`"
            )

    if found_journals:
        sections.append("### Tier 1: Global Journals\n" + "\n".join(found_journals))

    # 3. Tier 2: Check for Session Workspace Scratchpad
    session_file = workspace_path / "SESSION.md"
    if session_file.exists():
        summary = _read_summary(session_file)
        sections.append(
            f"### Tier 2: Session Scratchpad\n- `{session_file.absolute()}`: {summary}"
            if summary
            else f"### Tier 2: Session Scratchpad\n- `{session_file.absolute()}`"
        )

    if not sections:
        # Provide base guidance even if no files exist yet
        return (
            "\n## Context Architecture Guidance\n"
            f"You have persistent global memory at `{GLOBAL_CONFIG_DIR.absolute()}` and session memory at `{workspace_path.absolute()}/SESSION.md`.\n"
            "1. USE your file tools (`ls`, `cat`) to find and read them if you need context.\n"
            "2. UPDATE them using `edit_file` to record important facts or progress.\n"
            "3. DO NOT ask for permission to read them; they are yours to manage.\n"
        )

    content_block = "\n\n".join(sections)
    return (
        "\n## Context Architecture Guidance\n"
        "The following memory files exist across your Global Brain and Session Workspace. Quick summaries provided:\n\n"
        f"{content_block}\n\n"
        "1. READ these ABSOLUTE paths if you need to understand long-term facts or recent progress.\n"
        "2. UPDATE them yourself using your file editing tools to record new information.\n"
        "3. Remember: Global memory applies to ALL sessions. Session memory only applies to this chat.\n"
    )
