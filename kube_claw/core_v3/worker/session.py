import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """State management for a single turn or session."""

    session_id: str
    workspace_path: str
    identity: Dict[str, Any]
    llm_config: Dict[str, Any]
    active: bool = False


class SessionManager:
    """
    Handles 'Soft Resets' and Bootstrap Data.
    Maintains the state of the worker between turns.
    """

    def __init__(self):
        self._current_session: Optional[SessionState] = None
        self._lock = asyncio.Lock()

    async def bootstrap(self, config: Dict[str, Any]):
        """
        JIT Config via A2A Handshake.
        Receives identity, workspace, and LLM configuration.
        """
        async with self._lock:
            self._current_session = SessionState(
                session_id=config.get("session_id", "default"),
                workspace_path=config.get("workspace_path", "/workspace"),
                identity=config.get("identity", {}),
                llm_config=config.get("llm_config", {}),
                active=True,
            )
            logger.info(
                f"Worker bootstrapped for session: {self._current_session.session_id}"
            )
            # Here we would initialize ADK or update env vars.
            self._apply_env_overrides()

    async def soft_reset(self):
        """
        Clears state between turns to ensure 'Warm Lane' stability.
        Resets environment variables, clears temp buffers, but keeps the process alive.
        """
        async with self._lock:
            if self._current_session:
                logger.info(
                    f"Soft resetting session: {self._current_session.session_id}"
                )
                # Reset tool registry or clear local cache if needed.
                self._current_session.active = False
            self._current_session = None

    def _apply_env_overrides(self):
        """Applies configuration to the environment."""
        if not self._current_session:
            return
        # Example: Set ADK related env vars.
        import os

        os.environ["CLAW_WORKSPACE"] = self._current_session.workspace_path
        # Map identity to git config, etc.

    @property
    def is_bootstrapped(self) -> bool:
        return self._current_session is not None and self._current_session.active

    @property
    def config(self) -> Optional[SessionState]:
        return self._current_session
