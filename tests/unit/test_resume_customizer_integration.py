import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.resume_customizer.executor import ResumeCustomizer
from app.schemas.pydanticai_models import ResumeAnalysis, CustomizationPlan, VerificationResult


@pytest.mark.asyncio
async def test_customize_resume_success(sample_resume, sample_job_description):
    customizer = ResumeCustomizer()
    events = []

    async def progress(stage: str, pct: int, msg: str) -> None:
        events.append((stage, pct, msg))

    customizer.set_progress_callback(progress)

    analysis = ResumeAnalysis(
        match_score=80,
        key_matches=["Python"],
        missing_skills=["Docker"],
        strengths=["S1", "S2", "S3"],
        weaknesses=["W1", "W2"],
        section_analysis={"experience": "ok"},
    )
    plan = CustomizationPlan(
        target_score=90,
        section_changes={"experience": "add metrics"},
        keywords_to_add=["Docker"],
        format_improvements=["Bullets"],
        change_explanations={"experience": "Add metrics"},
    )
    verification = VerificationResult(
        is_truthful=True,
        issues=[],
        final_score=90,
        improvement=10,
        section_assessments={"experience": "good"},
    )

    with (
        patch.object(customizer.evaluator, "evaluate_resume", AsyncMock(return_value=analysis)),
        patch.object(customizer.planner, "plan_customization", AsyncMock(return_value=plan)),
        patch.object(customizer.implementer, "implement_changes", AsyncMock(return_value="UPDATED")),
        patch.object(customizer.verifier, "verify_customization", AsyncMock(return_value=verification)),
        patch.object(customizer.diff_service, "html_diff_view", return_value="<diff>") as mock_diff,
    ):
        result = await customizer.customize_resume(sample_resume, sample_job_description, "tmpl", "id1")

    assert result["success"]
    assert result["customized_resume"] == "UPDATED"
    assert mock_diff.called
    assert any(e[0] == "evaluation" for e in events)
    assert events[-1][0] == "verification"


@pytest.mark.asyncio
async def test_customize_resume_error(sample_resume, sample_job_description):
    customizer = ResumeCustomizer()
    async def noop_progress(*args):
        pass
    customizer.set_progress_callback(noop_progress)  # Use an async no-op function

    with (
        patch.object(customizer.evaluator, "evaluate_resume", AsyncMock(return_value=ResumeAnalysis(match_score=80, key_matches=[], missing_skills=[], strengths=["s1", "s2", "s3"], weaknesses=["w1", "w2"], section_analysis={"experience": "ok"}))),
        patch.object(customizer.planner, "plan_customization", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        result = await customizer.customize_resume(sample_resume, sample_job_description, "tmpl", "id2")

    assert not result["success"]
    assert "boom" in result["error"]
