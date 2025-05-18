import logfire
from pydantic_ai import Agent, ModelRetry

from app.schemas.pydanticai_models import CustomizationPlan, ResumeAnalysis


class ResumePlanner:
    """Generate a strategic plan to improve a resume."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "anthropic:claude-3-7-sonnet-latest"

    def _prioritize_sections(self, analysis: ResumeAnalysis) -> list[str]:
        """Return sections ordered by impact based on analysis notes."""
        keywords = ["missing", "lack", "weak", "improve"]
        high_impact: list[str] = []
        low_impact: list[str] = []
        for section, note in analysis.section_analysis.items():
            note_lower = note.lower()
            if any(k in note_lower for k in keywords):
                high_impact.append(section)
            else:
                low_impact.append(section)
        return high_impact + low_impact

    async def plan_customization(
        self, resume: str, job: str, analysis: ResumeAnalysis
    ) -> CustomizationPlan:
        """Create a customization plan based on evaluation results.

        Args:
            resume: The resume text.
            job: The job description.
            analysis: Results from ``ResumeEvaluator``.

        Returns:
            CustomizationPlan: Structured plan for improvements.
        """
        try:
            agent = Agent(
                model=self.model,
                output_type=CustomizationPlan,
                system_prompt=(
                    "You are an expert resume writer specializing in strategic resume "
                    "customization to match specific job descriptions."
                ),
            )

            @agent.output_validator()
            async def validate_plan(ctx, result: CustomizationPlan) -> CustomizationPlan:
                """Ensure the plan addresses key gaps."""
                if not (analysis.match_score <= result.target_score <= 100):
                    raise ModelRetry(
                        f"Target score ({result.target_score}) must be higher than "
                        f"current score ({analysis.match_score}) and at most 100"
                    )
                if len(result.section_changes) < 2:
                    raise ModelRetry("Plan must include changes for at least 2 sections")
                if len(result.keywords_to_add) < max(1, len(analysis.missing_skills) // 2):
                    raise ModelRetry("Plan should incorporate more missing keywords")
                return result

            prioritized_sections = ", ".join(self._prioritize_sections(analysis))
            prompt = f"""
Create a strategic plan to customize this resume for the job description.

RESUME:
{resume}

JOB DESCRIPTION:
{job}

CURRENT ANALYSIS:
{analysis.json()}

Prioritize updates to these sections for maximum impact: {prioritized_sections}

Develop a comprehensive plan that includes:
1. Target match score after changes
2. Specific changes to make for each major section
3. Keywords and skills to incorporate from the job description
4. Format or structure improvements
5. Clear explanation for each change, connecting it to the job requirements

Focus on substantive improvements that meaningfully increase the match score.
IMPORTANT: All changes must maintain truthfulness - do not suggest fabricating experience or skills.
"""
            return await agent.run(prompt)
        except Exception as exc:  # noqa: D401
            logfire.error(f"Planning failed: {str(exc)}", exc_info=True)
            raise RuntimeError(f"Resume planning failed: {str(exc)}") from exc
