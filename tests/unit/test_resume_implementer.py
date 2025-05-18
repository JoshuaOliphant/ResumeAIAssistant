import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.pydanticai_models import CustomizationPlan


@pytest.mark.asyncio
async def test_implement_changes_runs_agent_and_tracks_modifications():
    plan = CustomizationPlan(
        target_score=90,
        section_changes={"summary": "Add metrics"},
        keywords_to_add=["Python"],
        format_improvements=["Bullets"],
        change_explanations={"summary": "Add results"},
    )

    import app.services.resume_customizer.resume_implementer as svc
    with (
        patch.object(svc, "Agent") as MockAgent,
        patch.object(svc, "EvidenceTracker") as MockTracker,
        patch.object(svc, "TemplateProcessor") as MockProcessor,
    ):

        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value="UPDATED")
        MockAgent.return_value = agent_instance

        tracker_instance = MagicMock()
        tracker_instance.verify.return_value = []
        MockTracker.return_value = tracker_instance

        processor_instance = MagicMock()
        processor_instance.parse_resume_to_context = AsyncMock(
            side_effect=[{"summary": "OLD"}, {"summary": "NEW"}]
        )
        MockProcessor.return_value = processor_instance

        impl = svc.ResumeImplementer()
        result = await impl.implement_changes("RES", "JOB", plan, "tmpl")

        MockAgent.assert_called_once()
        agent_instance.run.assert_awaited()
        MockTracker.assert_called_once_with("RES")
        tracker_instance.verify.assert_called_once_with("UPDATED")
        assert result == "UPDATED"
        assert impl.modifications == {"summary": {"original": "OLD", "updated": "NEW"}}


@pytest.mark.asyncio
async def test_track_modifications_handles_new_sections():
    import app.services.resume_customizer.resume_implementer as svc
    with patch.object(svc, "TemplateProcessor") as MockProcessor:

        processor_instance = MagicMock()
        processor_instance.parse_resume_to_context = AsyncMock(
            side_effect=[{"header": "A"}, {"header": "A", "skills": "Python"}]
        )
        MockProcessor.return_value = processor_instance

        impl = svc.ResumeImplementer()
        mods = await impl._track_modifications("OLD", "NEW")

        expected = {"skills": {"original": "", "updated": "Python"}}
        assert mods == expected
