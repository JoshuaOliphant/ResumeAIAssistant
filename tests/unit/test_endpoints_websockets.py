from unittest.mock import Mock, patch


def test_get_task_status(client):
    dummy = Mock(task_id="abc", status="completed", progress=100,
                 message="done", result={"ok": True}, error=None)
    with patch("app.services.claude_code.progress_tracker.progress_tracker.get_task", return_value=dummy):
        resp = client.get("/api/v1/progress/abc/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "abc"
    assert data["status"] == "completed"
