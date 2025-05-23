from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "claude_prompts"


def load_prompt(filename: str) -> str:
    """Load a prompt file from the claude_prompts directory."""
    path = PROMPTS_DIR / filename
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Prompt file not found: {path}") from exc
