"""
Tests for WebSocket progress tracking implementation.

This module contains tests for real-time progress tracking functionality,
including WebSocket connections, progress updates, and authentication.
"""

import asyncio
import json
import pytest
import websockets
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import WebSocket
from starlette.testclient import TestClient
from fastapi.testclient import TestClient as FastAPITestClient

from app.api.endpoints.progress import (
    ProgressUpdate, 
    ProgressStageModel, 
    ProgressConnectionManager,
    router
)
from app.services.parallel_processor import (
    ProgressTracker,
    ParallelTaskScheduler,
    ParallelProcessor
)

@pytest.fixture
def progress_connection_manager():
    """Fixture to create a fresh ProgressConnectionManager for each test."""
    return ProgressConnectionManager()

@pytest.fixture
def progress_update():
    """Fixture to create a sample progress update."""
    return ProgressUpdate(
        task_id="test-task-123",
        overall_progress=0.5,
        status="in_progress",
        current_stage="analysis",
        stages={
            "initialization": ProgressStageModel(
                name="initialization",
                description="Initializing task",
                progress=1.0,
                status="completed"
            ),
            "analysis": ProgressStageModel(
                name="analysis",
                description="Analyzing content",
                progress=0.5,
                status="in_progress"
            )
        },
        message="Processing content",
        estimated_time_remaining=30.0,
        started_at="2023-01-01T12:00:00",
        updated_at="2023-01-01T12:01:00"
    )


def test_progress_update_model():
    """Test the ProgressUpdate model validation"""
    # Test valid progress update
    update = ProgressUpdate(
        task_id="task-123",
        overall_progress=0.5,
        status="in_progress",
        current_stage="analysis"
    )
    assert update.overall_progress == 0.5
    assert update.status == "in_progress"
    
    # Test progress bounds
    update = ProgressUpdate(task_id="task-123", overall_progress=1.5)
    assert update.overall_progress == 1.0, "Progress should be capped at 1.0"
    
    update = ProgressUpdate(task_id="task-123", overall_progress=-0.5)
    assert update.overall_progress == 0.0, "Progress should have a minimum of 0.0"


def test_progress_stage_model():
    """Test the ProgressStageModel model validation"""
    # Test valid stage model
    stage = ProgressStageModel(
        name="test",
        description="Test stage",
        progress=0.5,
        status="in_progress"
    )
    assert stage.progress == 0.5
    assert stage.status == "in_progress"
    
    # Test progress bounds
    stage = ProgressStageModel(
        name="test",
        description="Test stage",
        progress=1.5,
        status="in_progress"
    )
    assert stage.progress == 1.0, "Progress should be capped at 1.0"


def test_connection_manager_basic_operations(progress_connection_manager):
    """Test basic operations of the ProgressConnectionManager"""
    manager = progress_connection_manager
    
    # Check initial state
    assert len(manager.active_connections) == 0
    assert len(manager.task_subscriptions) == 0
    assert len(manager.latest_updates) == 0
    

@pytest.mark.asyncio
async def test_connection_manager_subscribe_unsubscribe(progress_connection_manager):
    """Test subscribing and unsubscribing from tasks"""
    manager = progress_connection_manager
    
    # Subscribe to a task
    manager.subscribe("task-123", "user-456")
    assert "task-123" in manager.task_subscriptions
    assert "user-456" in manager.task_subscriptions["task-123"]
    
    # Subscribe another user to the same task
    manager.subscribe("task-123", "user-789")
    assert len(manager.task_subscriptions["task-123"]) == 2
    
    # Unsubscribe a user
    manager.unsubscribe("task-123", "user-456")
    assert "user-456" not in manager.task_subscriptions["task-123"]
    assert "user-789" in manager.task_subscriptions["task-123"]
    
    # Unsubscribe the last user
    manager.unsubscribe("task-123", "user-789")
    assert "task-123" not in manager.task_subscriptions


@pytest.mark.asyncio
async def test_connection_manager_connect_disconnect(progress_connection_manager):
    """Test connecting and disconnecting WebSockets"""
    manager = progress_connection_manager
    
    # Create mock WebSocket
    mock_websocket = AsyncMock(spec=WebSocket)
    
    # Connect the WebSocket
    await manager.connect(mock_websocket, "user-123")
    assert mock_websocket.accept.called
    assert "user-123" in manager.active_connections
    assert mock_websocket in manager.active_connections["user-123"]
    
    # Disconnect the WebSocket
    manager.disconnect(mock_websocket, "user-123")
    assert "user-123" not in manager.active_connections


@pytest.mark.asyncio
async def test_connection_manager_broadcast(progress_connection_manager, progress_update):
    """Test broadcasting messages to subscribed users"""
    manager = progress_connection_manager
    
    # Set up websockets and subscriptions
    mock_websocket1 = AsyncMock(spec=WebSocket)
    mock_websocket2 = AsyncMock(spec=WebSocket)
    
    await manager.connect(mock_websocket1, "user-1")
    await manager.connect(mock_websocket2, "user-2")
    
    manager.subscribe("test-task-123", "user-1")
    manager.subscribe("test-task-123", "user-2")
    
    # Broadcast a message
    message = progress_update.dict()
    await manager.broadcast("test-task-123", message)
    
    # Check that the message was sent to both WebSockets
    mock_websocket1.send_json.assert_called_once_with(message)
    mock_websocket2.send_json.assert_called_once_with(message)
    
    # Check that the latest update was stored
    assert "test-task-123" in manager.latest_updates
    assert manager.latest_updates["test-task-123"].task_id == "test-task-123"


@pytest.mark.asyncio
async def test_progress_tracker_initialization():
    """Test initialization of ProgressTracker"""
    tracker = ProgressTracker(task_id="test-123")
    
    # Check initial state
    assert tracker.task_id == "test-123"
    assert tracker.overall_progress == 0.0
    assert tracker.status == "initializing"
    assert len(tracker.stages) == 5  # Should have 5 default stages
    
    # Check stage weights
    assert sum(tracker.stage_weights.values()) == 1.0
    

@pytest.mark.asyncio
async def test_progress_tracker_update_stage():
    """Test updating a stage in the ProgressTracker"""
    # We need to patch the _send_update method to avoid actual HTTP requests
    with patch.object(ProgressTracker, '_send_update', AsyncMock()):
        tracker = ProgressTracker(task_id="test-123")
        
        # Update a stage
        tracker.update_stage(
            stage="analysis",
            progress=0.5,
            message="Processing content",
            status="in_progress"
        )
        
        # Check that the stage was updated
        assert tracker.stages["analysis"].progress == 0.5
        assert tracker.stages["analysis"].status == "in_progress"
        assert tracker.stages["analysis"].message == "Processing content"
        assert tracker.current_stage == "analysis"
        
        # Check that the overall progress was updated
        expected_progress = 0.5 * tracker.stage_weights["analysis"]
        assert abs(tracker.overall_progress - expected_progress) < 0.001
        
        # Verify _send_update was called
        assert tracker._send_update.called


@pytest.mark.asyncio
async def test_progress_tracker_complete_stage():
    """Test completing a stage in the ProgressTracker"""
    # We need to patch the _send_update method to avoid actual HTTP requests
    with patch.object(ProgressTracker, '_send_update', AsyncMock()):
        tracker = ProgressTracker(task_id="test-123")
        
        # Complete the initialization stage
        tracker.complete_stage(
            stage="initialization",
            message="Initialization complete"
        )
        
        # Check that the stage was completed
        assert tracker.stages["initialization"].progress == 1.0
        assert tracker.stages["initialization"].status == "completed"
        assert tracker.stages["initialization"].message == "Initialization complete"
        
        # Check that the next stage was started
        assert tracker.current_stage == "analysis"
        assert tracker.stages["analysis"].status == "in_progress"
        
        # Verify _send_update was called
        assert tracker._send_update.called


@pytest.mark.asyncio
async def test_progress_tracker_complete_all():
    """Test completing all stages in the ProgressTracker"""
    # We need to patch the _send_update method to avoid actual HTTP requests
    with patch.object(ProgressTracker, '_send_update', AsyncMock()):
        tracker = ProgressTracker(task_id="test-123")
        
        # Complete all stages
        tracker.complete_all(message="All stages complete")
        
        # Check that all stages are completed
        for stage_name, stage in tracker.stages.items():
            assert stage.progress == 1.0
            assert stage.status == "completed"
        
        # Check that the overall progress is 1.0
        assert tracker.overall_progress == 1.0
        assert tracker.status == "completed"
        assert tracker.message == "All stages complete"
        
        # Verify _send_update was called
        assert tracker._send_update.called


@pytest.mark.asyncio
async def test_progress_tracker_set_error():
    """Test setting an error in the ProgressTracker"""
    # We need to patch the _send_update method to avoid actual HTTP requests
    with patch.object(ProgressTracker, '_send_update', AsyncMock()):
        tracker = ProgressTracker(task_id="test-123")
        tracker.current_stage = "analysis"
        
        # Set an error
        tracker.set_error(message="An error occurred", stage="analysis")
        
        # Check that the stage has an error
        assert tracker.stages["analysis"].status == "error"
        assert tracker.stages["analysis"].message == "An error occurred"
        
        # Check that the overall status is error
        assert tracker.status == "error"
        assert tracker.message == "An error occurred"
        
        # Verify _send_update was called
        assert tracker._send_update.called


@pytest.mark.asyncio
async def test_progress_tracker_send_update():
    """Test sending updates via HTTP in the ProgressTracker"""
    # Mock httpx.AsyncClient
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value.status_code = 200
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        tracker = ProgressTracker(task_id="test-123")
        
        # Call _send_update
        await tracker._send_update()
        
        # Verify the HTTP request was made with the right data
        assert mock_client.post.called
        args, kwargs = mock_client.post.call_args
        assert args[0].endswith('/progress/update')
        
        # Check that the request body contains the expected data
        request_data = kwargs['json']
        assert request_data['task_id'] == "test-123"
        assert request_data['status'] == "initializing"


@pytest.mark.asyncio
async def test_parallel_task_scheduler_with_progress_tracking():
    """Test integration of ProgressTracker with ParallelTaskScheduler"""
    # Mock the ProgressTracker
    mock_tracker = MagicMock(spec=ProgressTracker)
    mock_tracker.update_stage = MagicMock()
    
    # Create scheduler with progress tracking
    scheduler = ParallelTaskScheduler(progress_tracker=mock_tracker)
    
    # Create a mock task function
    mock_task_func = AsyncMock(return_value="task result")
    
    # Add a task
    from app.services.parallel_processor import ParallelTask, TaskPriority, SectionType
    task = ParallelTask(
        name="test_task",
        section_type=SectionType.EXPERIENCE,
        priority=TaskPriority.HIGH,
        func=mock_task_func,
        args=[],
        kwargs={}
    )
    
    task_id = scheduler.add_task(task)
    
    # Mock asyncio.create_task to run the coroutines synchronously
    with patch('asyncio.create_task', AsyncMock()):
        results = await scheduler.execute_all()
    
    # Verify progress tracking was called
    assert mock_tracker.update_stage.called
    
    # For more detailed verification, you can check specific calls and arguments
    call_args_list = mock_tracker.update_stage.call_args_list
    assert len(call_args_list) > 0
    
    # Check the final result
    assert task_id in results
    assert results[task_id] == "task result"


@pytest.mark.asyncio
async def test_parallel_processor_with_progress_tracking():
    """Test integration of ProgressTracker with ParallelProcessor"""
    # Create a ParallelProcessor
    processor = ParallelProcessor()
    
    # Initialize progress tracking
    task_id = processor.initialize_progress_tracking()
    
    # Ensure a ProgressTracker was created
    assert processor.progress_tracker is not None
    assert processor.progress_tracker.task_id == task_id
    
    # Ensure the scheduler was updated with the tracker
    assert processor.scheduler.progress_tracker == processor.progress_tracker


@pytest.mark.asyncio
async def test_create_progress_tracker_api(monkeypatch):
    """Test the create progress tracker API endpoint"""
    # Create a test client
    client = FastAPITestClient(router)
    
    # Mock authentication
    async def mock_get_current_user(token, db):
        return MagicMock(id="test-user-123")
    
    monkeypatch.setattr(
        "app.api.endpoints.progress.get_current_user", 
        mock_get_current_user
    )
    
    # Make a request to create a progress tracker
    response = client.post("/create")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "initializing"


@pytest.mark.asyncio
async def test_update_progress_api(monkeypatch, progress_update):
    """Test the update progress API endpoint"""
    # Create a test client
    client = FastAPITestClient(router)
    
    # Mock authentication and connection manager
    async def mock_get_current_user(token, db):
        return MagicMock(id="test-user-123")
    
    monkeypatch.setattr(
        "app.api.endpoints.progress.get_current_user", 
        mock_get_current_user
    )
    
    # Mock the broadcast method
    async def mock_broadcast(task_id, data):
        return
    
    monkeypatch.setattr(
        "app.api.endpoints.progress.connection_manager.broadcast", 
        mock_broadcast
    )
    
    # Make a request to update progress
    response = client.post(
        "/update",
        json=progress_update.dict()
    )
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == progress_update.task_id
    assert data["overall_progress"] == progress_update.overall_progress


@pytest.mark.asyncio
async def test_get_progress_status_api(monkeypatch, progress_update):
    """Test the get progress status API endpoint"""
    # Create a test client
    client = FastAPITestClient(router)
    
    # Mock authentication
    async def mock_get_current_user(token, db):
        return MagicMock(id="test-user-123")
    
    monkeypatch.setattr(
        "app.api.endpoints.progress.get_current_user", 
        mock_get_current_user
    )
    
    # Add a progress update to the connection manager
    connection_manager = ProgressConnectionManager()
    connection_manager.latest_updates[progress_update.task_id] = progress_update
    
    monkeypatch.setattr(
        "app.api.endpoints.progress.connection_manager", 
        connection_manager
    )
    
    # Make a request to get progress status
    response = client.get(f"/status/{progress_update.task_id}")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == progress_update.task_id
    assert data["overall_progress"] == progress_update.overall_progress