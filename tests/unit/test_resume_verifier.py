from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.pydanticai_models import VerificationResult


@pytest.mark.asyncio
async def test_verify_customization_runs_agent_and_checks_truthfulness():
    data = VerificationResult(
        is_truthful=True,
        issues=[],
        final_score=90,
        improvement=10,
        section_assessments={"Summary": "Good"},
    )

    with patch("app.services.resume_customizer.resume_verifier.Agent") as MockAgent, patch(
        "app.services.resume_customizer.resume_verifier.EvidenceTracker"
    ) as MockTracker:
        import app.services.resume_customizer.resume_verifier as svc

        agent_instance = MagicMock()
        agent_instance.run = AsyncMock(return_value=data)
        MockAgent.return_value = agent_instance

        tracker_instance = MagicMock()
        tracker_instance.verify.return_value = ["Fake line"]
        MockTracker.return_value = tracker_instance

        verifier = svc.ResumeVerifier()
        result = await verifier.verify_customization("ORIG", "CUST", "JOB")

        MockTracker.assert_called_once_with("ORIG")
        agent_instance.run.assert_awaited()
        tracker_instance.verify.assert_called_once_with("CUST")
        assert not result.is_truthful
        assert "Unverified line" in result.issues[0]

