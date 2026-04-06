"""
Workspace initialization for adk-claw.

Automatically sets up the Tier 1 Global Brain and Tier 2 Session Workspaces.
"""

import logging
from pathlib import Path
from importlib import resources

from adk_claw.config import GLOBAL_CONFIG_DIR

logger = logging.getLogger(__name__)

GLOBAL_INSTRUCTION_MARKERS = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "HEARTBEAT.md",
    "MEMORY.md",
]


def _get_starter_content(filename: str) -> str:
    """Helper to load starter content from the resources directory."""
    try:
        resource_path = resources.files("adk_claw.resources.starter_files").joinpath(
            filename
        )
        return resource_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to load resource {filename}: {e}")
        return ""


def initialize_global_brain() -> None:
    """
    Bootstraps the Global Brain (Tier 1) at ~/.adk-claw/.
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Global memory/ directory
    memory_dir = GLOBAL_CONFIG_DIR / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    for filename in GLOBAL_INSTRUCTION_MARKERS:
        if filename == "MEMORY.md":
            continue

        file_path = GLOBAL_CONFIG_DIR / filename
        if not file_path.exists():
            content = _get_starter_content(filename)
            if content:
                try:
                    file_path.write_text(content, encoding="utf-8")
                    logger.debug(f"Created global {filename}")
                except Exception as e:
                    logger.warning(f"Failed to create {filename}: {e}")


def initialize_session_workspace(workspace_path: Path) -> None:
    """
    Bootstraps the Session Workspace (Tier 2).
    """
    logger.info(f"Initializing session workspace at {workspace_path}")
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create the src/ directory for Tier 3 projects
    src_dir = workspace_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Bootstraps the empty SESSION.md scratchpad
    session_file = workspace_path / "SESSION.md"
    if not session_file.exists():
        try:
            session_file.write_text(
                "# Session Context\n\nActive scratchpad for this session.\n",
                encoding="utf-8",
            )
            logger.debug("Created SESSION.md scratchpad")
        except Exception as e:
            logger.warning(f"Failed to create SESSION.md: {e}")


def assemble_instructions(workspace_path: Path) -> str:
    """
    Loads and assembles system instructions from Tier 1 (Global) and Tier 2 (Session).
    """
    project_instructions = []

    # 1. Load Tier 1 Global Persona and Memory
    for marker in GLOBAL_INSTRUCTION_MARKERS:
        marker_path = GLOBAL_CONFIG_DIR / marker
        if marker_path.exists():
            try:
                content = marker_path.read_text(encoding="utf-8").strip()
                if content:
                    project_instructions.append(
                        f"\n--- From Global {marker} ---\n{content}"
                    )
            except Exception as e:
                logger.warning("Failed to read %s: %s", marker, e)

    # 2. Load Tier 2 Session Scratchpad
    session_path = workspace_path / "SESSION.md"
    if session_path.exists():
        try:
            content = session_path.read_text(encoding="utf-8").strip()
            if content:
                project_instructions.append(
                    f"\n--- From Session SESSION.md ---\n{content}"
                )
        except Exception as e:
            logger.warning("Failed to read session cache: %s", e)

    # 3. Load Project-specific Agents/Tools if they exist at workspace root
    for marker in ["AGENTS.md", "TOOLS.md"]:
        marker_path = workspace_path / marker
        if marker_path.exists():
            try:
                content = marker_path.read_text(encoding="utf-8").strip()
                if content:
                    project_instructions.append(f"\n--- From {marker} ---\n{content}")
            except Exception:
                pass

    return "\n\n## System Instructions\n" + "\n".join(project_instructions)


def get_subagent_instructions(workspace_path: Path) -> str:
    """
    Returns a slim instruction set for subagents.
    """
    project_instructions = []

    # Subagents keep the global identity
    for marker in ["SOUL.md", "IDENTITY.md"]:
        marker_path = GLOBAL_CONFIG_DIR / marker
        if marker_path.exists():
            try:
                content = marker_path.read_text(encoding="utf-8").strip()
                if content:
                    project_instructions.append(
                        f"\n--- From Global {marker} ---\n{content}"
                    )
            except Exception:
                pass

    # Subagents get AGENTS.md and TOOLS.md for specialized focus from workspace
    subagent_markers = ["AGENTS.md", "TOOLS.md", "SESSION.md"]
    for marker in subagent_markers:
        marker_path = workspace_path / marker
        if marker_path.exists():
            try:
                content = marker_path.read_text(encoding="utf-8").strip()
                if content:
                    project_instructions.append(f"\n--- From {marker} ---\n{content}")
            except Exception as e:
                logger.warning("Failed to read %s: %s", marker, e)

    return "\n\n## Project-Specific Instructions\n" + "\n".join(project_instructions)
