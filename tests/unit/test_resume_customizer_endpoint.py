from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch

from app.api.endpoints import resume_customizer

app = FastAPI()
app.include_router(resume_customizer.router, prefix="/api/v1/resume-customizer")


def test_customize_resume_endpoint_starts_background_task():
    client = TestClient(app)
    with patch("app.api.endpoints.resume_customizer.ResumeCustomizer") as MockCust, \
         patch("app.api.endpoints.resume_customizer.run_customization_process", new=AsyncMock()) as mock_run:
        mock_instance = MockCust.return_value
        mock_instance.set_progress_callback.return_value = None
        response = client.post(
            "/api/v1/resume-customizer/customize/resume",
            params={
                "resume_content": "RES",
                "job_description": "JOB",
                "template_id": "tmpl",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "customization_id" in data
        mock_run.assert_awaited()
