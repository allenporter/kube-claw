"""
YAML Configuration Loader for adk-claw.

Supports two levels of configuration:
- Global: ``~/.adk-claw/config.yaml``
- Project: ``.adk-claw.yaml`` in the workspace root

Project-level settings override global settings via dict merge.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

GLOBAL_CONFIG_DIR = Path.home() / ".adk-claw"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"
PROJECT_CONFIG_FILE = ".adk-claw.yaml"


@dataclass
class AgentConfig:
    """Agent execution settings."""

    model: str | None = None
    permission_mode: str = "auto"
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class QueueConfig:
    """Queue and concurrency settings."""

    mode: str = "collect"
    debounce_ms: int = 1500
    max_concurrent: int = 4


@dataclass
class ClawConfig:
    """Top-level adk-claw configuration."""

    agent: AgentConfig = field(default_factory=AgentConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)
    channels: dict[str, Any] = field(default_factory=dict)
    mcp_servers: dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict on missing or invalid files."""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Failed to load config from %s: %s", path, e)
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *override* into *base*, returning a new dict."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(workspace_path: Path | None = None) -> ClawConfig:
    """Load and merge global + project config into a ``ClawConfig``.

    Args:
        workspace_path: Path to the project root. If ``None``, uses ``cwd()``.
    """
    global_data = _load_yaml(GLOBAL_CONFIG_FILE)

    project_root = workspace_path or Path.cwd()
    project_data = _load_yaml(project_root / PROJECT_CONFIG_FILE)

    merged = _deep_merge(global_data, project_data)

    agent_raw = merged.get("agent", {})
    queue_raw = merged.get("queue", {})

    return ClawConfig(
        agent=AgentConfig(
            model=agent_raw.get("model"),
            permission_mode=agent_raw.get("permission_mode", "auto"),
            env=agent_raw.get("env", {}),
        ),
        queue=QueueConfig(
            mode=queue_raw.get("mode", "collect"),
            debounce_ms=queue_raw.get("debounce_ms", 1500),
            max_concurrent=queue_raw.get("max_concurrent", 4),
        ),
        channels=merged.get("channels", {}),
        mcp_servers=merged.get("mcpServers")
        or merged.get("mcp_servers")
        or merged.get("mcp", {}),
    )
