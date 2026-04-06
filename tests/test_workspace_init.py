from adk_claw.workspace_init import (
    initialize_global_brain,
    initialize_session_workspace,
    assemble_instructions,
)


def test_global_brain_initialization(tmp_path, monkeypatch):
    global_dir = tmp_path / ".adk-claw"
    monkeypatch.setattr("adk_claw.workspace_init.GLOBAL_CONFIG_DIR", global_dir)

    initialize_global_brain()

    expected_files = [
        "SOUL.md",
        "IDENTITY.md",
        "USER.md",
        "HEARTBEAT.md",
        "memory",
    ]
    for filename in expected_files:
        assert (global_dir / filename).exists(), f"{filename} missing"


def test_session_workspace_initialization(tmp_path):
    workspace = tmp_path / "session-abc"
    initialize_session_workspace(workspace)

    assert (workspace / "src").exists()
    assert (workspace / "SESSION.md").exists()


def test_instruction_assembly(tmp_path, monkeypatch):
    global_dir = tmp_path / ".adk-claw"
    monkeypatch.setattr("adk_claw.workspace_init.GLOBAL_CONFIG_DIR", global_dir)

    workspace = tmp_path / "session-abc"
    initialize_global_brain()
    initialize_session_workspace(workspace)

    # Modify some files to check content
    (global_dir / "SOUL.md").write_text("Soul content", encoding="utf-8")
    (workspace / "SESSION.md").write_text("Session content", encoding="utf-8")
    # Simulate an AGENTS.md from a project
    (workspace / "AGENTS.md").write_text("Agents content", encoding="utf-8")

    instr = assemble_instructions(workspace)

    assert "--- From Global SOUL.md ---" in instr
    assert "Soul content" in instr
    assert "--- From Session SESSION.md ---" in instr
    assert "Session content" in instr
    assert "--- From AGENTS.md ---" in instr
    assert "Agents content" in instr
