import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.schemas.progress import StageProgress, WebSocketProgressUpdate, calculate_overall_progress
from app.services.websocket_manager import WebSocketManager
from app.services.progress_tracker import ProgressTracker


def test_stage_progress_validation():
    stage = StageProgress(status="in_progress", progress=50)
    assert stage.progress == 50

    with pytest.raises(ValidationError):
        StageProgress(status="in_progress", progress=150)


def test_websocket_progress_update_clamp():
    update = WebSocketProgressUpdate(
        overall_progress=150,
        status="in_progress",
        task_statuses={},
        elapsed_seconds=0,
    )
    assert update.overall_progress == 100


def test_calculate_overall_progress():
    stages = {
        "evaluation": StageProgress(status="completed", progress=100),
        "planning": StageProgress(status="in_progress", progress=50),
    }
    weights = {"evaluation": 0.2, "planning": 0.8}
    expected = int((100 * 0.2 + 50 * 0.8) / (0.2 + 0.8))
    assert calculate_overall_progress(stages, weights) == expected


def test_websocket_manager_register_send_remove():
    manager = WebSocketManager()
    mock_ws = AsyncMock()
    asyncio.run(manager.register("abc", mock_ws))
    assert mock_ws in manager.active_connections["abc"]

    asyncio.run(manager.send_json("abc", {"msg": "hi"}))
    mock_ws.send_json.assert_awaited_with({"msg": "hi"})

    manager.remove("abc", mock_ws)
    assert "abc" not in manager.active_connections


def test_progress_tracker_flow():
    manager = WebSocketManager()
    manager.send_json = AsyncMock()
    tracker = ProgressTracker("abc", manager)

    asyncio.run(tracker.start())
    manager.send_json.assert_awaited()
    manager.send_json.reset_mock()

    asyncio.run(tracker.update_stage("evaluation", "in_progress", progress=50))
    assert tracker.overall_progress == 10
    manager.send_json.assert_awaited()

    asyncio.run(tracker.complete())
    assert tracker.status == "completed"
    assert tracker.overall_progress == 100
