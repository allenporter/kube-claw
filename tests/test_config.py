"""Tests for YAML configuration loader."""

from pathlib import Path

from adk_claw.config import (
    _deep_merge,
    _load_yaml,
    load_config,
)


def test_load_yaml_missing_file(tmp_path: Path) -> None:
    """Missing file returns empty dict."""
    assert _load_yaml(tmp_path / "nope.yaml") == {}


def test_load_yaml_valid(tmp_path: Path) -> None:
    """Valid YAML file is loaded."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("agent:\n  model: gemini-2.5-pro\n")
    result = _load_yaml(cfg)
    assert result == {"agent": {"model": "gemini-2.5-pro"}}


def test_load_yaml_invalid(tmp_path: Path) -> None:
    """Invalid YAML returns empty dict."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("not: [valid: yaml: {{")
    assert _load_yaml(cfg) == {}


def test_deep_merge_flat() -> None:
    assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_deep_merge_override() -> None:
    assert _deep_merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_deep_merge_nested() -> None:
    base = {"agent": {"model": "flash", "permission_mode": "ask"}}
    override = {"agent": {"model": "pro"}}
    result = _deep_merge(base, override)
    assert result == {"agent": {"model": "pro", "permission_mode": "ask"}}


def test_load_config_defaults(tmp_path: Path) -> None:
    """No config files → all defaults."""
    config = load_config(workspace_path=tmp_path)
    assert config.agent.model is None
    assert config.agent.permission_mode == "auto"
    assert config.queue.mode == "collect"
    assert config.queue.max_concurrent == 4


def test_load_config_project_file(tmp_path: Path) -> None:
    """Project-level .adk-claw.yaml is loaded."""
    cfg = tmp_path / ".adk-claw.yaml"
    cfg.write_text("agent:\n  model: gemini-2.5-pro\nqueue:\n  mode: steer\n")
    config = load_config(workspace_path=tmp_path)
    assert config.agent.model == "gemini-2.5-pro"
    assert config.queue.mode == "steer"
    # Defaults for unset fields
    assert config.agent.permission_mode == "auto"
    assert config.queue.debounce_ms == 1500
