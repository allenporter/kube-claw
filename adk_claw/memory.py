"""
Cross-session memory store for adk-claw agents.

Provides persistent key-value storage scoped per workspace.
Default implementation writes JSON files to ``.adk-claw/memory/``
inside the workspace directory.
"""

import json
import logging
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class MemoryStore(Protocol):
    """Protocol for cross-session agent memory."""

    async def get(self, workspace_id: str, key: str) -> str | None: ...

    async def put(self, workspace_id: str, key: str, value: str) -> None: ...

    async def list_keys(self, workspace_id: str) -> list[str]: ...


class FileMemoryStore:
    """MemoryStore backed by JSON files in the workspace.

    Stores each key as a separate JSON file under
    ``<base_path>/<workspace_id>/``.
    """

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self._base_path / workspace_id

    def _key_path(self, workspace_id: str, key: str) -> Path:
        # Sanitize key to be filesystem-safe
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._workspace_dir(workspace_id) / f"{safe_key}.json"

    async def get(self, workspace_id: str, key: str) -> str | None:
        """Retrieve a value by key, or ``None`` if not found."""
        path = self._key_path(workspace_id, key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("value")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read memory key '%s': %s", key, e)
            return None

    async def put(self, workspace_id: str, key: str, value: str) -> None:
        """Store a value by key, creating directories as needed."""
        path = self._key_path(workspace_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"key": key, "value": value}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Stored memory key '%s' for workspace '%s'", key, workspace_id)

    async def list_keys(self, workspace_id: str) -> list[str]:
        """List all stored keys for a workspace."""
        ws_dir = self._workspace_dir(workspace_id)
        if not ws_dir.exists():
            return []
        return [p.stem for p in ws_dir.glob("*.json")]
