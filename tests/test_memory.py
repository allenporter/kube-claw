"""Tests for FileMemoryStore."""

import pytest
from pathlib import Path

from adk_claw.memory import FileMemoryStore


@pytest.fixture
def store(tmp_path: Path) -> FileMemoryStore:
    return FileMemoryStore(base_path=tmp_path)


@pytest.mark.asyncio
async def test_get_missing_key(store: FileMemoryStore) -> None:
    """Getting a non-existent key returns None."""
    assert await store.get("ws1", "missing") is None


@pytest.mark.asyncio
async def test_put_and_get(store: FileMemoryStore) -> None:
    """Values round-trip through put/get."""
    await store.put("ws1", "greeting", "hello world")
    result = await store.get("ws1", "greeting")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_put_overwrites(store: FileMemoryStore) -> None:
    """Putting the same key twice overwrites the value."""
    await store.put("ws1", "key", "v1")
    await store.put("ws1", "key", "v2")
    assert await store.get("ws1", "key") == "v2"


@pytest.mark.asyncio
async def test_list_keys_empty(store: FileMemoryStore) -> None:
    """Empty workspace returns empty list."""
    assert await store.list_keys("ws1") == []


@pytest.mark.asyncio
async def test_list_keys(store: FileMemoryStore) -> None:
    """list_keys returns all stored keys."""
    await store.put("ws1", "alpha", "a")
    await store.put("ws1", "bravo", "b")
    keys = await store.list_keys("ws1")
    assert sorted(keys) == ["alpha", "bravo"]


@pytest.mark.asyncio
async def test_workspace_isolation(store: FileMemoryStore) -> None:
    """Different workspaces have separate key spaces."""
    await store.put("ws1", "key", "from-ws1")
    await store.put("ws2", "key", "from-ws2")
    assert await store.get("ws1", "key") == "from-ws1"
    assert await store.get("ws2", "key") == "from-ws2"


@pytest.mark.asyncio
async def test_key_sanitization(store: FileMemoryStore) -> None:
    """Keys with slashes are sanitized for filesystem safety."""
    await store.put("ws1", "path/to/key", "value")
    assert await store.get("ws1", "path/to/key") == "value"


@pytest.mark.asyncio
async def test_journal_round_trip(store: FileMemoryStore) -> None:
    """Journal entries can be appended and read back."""
    from datetime import date as dt_date

    today = dt_date.today().isoformat()
    await store.append_journal("ws1", "Entry 1")
    result = await store.read_journal("ws1", today)
    assert result
    assert "Entry 1" in result


@pytest.mark.asyncio
async def test_journal_append(store: FileMemoryStore) -> None:
    """Journal entries append to the same file."""
    from datetime import date as dt_date

    today = dt_date.today().isoformat()
    await store.append_journal("ws1", "First")
    await store.append_journal("ws1", "Second")
    result = await store.read_journal("ws1", today)
    assert result
    assert "First" in result
    assert "Second" in result


@pytest.mark.asyncio
async def test_list_journals(store: FileMemoryStore) -> None:
    """list_journals returns a sorted list of dates."""
    await store.append_journal("ws1", "Entry 1")
    # Simulate a different date by manually creating a file
    journal_dir = store._workspace_dir("ws1") / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    (journal_dir / "2023-01-01.md").write_text("Old stuff")

    dates = await store.list_journals("ws1")
    assert "2023-01-01" in dates
    assert len(dates) >= 2
    assert dates[0] >= dates[1]  # Sorted reverse chronological


@pytest.mark.asyncio
async def test_long_term_memory(store: FileMemoryStore) -> None:
    """MEMORY.md acts as long-term storage."""
    await store.put("ws1", "MEMORY", "Project Goals: Build a better claw.")
    result = await store.get("ws1", "MEMORY")
    assert result
    assert "Project Goals" in result
