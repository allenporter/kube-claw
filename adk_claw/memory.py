"""
Cross-session memory store for adk-claw agents.

Provides persistent key-value storage scoped per workspace.
Default implementation writes JSON files to ``.adk-claw/memory/``
inside the workspace directory.
"""

import logging
from datetime import date as dt_date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


async def load_memory_context(workspace_path: Path) -> str:
    """
    Returns a guidance block for the agent about available memory files.
    """
    available_files = []

    # 1. Check for stable files
    stable_files = ["MEMORY.md", "USER.md", "SOUL.md"]
    for filename in stable_files:
        if (workspace_path / filename).exists():
            available_files.append(f"- `{filename}`")

    # 2. Check for recent journals
    today = dt_date.today()
    yesterday = today - timedelta(days=1)

    found_journals = []
    for d in [yesterday, today]:
        journal_path = workspace_path / "memory" / f"{d.isoformat()}.md"
        if journal_path.exists():
            found_journals.append(f"- `memory/{d.isoformat()}.md`")

    if found_journals:
        available_files.extend(found_journals)

    if not available_files:
        # Provide base guidance even if no files exist yet
        return (
            "\n## Memory Guidance\n"
            "You have persistent memory files in this workspace (e.g., `MEMORY.md`, `memory/YYYY-MM-DD.md`).\n"
            "1. USE your file tools (`ls`, `cat`) to find and read them if you need context.\n"
            "2. UPDATE them using `edit_file` to record important facts or progress.\n"
            "3. DO NOT ask for permission to read them; they are yours to manage.\n"
        )

    files_list = "\n".join(available_files)
    return (
        "\n## Memory Guidance\n"
        "The following memory files exist in this workspace:\n"
        f"{files_list}\n\n"
        "1. READ these files if you need to understand long-term facts or recent progress.\n"
        "2. UPDATE them yourself using your file tools to record new information.\n"
        "3. DO NOT use specialized tools; just treat them as normal project files.\n"
    )
