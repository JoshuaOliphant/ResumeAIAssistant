import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.pydanticai_models import CustomizationPlan, ResumeAnalysis


@pytest.mark.asyncio
async def test_plan_customization_runs_agent_and_returns_plan():
    analysis_data = {
        "match_score": 70,
        "key_matches": ["Python"],
        "missing_skills": ["Docker", "Kubernetes"],
        "strengths": ["S1", "S2", "S3"],
        "weaknesses": ["W1", "W2"],
        "section_analysis": {"Experience": "Needs metrics", "Skills": "Missing keywords"},
    }
    plan_data = {
        "target_score": 85,
        "section_changes": {"Experience": "Add metrics", "Skills": "Include Docker"},
        "keywords_to_add": ["Docker"],
        "format_improvements": ["Use bullets"],
        "change_explanations": {"Experience": "Metrics show impact"},
    }

    with patch("app.services.resume_customizer.resume_planner.Agent") as MockAgent:
        import app.services.resume_customizer.resume_planner as svc

        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=CustomizationPlan(**plan_data))
        MockAgent.return_value = agent_instance

        planner = svc.ResumePlanner()
        analysis = ResumeAnalysis(**analysis_data)
        result = await planner.plan_customization("RES", "JOB", analysis)

        MockAgent.assert_called_once()
        agent_instance.run.assert_awaited()
        assert isinstance(result, CustomizationPlan)
        args, kwargs = MockAgent.call_args
        assert kwargs["model"] == "anthropic:claude-3-7-sonnet-latest"
        assert kwargs["output_type"] is svc.CustomizationPlan
        assert "resume writer" in kwargs["system_prompt"]
