from datetime import datetime

from app.services.evaluation_service import EvaluationService
from evaluation.pipeline import PipelineResult, PipelineMode


def _dummy_result(idx: int) -> PipelineResult:
    return PipelineResult(
        pipeline_id=f"id{idx}",
        test_case_id=f"case{idx}",
        mode=PipelineMode.COMPREHENSIVE,
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=0.1,
    )


def test_history_respects_max_size():
    service = EvaluationService(max_history_size=5)
    for i in range(7):
        service._record_evaluation_history(f"id{i}", _dummy_result(i))
    assert len(service.evaluation_history) == 5
    assert [e["evaluation_id"] for e in service.evaluation_history] == [f"id{i}" for i in range(2,7)]


def test_history_size_from_env(monkeypatch):
    monkeypatch.setenv("EVALUATION_HISTORY_SIZE", "3")
    service = EvaluationService()
    for i in range(5):
        service._record_evaluation_history(f"id{i}", _dummy_result(i))
    assert len(service.evaluation_history) == 3
