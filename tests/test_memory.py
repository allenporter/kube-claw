"""Tests for load_memory_context bootstrapping."""

import pytest
from pathlib import Path
from datetime import date as dt_date, timedelta
from adk_claw.memory import load_memory_context


@pytest.fixture
def global_dir(tmp_path: Path, monkeypatch) -> Path:
    g_dir = tmp_path / "global"
    g_dir.mkdir()
    monkeypatch.setattr("adk_claw.memory.GLOBAL_CONFIG_DIR", g_dir)
    return g_dir


@pytest.mark.asyncio
async def test_load_empty_workspace(tmp_path: Path, global_dir: Path) -> None:
    """Loading a workspace with no memory files returns base guidance."""
    context = await load_memory_context(tmp_path)
    assert "## Context Architecture Guidance" in context
    assert "You have persistent global memory at" in context


@pytest.mark.asyncio
async def test_load_stable_files(tmp_path: Path, global_dir: Path) -> None:
    """Loading stable files from global and session returns guidance with summaries."""
    (global_dir / "MEMORY.md").write_text("Long term memory", encoding="utf-8")
    (global_dir / "USER.md").write_text("User info", encoding="utf-8")

    (tmp_path / "SESSION.md").write_text("Session scratchpad", encoding="utf-8")

    context = await load_memory_context(tmp_path)
    assert "## Context Architecture Guidance" in context
    assert "The following memory files exist" in context
    assert f"- `{global_dir / 'MEMORY.md'}`: Long term memory" in context
    assert f"- `{global_dir / 'USER.md'}`: User info" in context
    assert f"- `{tmp_path / 'SESSION.md'}`: Session scratchpad" in context


@pytest.mark.asyncio
async def test_load_journals(tmp_path: Path, global_dir: Path) -> None:
    """Loading journals includes today and yesterday with absolute paths."""
    memory_dir = global_dir / "memory"
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
    assert f"- `{memory_dir / f'{today.isoformat()}.md'}`: Today's journal" in context
    assert (
        f"- `{memory_dir / f'{yesterday.isoformat()}.md'}`: Yesterday's journal"
        in context
    )
    assert old.isoformat() not in context
