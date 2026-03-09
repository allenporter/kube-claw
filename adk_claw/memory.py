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
    """
    sections = []

    # 1. Check for stable files
    stable_files = ["USER.md", "SOUL.md", "MEMORY.md"]
    found_stable = []
    for filename in stable_files:
        path = workspace_path / filename
        if path.exists():
            summary = _read_summary(path)
            found_stable.append(
                f"- `{filename}`: {summary}" if summary else f"- `{filename}`"
            )

    if found_stable:
        sections.append("### Core Memory\n" + "\n".join(found_stable))

    # 2. Check for recent journals
    today = dt_date.today()
    yesterday = today - timedelta(days=1)

    found_journals = []
    for d in [yesterday, today]:
        journal_path = workspace_path / "memory" / f"{d.isoformat()}.md"
        if journal_path.exists():
            summary = _read_summary(journal_path)
            found_journals.append(
                f"- `memory/{d.isoformat()}.md`: {summary}"
                if summary
                else f"- `memory/{d.isoformat()}.md`"
            )

    if found_journals:
        sections.append("### Recent Journals\n" + "\n".join(found_journals))

    if not sections:
        # Provide base guidance even if no files exist yet
        return (
            "\n## Memory Guidance\n"
            "You have persistent memory files in this workspace (e.g., `MEMORY.md`, `memory/YYYY-MM-DD.md`).\n"
            "1. USE your file tools (`ls`, `cat`) to find and read them if you need context.\n"
            "2. UPDATE them using `edit_file` to record important facts or progress.\n"
            "3. DO NOT ask for permission to read them; they are yours to manage.\n"
        )

    content_block = "\n\n".join(sections)
    return (
        "\n## Memory Guidance\n"
        "The following memory files exist in this workspace. Quick summaries provided:\n\n"
        f"{content_block}\n\n"
        "1. READ these files if you need to understand long-term facts or recent progress.\n"
        "2. UPDATE them yourself using your file tools to record new information.\n"
        "3. DO NOT use specialized tools; just treat them as normal project files.\n"
    )
