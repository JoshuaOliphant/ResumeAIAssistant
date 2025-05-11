"""
Integration tests for the smart request handler.

These tests verify that the smart request handler correctly handles
different types of requests, prioritizes them, and provides accurate
monitoring information.
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.services.smart_request_handler import (
    smart_request, 
    TaskComplexity, 
    RequestPriority,
    RequestStatus,
    request_tracker
)

# Create test client
client = TestClient(app)

# Mock resume and job description IDs for testing
MOCK_RESUME_ID = "test-resume-id"
MOCK_JOB_ID = "test-job-id"

# Test data for ATS analysis
TEST_ATS_REQUEST = {
    "resume_id": MOCK_RESUME_ID,
    "job_description_id": MOCK_JOB_ID
}

# Test resume and job description content
TEST_RESUME_CONTENT = """
# John Doe
**Software Engineer**

## Summary
Experienced software engineer with a focus on backend development and AI.

## Experience
**Senior Developer, ABC Company**
- Developed scalable backend systems
- Implemented machine learning models

## Skills
Python, FastAPI, Machine Learning, SQL
"""

TEST_JOB_DESCRIPTION = """
# Software Engineer Position

## Requirements
- 3+ years of Python development
- Experience with FastAPI or similar frameworks
- Machine learning knowledge
- SQL database experience

## Responsibilities
- Design and implement backend systems
- Develop AI components for our platform
"""

# Patch database queries to return mock data
@pytest.fixture
def mock_db_queries():
    """Mock database queries to return test data."""
    with patch("app.api.endpoints.ats.db.query") as mock_query:
        # Mock Resume query
        mock_resume = AsyncMock()
        mock_resume.id = MOCK_RESUME_ID
        mock_resume.user_id = "test-user-id"
        
        # Mock ResumeVersion query
        mock_resume_version = AsyncMock()
        mock_resume_version.content = TEST_RESUME_CONTENT
        mock_resume_version.resume_id = MOCK_RESUME_ID
        
        # Mock JobDescription query
        mock_job = AsyncMock()
        mock_job.id = MOCK_JOB_ID
        mock_job.description = TEST_JOB_DESCRIPTION
        
        # Configure the mock query to return our mock objects
        mock_query_instance = mock_query.return_value
        mock_query_instance.filter.return_value = mock_query_instance
        mock_query_instance.first.side_effect = [mock_resume, mock_resume_version, mock_job]
        mock_query_instance.order_by.return_value = mock_query_instance
        
        yield

# Test basic ATS analysis with smart request handling
@pytest.mark.asyncio
async def test_ats_analysis_with_smart_request(mock_db_queries):
    """Test that ATS analysis endpoint works with smart request handling."""
    # Send test request
    response = client.post("/api/v1/ats/analyze", json=TEST_ATS_REQUEST)
    
    # Verify response
    assert response.status_code == 200
    result = response.json()
    
    # Check that the response contains expected fields
    assert "match_score" in result
    assert "matching_keywords" in result
    assert "missing_keywords" in result
    assert "improvements" in result
    
    # Verify request ID is included
    assert "request_id" in result
    request_id = result["request_id"]
    assert request_id is not None
    
    # Allow time for async stats to update
    await asyncio.sleep(0.1)
    
    # Test request statistics endpoint
    stats_response = client.get("/api/v1/stats/requests")
    assert stats_response.status_code == 200 or stats_response.status_code == 501  # 501 if not available
    
    # If smart request handling is available, check details
    if stats_response.status_code == 200:
        stats = stats_response.json()
        assert "total_requests" in stats
        assert stats["total_requests"] >= 1
        
        # Test specific request details
        request_details_response = client.get(f"/api/v1/stats/request/{request_id}")
        if request_details_response.status_code == 200:
            details = request_details_response.json()
            assert details["endpoint"] == "/api/v1/ats/analyze"
            assert details["status"] in [RequestStatus.COMPLETED.value, RequestStatus.PROCESSING.value]

# Test concurrent requests
@pytest.mark.asyncio
async def test_concurrent_requests(mock_db_queries):
    """Test that multiple concurrent requests are handled properly."""
    # Create multiple requests
    async def make_request():
        response = client.post("/api/v1/ats/analyze", json=TEST_ATS_REQUEST)
        return response.json()
    
    # Make 3 concurrent requests
    tasks = [make_request() for _ in range(3)]
    results = await asyncio.gather(*tasks)
    
    # Verify all requests succeeded
    for result in results:
        assert "match_score" in result
        assert "request_id" in result
    
    # Allow time for async stats to update
    await asyncio.sleep(0.1)
    
    # Check request statistics
    stats_response = client.get("/api/v1/stats/requests")
    if stats_response.status_code == 200:  # If smart request handling is available
        stats = stats_response.json()
        assert stats["total_requests"] >= 3

# Test health endpoint
def test_health_endpoint():
    """Test the health monitoring endpoint."""
    response = client.get("/api/v1/stats/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "system" in data
    assert "cpu_percent" in data["system"]
    assert "memory_percent" in data["system"]
    
    # Check if request stats are included
    if "requests" in data and isinstance(data["requests"], dict):
        # Smart request handling is active
        if "active" in data["requests"]:
            assert isinstance(data["requests"]["active"], int)

# Direct test of smart request decorator
@pytest.mark.asyncio
async def test_smart_request_decorator():
    """Test the smart request decorator functionality directly."""
    # Create a test function with the decorator
    @smart_request(complexity=TaskComplexity.SIMPLE, priority=RequestPriority.HIGH)
    async def test_function(param1, param2=None, request_id=None):
        return {
            "param1": param1,
            "param2": param2,
            "request_id": request_id
        }
    
    # Call the decorated function
    result = await test_function("test_value", param2="optional_value")
    
    # Verify result contains request_id
    assert "request_id" in result
    assert result["request_id"] is not None
    
    # Verify request was tracked
    request_id = result["request_id"]
    request_data = request_tracker.get_request(request_id)
    
    # If request tracking is enabled
    if request_data:
        assert request_data["complexity"] == TaskComplexity.SIMPLE
        assert request_data["priority"] == RequestPriority.HIGH
        assert request_data["status"] == RequestStatus.COMPLETED