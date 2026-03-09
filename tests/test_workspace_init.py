from adk_claw.workspace_init import initialize_workspace, assemble_instructions


def test_workspace_initialization(tmp_path):
    project_root = tmp_path
    initialize_workspace(project_root)

    expected_files = [
        "AGENTS.md",
        "SOUL.md",
        "IDENTITY.md",
        "USER.md",
        "TOOLS.md",
        "HEARTBEAT.md",
        "BOOTSTRAP.md",
        ".adk",
        ".git",
    ]
    for filename in expected_files:
        assert (project_root / filename).exists(), f"{filename} missing"


def test_instruction_assembly(tmp_path):
    project_root = tmp_path
    initialize_workspace(project_root)

    # Modify some files to check content
    (project_root / "AGENTS.md").write_text("Agents content", encoding="utf-8")
    (project_root / "SOUL.md").write_text("Soul content", encoding="utf-8")

    instr = assemble_instructions(project_root)

    assert "--- From AGENTS.md ---" in instr
    assert "Agents content" in instr
    assert "--- From SOUL.md ---" in instr
    assert "Soul content" in instr
    # Other starter files should also be present
    assert "--- From IDENTITY.md ---" in instr


def test_bootstrap_only_once(tmp_path):
    project_root = tmp_path
    # First init
    initialize_workspace(project_root)
    assert (project_root / "BOOTSTRAP.md").exists()

    # Delete and init again
    (project_root / "BOOTSTRAP.md").unlink()
    initialize_workspace(project_root)
    assert not (project_root / "BOOTSTRAP.md").exists()
