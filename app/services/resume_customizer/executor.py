import uuid
from typing import Awaitable, Callable

import logfire

from app.services.resume_customizer.resume_evaluator import ResumeEvaluator
from app.services.resume_customizer.resume_planner import ResumePlanner
from app.services.resume_customizer.resume_implementer import ResumeImplementer
from app.services.resume_customizer.resume_verifier import ResumeVerifier
from app.services.diff_service import DiffGenerator
from app.services.metrics import track_latency, metrics_collector
from app.schemas.pydanticai_models import (
    ResumeAnalysis,
    CustomizationPlan,
    VerificationResult,
)


class ResumeCustomizer:
    """End-to-end resume customization using resume optimizer services."""

    def __init__(self) -> None:
        """Initialize the underlying services and logging configuration."""
        logfire.configure(service_name="resume-customizer")
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

                diff_html = self._generate_diff(resume_content, customized_resume)

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
        """Send a progress update via the configured callback."""
        if self.progress_callback:
            await self.progress_callback(stage, percentage, message)

    async def _evaluate_resume(self, resume: str, job: str) -> ResumeAnalysis:
        """Run the evaluation stage using :class:`ResumeEvaluator`."""
        with track_latency("evaluation"):
            result = await self.evaluator.evaluate_resume(resume, job)
        metrics_collector.increment("evaluations")
        return result

    async def _create_plan(
        self, resume: str, job: str, analysis: ResumeAnalysis
    ) -> CustomizationPlan:
        """Generate an optimization plan based on the evaluation results."""
        with track_latency("planning"):
            result = await self.planner.plan_customization(resume, job, analysis)
        metrics_collector.increment("plans")
        return result

    async def _implement_changes(
        self, resume: str, job: str, plan: CustomizationPlan, template_id: str
    ) -> str:
        """Apply the customization plan using :class:`ResumeImplementer`."""
        with track_latency("implementation"):
            result = await self.implementer.implement_changes(resume, job, plan, template_id)
        metrics_collector.increment("implementations")
        return result

    async def _verify_customization(
        self, original: str, customized: str, job: str
    ) -> VerificationResult:
        """Validate that the customized resume remains truthful."""
        with track_latency("verification"):
            result = await self.verifier.verify_customization(original, customized, job)
        metrics_collector.increment("verifications")
        return result

    def _generate_diff(self, original: str, customized: str) -> str:
        """Generate an HTML diff comparing the original and customized resumes."""
        with track_latency("diff_generation"):
            result = self.diff_service.html_diff_view(original, customized)
        metrics_collector.increment("diffs")
        return result
