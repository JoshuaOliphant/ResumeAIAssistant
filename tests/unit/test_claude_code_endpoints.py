from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import claude_code
from app.api.endpoints.claude_code import ClaudeCodeExecutionError, progress_tracker

test_app = FastAPI()
test_app.include_router(claude_code.router, prefix="/api/v1")
client = TestClient(test_app)


def _build_request(resume: str, job: str) -> dict:
    return {
        "resume_id": "1",
        "job_id": "1",
        "user_id": "u1",
        "resume_content": resume,
        "job_description": job,
    }


@patch("app.api.endpoints.claude_code.get_claude_code_executor")
@patch("app.api.endpoints.claude_code.read_file")
@patch("app.schemas.resume.CustomizeResumeRequest", create=True)
def test_customize_resume_success(mock_schema, mock_read_file, mock_get_executor, sample_resume, sample_job_description):
    mock_exec = MagicMock()
    mock_exec.customize_resume.return_value = None
    mock_get_executor.return_value = mock_exec
    mock_read_file.side_effect = ["customized", "summary"]

    resp = client.post("/api/v1/customize-resume", json=_build_request(sample_resume, sample_job_description))
    assert resp.status_code == 200
    data = resp.json()
    assert data["customized_resume"] == "customized"
    assert data["customization_summary"] == "summary"


@patch("app.api.endpoints.claude_code.get_claude_code_executor")
@patch("app.schemas.resume.CustomizeResumeRequest", create=True)
def test_customize_resume_timeout_error(mock_schema, mock_get_executor, sample_resume, sample_job_description):
    mock_exec = MagicMock()
    mock_exec.customize_resume.side_effect = ClaudeCodeExecutionError("timeout exceeded")
    mock_get_executor.return_value = mock_exec

    resp = client.post("/api/v1/customize-resume", json=_build_request(sample_resume, sample_job_description))
    assert resp.status_code == 408
    assert "timeout" in resp.json()["detail"].lower()


@patch("app.api.endpoints.claude_code.get_claude_code_executor")
def test_customize_resume_async(mock_get_executor, sample_resume, sample_job_description):
    mock_exec = MagicMock()
    mock_exec.start_async.return_value = {"task_id": "abc", "status": "processing"}
    mock_get_executor.return_value = mock_exec

    resp = client.post("/api/v1/customize-resume/async/", json=_build_request(sample_resume, sample_job_description))
    assert resp.status_code == 200
    assert resp.json() == {"task_id": "abc", "status": "processing"}


@patch("app.services.claude_code.log_streamer.get_log_streamer")
@patch.object(progress_tracker, "get_task")
def test_get_customize_status(mock_get_task, mock_get_log_streamer):
    task = SimpleNamespace(
        task_id="t1",
        status="completed",
        message="done",
        result={"r": 1},
        error=None,
        created_at=1.0,
        updated_at=2.0,
    )
    task.to_dict = lambda: {
        "task_id": task.task_id,
        "status": task.status,
        "message": task.message,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "progress": 100,
    }
    mock_get_task.return_value = task

    mock_streamer = MagicMock()
    mock_streamer.get_logs.return_value = ["log"]
    mock_get_log_streamer.return_value = mock_streamer

    resp = client.get("/api/v1/customize-resume/status/t1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "t1"
    assert data["status"] == "completed"
    assert data["result"] == {"r": 1}
    assert data["logs"] == ["log"]


@patch.object(progress_tracker, "get_task", return_value=None)
def test_get_customize_status_not_found(mock_get_task):
    resp = client.get("/api/v1/customize-resume/status/unknown")
    assert resp.status_code == 404
