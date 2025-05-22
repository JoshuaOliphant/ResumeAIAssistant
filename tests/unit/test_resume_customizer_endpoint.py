import pytest
from fastapi import BackgroundTasks
from unittest.mock import patch, MagicMock

from app.api.endpoints import resume_customizer as endpoint


@pytest.mark.asyncio
async def test_customize_resume_schedules_background_task():
    task = BackgroundTasks()
    fake_uuid = MagicMock()
    fake_uuid.hex = "abc123"
    with (
        patch("uuid.uuid4", return_value=fake_uuid),
        patch.object(endpoint, "run_customization_process") as mock_run,
    ):
        result = await endpoint.customize_resume(
            resume_content="RES",
            job_description="JOB",
            template_id="tpl",
            background_tasks=task,
        )
        assert result == {"customization_id": "abc123", "status": "pending"}
        assert task.tasks  # background task scheduled
        mock_run.assert_not_called()
