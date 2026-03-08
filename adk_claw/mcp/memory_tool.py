"""
Memory Tool — Persistent Agent Memory.

Provides tools for the agent to store and retrieve facts across sessions
using the Claw MemoryStore.
"""

import logging

from adk_claw.memory import MemoryStore
from google.adk.tools.function_tool import FunctionTool

logger = logging.getLogger(__name__)


class MemoryToolSet:
    """
    Sets up tools for persistent memory access.
    """

    def __init__(self, store: MemoryStore, workspace_id: str) -> None:
        self._store = store
        self._workspace_id = workspace_id

    async def get_memory(self, key: str) -> str:
        """
        Retrieve a value from the cross-session memory store.
        Use this to recall facts, preferences, or status from previous sessions.
        """
        val = await self._store.get(self._workspace_id, key)
        if val is None:
            return f"Key '{key}' not found in memory."
        return val

    async def put_memory(self, key: str, value: str) -> str:
        """
        Store a value in the cross-session memory store.
        Use this to save important facts or state that should persist.
        """
        await self._store.put(self._workspace_id, key, value)
        return f"Successfully stored '{key}' in memory."

    async def add_journal_entry(self, content: str) -> str:
        """
        Append a narrative entry to today's episodic journal.
        Use this to record major accomplishments, decisions, or contextual changes
        that an agent in a future session should know about.
        """
        await self._store.append_journal(self._workspace_id, content)
        return "Successfully added to today's journal."

    async def read_journal(self, date: str) -> str:
        """
        Read the episodic journal for a specific date (format: YYYY-MM-DD).
        Use this to recall the narrative history of past sessions.
        """
        val = await self._store.read_journal(self._workspace_id, date)
        if val is None:
            return f"No journal entry found for date '{date}'."
        return val

    async def list_journals(self) -> str:
        """
        List all available dates in the episodic journal.
        Returns a list of YYYY-MM-DD strings.
        """
        dates = await self._store.list_journals(self._workspace_id)
        if not dates:
            return "No journals found."
        return "\n".join(dates)

    async def get_long_term_memory(self) -> str:
        """
        Read the MEMORY.md file containing durable facts and preferences.
        Use this to recall long-term context that persists across project history.
        """
        val = await self._store.get(self._workspace_id, "MEMORY")
        if val is None:
            return "No long-term memory (MEMORY.md) found."
        return val

    async def put_long_term_memory(self, content: str) -> str:
        """
        Update the MEMORY.md file with durable facts, decisions, or preferences.
        Use this for information that should be remembered forever (e.g. project goals, tech stack choices).
        """
        await self._store.put(self._workspace_id, "MEMORY", content)
        return "Successfully updated long-term memory (MEMORY.md)."

    def get_tools(self) -> list[FunctionTool]:
        """Return the FunctionTool instances for registration."""
        return [
            FunctionTool(self.get_memory),
            FunctionTool(self.put_memory),
            FunctionTool(self.add_journal_entry),
            FunctionTool(self.read_journal),
            FunctionTool(self.list_journals),
            FunctionTool(self.get_long_term_memory),
            FunctionTool(self.put_long_term_memory),
        ]
