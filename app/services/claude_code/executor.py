import uuid
from typing import Awaitable, Callable

import logfire

from app.services.claude_code.resume_evaluator import ResumeEvaluator
from app.services.claude_code.resume_planner import ResumePlanner
from app.services.claude_code.resume_implementer import ResumeImplementer
from app.services.claude_code.resume_verifier import ResumeVerifier
from app.services.diff_service import DiffGenerator
from app.schemas.pydanticai_models import (
    ResumeAnalysis,
    CustomizationPlan,
    VerificationResult,
)


class ResumeCustomizer:
    """End-to-end resume customization using Claude Code services."""

    def __init__(self) -> None:
        logfire.configure(app_name="resume-customizer")
        logfire.instrument_pydantic_ai()
        self.progress_callback: Callable[[str, int, str], Awaitable[None]] | None = None
        self.model = "anthropic:claude-3-7-sonnet-latest"
        self.evaluator = ResumeEvaluator(self.model)
        self.planner = ResumePlanner(self.model)
        self.implementer = ResumeImplementer(self.model)
        self.verifier = ResumeVerifier(self.model)
        self.diff_service = DiffGenerator()

    def set_progress_callback(
        self, callback: Callable[[str, int, str], Awaitable[None]] | None
    ) -> None:
        """Set a callback for progress updates."""
        self.progress_callback = callback

    async def customize_resume(
        self,
        resume_content: str,
        job_description: str,
        template_id: str,
        customization_id: str | None = None,
    ) -> dict:
        """Customize a resume for a job description using a template."""
        customization_id = customization_id or str(uuid.uuid4())

        with logfire.span("customize_resume", {"customization_id": customization_id}):
            try:
                await self._update_progress("evaluation", 0, "Starting evaluation")
                analysis = await self._evaluate_resume(resume_content, job_description)
                await self._update_progress("evaluation", 100, "Evaluation complete")

                await self._update_progress("planning", 0, "Creating improvement plan")
                plan = await self._create_plan(resume_content, job_description, analysis)
                await self._update_progress("planning", 100, "Plan created")

                await self._update_progress("implementation", 0, "Implementing changes")
                customized_resume = await self._implement_changes(
                    resume_content, job_description, plan, template_id
                )
                await self._update_progress("implementation", 100, "Changes implemented")

                await self._update_progress("verification", 0, "Verifying truthfulness")
                verification = await self._verify_customization(
                    resume_content, customized_resume, job_description
                )
                await self._update_progress("verification", 100, "Verification complete")

                diff_html = await self._generate_diff(resume_content, customized_resume)

                return {
                    "customization_id": customization_id,
                    "original_resume": resume_content,
                    "customized_resume": customized_resume,
                    "analysis": analysis.dict(),
                    "plan": plan.dict(),
                    "verification": verification.dict(),
                    "diff_html": diff_html,
                    "success": True,
                }
            except Exception as exc:  # pragma: no cover - unexpected errors
                logfire.error("Customization failed", error=str(exc), exc_info=True)
                await self._update_progress("error", 100, f"Error: {str(exc)}")
                return {
                    "customization_id": customization_id,
                    "success": False,
                    "error": str(exc),
                }

    async def _update_progress(self, stage: str, percentage: int, message: str) -> None:
        if self.progress_callback:
            await self.progress_callback(stage, percentage, message)

    async def _evaluate_resume(self, resume: str, job: str) -> ResumeAnalysis:
        return await self.evaluator.evaluate_resume(resume, job)

    async def _create_plan(
        self, resume: str, job: str, analysis: ResumeAnalysis
    ) -> CustomizationPlan:
        return await self.planner.plan_customization(resume, job, analysis)

    async def _implement_changes(
        self, resume: str, job: str, plan: CustomizationPlan, template_id: str
    ) -> str:
        return await self.implementer.implement_changes(resume, job, plan, template_id)

    async def _verify_customization(
        self, original: str, customized: str, job: str
    ) -> VerificationResult:
        return await self.verifier.verify_customization(original, customized, job)

    async def _generate_diff(self, original: str, customized: str) -> str:
        return self.diff_service.html_diff_view(original, customized)
