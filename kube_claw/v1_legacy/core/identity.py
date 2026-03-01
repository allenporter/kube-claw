import pathlib


def get_system_instruction() -> str:
    """Returns the core system instruction for the Claw agent."""
    path = pathlib.Path(__file__).parent / "system_instruction.md"
    return path.read_text()
