import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.pydanticai_models import ResumeAnalysis


@pytest.mark.asyncio
async def test_evaluate_resume_runs_agent_and_returns_analysis():
    sample_data = {
        "match_score": 80,
        "key_matches": ["Python"],
        "missing_skills": ["Docker"],
        "strengths": ["Skill1", "Skill2", "Skill3"],
        "weaknesses": ["Weak1", "Weak2"],
        "section_analysis": {"Summary": "Good"},
    }

    with (
        patch("app.services.resume_customizer.resume_evaluator.Agent") as MockAgent,
        patch(
            "app.services.resume_customizer.resume_evaluator.EvidenceTracker"
        ) as MockTracker,
    ):
        import app.services.resume_customizer.resume_evaluator as svc

        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=ResumeAnalysis(**sample_data))
        MockAgent.return_value = agent_instance
        
        # Create a mock for EvidenceTracker with async methods
        tracker_instance = MagicMock()
        tracker_instance.extract_facts = AsyncMock()
        MockTracker.return_value = tracker_instance

        evaluator = svc.ResumeEvaluator()
        result = await evaluator.evaluate_resume("RES", "JOB")

        MockTracker.assert_called_once_with("RES")
        MockAgent.assert_called_once()
        agent_instance.run.assert_awaited()
        assert isinstance(result, ResumeAnalysis)
        args, kwargs = MockAgent.call_args
        assert kwargs["model"] == "anthropic:claude-3-7-sonnet-latest"
        assert kwargs["output_type"] is svc.ResumeAnalysis
        assert "resume evaluator" in kwargs["system_prompt"]
