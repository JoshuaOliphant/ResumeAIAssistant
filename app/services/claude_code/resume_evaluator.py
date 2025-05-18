import logfire
from pydantic_ai import Agent, ModelRetry

from app.schemas.pydanticai_models import ResumeAnalysis
from app.services.evidence_tracker import EvidenceTracker


class ResumeEvaluator:
    """Evaluate how well a resume matches a job description."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "anthropic:claude-3-7-sonnet-latest"
        self.evidence_tracker: EvidenceTracker | None = None

    async def evaluate_resume(self, resume: str, job: str) -> ResumeAnalysis:
        """Analyze resume-job alignment.

        Args:
            resume: The resume text.
            job: The job description text.

        Returns:
            ResumeAnalysis: Structured evaluation result.
        """
        # Initialize evidence tracker to capture baseline resume facts
        self.evidence_tracker = EvidenceTracker(resume)
        # Extract and track baseline facts from resume
        await self.evidence_tracker.extract_facts()

        try:
            agent = Agent(
                model=self.model,
                output_type=ResumeAnalysis,
                system_prompt=(
                    "You are an expert resume evaluator specializing in analyzing "
                    "how well resumes match job descriptions."
                ),
            )

            @agent.output_validator()
            async def validate_analysis(ctx, result: ResumeAnalysis) -> ResumeAnalysis:  # noqa: D401
                """Ensure analysis quality and retry if necessary."""
                if not (0 <= result.match_score <= 100):
                    raise ModelRetry("Match score must be between 0-100")
                if len(result.strengths) < 3:
                    raise ModelRetry("Identify at least 3 strengths")
                if len(result.weaknesses) < 2:
                    raise ModelRetry("Identify at least 2 areas for improvement")
                return result

            prompt = f"""
            Evaluate how well this resume matches the job description.

            RESUME:
            {resume}

            JOB DESCRIPTION:
            {job}

            Provide a detailed analysis including:
            1. Overall match score (0-100)
            2. Key skills/qualifications that match
            3. Important skills/qualifications missing from the resume
            4. The resume's strengths for this specific job
            5. Areas where the resume could be improved
            6. An analysis of each major resume section

            Be specific, objective, and focus on factual matches rather than subjective judgments.
            """

            return await agent.run(prompt)
        except Exception as exc:  # noqa: D401
            logfire.error(f"Evaluation failed: {str(exc)}", exc_info=True)
            raise RuntimeError(f"Resume evaluation failed: {str(exc)}") from exc
