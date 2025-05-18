import logfire
from pydantic_ai import Agent, ModelRetry

from app.services.evidence_tracker import EvidenceTracker
from app.schemas.pydanticai_models import VerificationResult


class ResumeVerifier:
    """Validate that a customized resume is truthful and high quality."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "anthropic:claude-3-7-sonnet-latest"
        self.evidence_tracker: EvidenceTracker | None = None

    async def verify_customization(
        self, original: str, customized: str, job: str
    ) -> VerificationResult:
        """Verify truthfulness and quality of the customized resume.

        Args:
            original: The original resume text.
            customized: The customized resume text.
            job: The job description text.

        Returns:
            VerificationResult: Structured verification outcome.
        """
        self.evidence_tracker = EvidenceTracker(original)

        try:
            agent = Agent(
                model=self.model,
                output_type=VerificationResult,
                system_prompt=(
                    "You are an expert resume verifier who ensures customized resumes "
                    "remain truthful and accurately represent the original content."
                ),
            )

            @agent.output_validator()
            async def validate_verification(ctx, result: VerificationResult) -> VerificationResult:
                """Ensure verification is thorough and accurate."""
                if result.is_truthful and len(result.issues) > 0:
                    raise ModelRetry(
                        "Inconsistent result: Cannot be truthful while having issues"
                    )
                if not (0 <= result.final_score <= 100):
                    raise ModelRetry("Final score must be between 0-100")
                if not (0 <= result.improvement <= 100):
                    raise ModelRetry("Improvement must be between 0-100")
                return result

            prompt = f"""
            Verify the truthfulness and quality of this customized resume.

            ORIGINAL RESUME:
            {original}

            CUSTOMIZED RESUME:
            {customized}

            JOB DESCRIPTION:
            {job}

            Carefully verify:
            1. Whether all content in the customized resume is supported by the original
            2. If any information has been fabricated or exaggerated
            3. The final match score (0-100) with the job description
            4. How much the score improved from the original
            5. Assessment of each major section's customization
            """

            result: VerificationResult = await agent.run(prompt)

            unsupported = self.evidence_tracker.verify(customized)
            if unsupported:
                result.is_truthful = False
                result.issues.extend([f"Unverified line: {line}" for line in unsupported])

            return result
        except Exception as exc:  # noqa: D401
            logfire.error(f"Verification failed: {str(exc)}", exc_info=True)
            raise
