import logfire
from pydantic_ai import Agent

from app.schemas.pydanticai_models import CustomizationPlan
from app.services.evidence_tracker import EvidenceTracker
from app.services.export_service import TemplateProcessor


class ResumeImplementer:
    """Apply customization plans to produce updated resume content."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "anthropic:claude-3-7-sonnet-latest"
        self.evidence_tracker: EvidenceTracker | None = None
        self.template_processor = TemplateProcessor()
        self.modifications: dict | None = None

    async def implement_changes(
        self,
        resume: str,
        job: str,
        plan: CustomizationPlan,
        template_id: str,
    ) -> str:
        """Apply the customization plan to the resume."""
        self.evidence_tracker = EvidenceTracker(resume)
        try:
            agent = Agent(
                model=self.model,
                output_type=str,
                system_prompt=(
                    "You are an expert resume writer who specializes in customizing "
                    "resumes to match job descriptions while maintaining truthfulness."
                ),
            )

            prompt = f"""
            Customize this resume according to the improvement plan and template.

            ORIGINAL RESUME:
            {resume}

            JOB DESCRIPTION:
            {job}

            IMPROVEMENT PLAN:
            {plan.json()}

            TEMPLATE ID:
            {template_id}

            Instructions:
            1. Apply all the changes specified in the improvement plan
            2. Format the resume according to the template structure
            3. Incorporate the keywords and skills identified in the plan
            4. Ensure all content remains truthful to the original resume
            5. Return the complete customized resume in a clean, professional format

            The resume should be significantly improved for this specific job while
            maintaining truthfulness and following the selected template's structure.
            """

            updated_resume = await agent.run(prompt)

            self.modifications = await self._track_modifications(resume, updated_resume)
            unverified = self.evidence_tracker.verify(updated_resume)
            if unverified:
                logfire.warning(
                    "Unverified resume lines detected", count=len(unverified)
                )

            return updated_resume
        except Exception as exc:  # noqa: D401
            logfire.error(f"Implementation failed: {str(exc)}", exc_info=True)
            raise

    async def _track_modifications(self, original: str, updated: str) -> dict:
        """Track modifications for each resume section."""
        try:
            processor = self.template_processor
            original_sections = await processor.parse_resume_to_context(original)
            updated_sections = await processor.parse_resume_to_context(updated)

            modifications: dict = {}
            for section, orig_text in original_sections.items():
                new_text = updated_sections.get(section, "")
                if orig_text != new_text:
                    modifications[section] = {
                        "original": orig_text,
                        "updated": new_text,
                    }

            for section, new_text in updated_sections.items():
                if section not in original_sections:
                    modifications[section] = {"original": "", "updated": new_text}

            return modifications
        except Exception as exc:  # noqa: D401
            logfire.error(
                f"Modification tracking failed: {str(exc)}", exc_info=True
            )
            return {}
