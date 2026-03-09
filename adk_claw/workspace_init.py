"""
Workspace initialization for adk-claw.

Automatically sets up a workspace with a git repository and starter
Markdown files for agent guidance and memory.
"""

import logging
import subprocess
from pathlib import Path
from importlib import resources

logger = logging.getLogger(__name__)

INSTRUCTION_MARKERS = [
    "AGENTS.md",
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "TOOLS.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
]


def _get_starter_content(filename: str) -> str:
    """Helper to load starter content from the resources directory."""
    try:
        # Use modern importlib.resources.files (Python 3.9+)
        resource_path = resources.files("adk_claw.resources.starter_files").joinpath(
            filename
        )
        return resource_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to load resource {filename}: {e}")
        return ""


def initialize_workspace(project_root: Path) -> None:
    """
    Sets up the workspace with git and starter files.
    """
    logger.info(f"Initializing workspace at {project_root}")

    # 1. Git initialization
    if not (project_root / ".git").exists():
        try:
            logger.info("Initializing git repository...")
            subprocess.run(
                ["git", "init"], cwd=project_root, check=True, capture_output=True
            )
        except Exception as e:
            logger.warning(f"Failed to initialize git: {e}")

    # 2. .adk directory
    adk_dir = project_root / ".adk"
    is_new_adk = not adk_dir.exists()
    adk_dir.mkdir(parents=True, exist_ok=True)

    # 3. Starter files
    for filename in INSTRUCTION_MARKERS:
        if filename in ["BOOTSTRAP.md", "MEMORY.md"]:
            continue

        file_path = project_root / filename
        if not file_path.exists():
            content = _get_starter_content(filename)
            if content:
                try:
                    file_path.write_text(content, encoding="utf-8")
                    logger.debug(f"Created {filename}")
                except Exception as e:
                    logger.warning(f"Failed to create {filename}: {e}")

    # 4. memory/ directory
    memory_dir = project_root / "memory"
    if not memory_dir.exists():
        try:
            memory_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created memory/ directory")
        except Exception as e:
            logger.warning(f"Failed to create memory directory: {e}")

    # 5. BOOTSTRAP.md (only on brand new .adk)
    bootstrap_path = project_root / "BOOTSTRAP.md"
    if is_new_adk and not bootstrap_path.exists():
        try:
            bootstrap_path.write_text(
                "# Welcome to your new workspace!\n\nThis is a brand new project setup. "
                "Explore the files and start building.\n",
                encoding="utf-8",
            )
            logger.info("Created BOOTSTRAP.md")
        except Exception as e:
            logger.warning(f"Failed to create BOOTSTRAP.md: {e}")


def assemble_instructions(workspace_path: Path) -> str:
    """
    Loads and assembles system instructions from priority-ordered markers.
    """
    project_instructions = []
    for marker in INSTRUCTION_MARKERS:
        marker_path = workspace_path / marker
        if marker_path.exists():
            try:
                # Add a descriptive header for each injected file
                content = marker_path.read_text(encoding="utf-8").strip()
                if content:
                    project_instructions.append(f"\n--- From {marker} ---\n{content}")
            except Exception as e:
                logger.warning("Failed to read %s: %s", marker, e)

    return "\n\n## Project-Specific Instructions\n" + "\n".join(project_instructions)


def get_subagent_instructions(workspace_path: Path) -> str:
    """
    Returns a slim instruction set for subagents.
    """
    project_instructions = []
    # Subagents only get AGENTS.md and TOOLS.md for specialized focus
    subagent_markers = ["AGENTS.md", "TOOLS.md"]
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
