from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "claude_prompts"

# Ensure the prompts directory exists
if not PROMPTS_DIR.exists():
    raise RuntimeError(f"Claude prompts directory not found: {PROMPTS_DIR}")


def load_prompt(filename: str) -> str:
    """Load a prompt file from the claude_prompts directory."""
    path = PROMPTS_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Prompt file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"Failed to decode prompt file {path}: {exc}") from exc
