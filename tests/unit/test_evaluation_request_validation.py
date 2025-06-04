import pytest
from pydantic import ValidationError

from app.services.evaluation_service import EvaluationRequest
from evaluation.pipeline import PipelineMode


def test_evaluation_request_validates_length():
    too_long = "a" * 10001
    with pytest.raises(ValidationError):
        EvaluationRequest(
            resume_content=too_long,
            job_description="job",
            mode=PipelineMode.COMPREHENSIVE,
        )
