"""Evidence tracking utilities for resume customization."""

from typing import List, Set
import logfire


class EvidenceTracker:
    """Validate that customized resume content remains truthful."""

    def __init__(self, original_resume: str) -> None:
        self.original_resume = original_resume
        self.facts = self._extract_facts(original_resume)
        logfire.info("Evidence tracker initialized", facts=len(self.facts))

    def _extract_facts(self, text: str) -> Set[str]:
        lines = {line.strip() for line in text.splitlines() if line.strip()}
        return lines

    def verify(self, updated_resume: str) -> List[str]:
        """Return list of lines not backed by the original resume."""
        updated_lines = {line.strip() for line in updated_resume.splitlines() if line.strip()}
        invalid = [line for line in updated_lines if line not in self.facts]
        if invalid:
            logfire.warning("Unverified content detected", count=len(invalid))
        return invalid
