"""Tests for load_memory_context bootstrapping."""

import pytest
from pathlib import Path
from datetime import date as dt_date, timedelta
from adk_claw.memory import load_memory_context


@pytest.mark.asyncio
async def test_load_empty_workspace(tmp_path: Path) -> None:
    """Loading a workspace with no memory files returns base guidance."""
    context = await load_memory_context(tmp_path)
    assert "## Memory Guidance" in context
    assert "You have persistent memory files" in context


@pytest.mark.asyncio
async def test_load_stable_files(tmp_path: Path) -> None:
    """Loading stable files (MEMORY, USER, SOUL) returns guidance with file list."""
    (tmp_path / "MEMORY.md").write_text("Long term memory", encoding="utf-8")
    (tmp_path / "USER.md").write_text("User info", encoding="utf-8")

    context = await load_memory_context(tmp_path)
    assert "## Memory Guidance" in context
    assert "The following memory files exist" in context
    assert "- `MEMORY.md`" in context
    assert "- `USER.md`" in context
    assert "Long term memory" not in context  # Should not include content
    assert "User info" not in context


@pytest.mark.asyncio
async def test_load_journals(tmp_path: Path) -> None:
    """Loading journals includes today and yesterday in the list."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    today = dt_date.today()
    yesterday = today - timedelta(days=1)
    old = today - timedelta(days=5)

    (memory_dir / f"{today.isoformat()}.md").write_text(
        "Today's journal", encoding="utf-8"
    )
    (memory_dir / f"{yesterday.isoformat()}.md").write_text(
        "Yesterday's journal", encoding="utf-8"
    )
    (memory_dir / f"{old.isoformat()}.md").write_text("Old journal", encoding="utf-8")

    context = await load_memory_context(tmp_path)
    assert f"- `memory/{today.isoformat()}.md`" in context
    assert f"- `memory/{yesterday.isoformat()}.md`" in context
    assert f"memory/{old.isoformat()}.md" not in context
    assert "Today's journal" not in context  # Should not include content
