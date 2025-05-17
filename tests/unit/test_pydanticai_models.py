import pytest
from pydantic import ValidationError

from app.schemas.pydanticai_models import (
    ResumeAnalysis,
    CustomizationPlan,
    ImplementationResult,
    EvidenceItem,
    VerificationResult,
    WebSocketProgressUpdate,
    WorkflowStage,
)


def _sample_resume_analysis_data():
    return {
        "match_score": 72,
        "key_matches": ["Python", "REST APIs"],
        "missing_skills": ["Docker"],
        "strengths": ["5 years Python"],
        "weaknesses": ["Limited leadership experience"],
        "section_analysis": {"Experience": "Relevant"},
    }


def test_resume_analysis_validation():
    data = _sample_resume_analysis_data()
    analysis = ResumeAnalysis(**data)
    assert analysis.match_score == 72

    with pytest.raises(ValidationError):
        ResumeAnalysis(**{**data, "match_score": 150})


def test_customization_plan_validation():
    data = {
        "target_score": 90,
        "section_changes": {"Summary": "Add metrics"},
        "keywords_to_add": ["Docker"],
        "format_improvements": ["Use bullet points"],
        "change_explanations": {"Docker": "Emphasize containerization"},
    }
    plan = CustomizationPlan(**data)
    assert plan.target_score == 90

    with pytest.raises(ValidationError):
        CustomizationPlan(**{**data, "target_score": -5})


def test_implementation_and_verification_results():
    impl = ImplementationResult(
        updated_sections={"Skills": "Python, Docker"},
        final_score=88,
        applied_keywords=["Docker"],
    )
    assert impl.final_score == 88

    with pytest.raises(ValidationError):
        ImplementationResult(
            updated_sections={},
            final_score=101,
            applied_keywords=[],
        )

    ver = VerificationResult(
        is_truthful=True,
        final_score=88,
        improvement=16,
        section_assessments={"Summary": "Improved"},
    )
    assert ver.issues == []


def test_evidence_item_and_progress_update():
    evidence = EvidenceItem(claim="Led migration", evidence="Docs", verified=True)
    assert evidence.verified

    update = WebSocketProgressUpdate(
        stage=WorkflowStage.PLANNING,
        percentage=40,
        overall_progress=25,
    )
    assert update.stage == WorkflowStage.PLANNING

    with pytest.raises(ValidationError):
        WebSocketProgressUpdate(stage="bad", percentage=10, overall_progress=5)
        
    with pytest.raises(ValidationError):
        WebSocketProgressUpdate(stage=WorkflowStage.PLANNING, percentage=101, overall_progress=25)
        
    with pytest.raises(ValidationError):
        WebSocketProgressUpdate(stage=WorkflowStage.PLANNING, percentage=40, overall_progress=101)

