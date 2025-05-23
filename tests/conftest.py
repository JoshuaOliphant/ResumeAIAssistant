import pytest
from unittest.mock import patch
import logfire
import os
import warnings
from pydantic import PydanticDeprecatedSince20


# Add a fixture to mock logfire configuration
@pytest.fixture(autouse=True)
def configure_logfire():
    """Configure logfire to use a mock configuration for tests."""
    # Create a minimal configuration to suppress the warning
    logfire.configure(
        service_name="test-project",
        environment="test",
    )
    
    # Use a custom override to prevent any real logging during tests
    original_info = logfire.info
    original_error = logfire.error
    original_debug = logfire.debug
    original_span = logfire.span
    
    # Patch all logfire methods to no-ops for tests
    def noop_log(*args, **kwargs):
        pass
    
    logfire.info = noop_log
    logfire.error = noop_log
    logfire.debug = noop_log
    
    class DummySpan:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def noop_span(*args, **kwargs):
        return DummySpan()

    logfire.span = noop_span
    
    yield
    
    # Restore original methods after the test
    logfire.info = original_info
    logfire.error = original_error
    logfire.debug = original_debug
    logfire.span = original_span


# Add a fixture to suppress pydantic deprecation warnings
@pytest.fixture(autouse=True)
def ignore_pydantic_warnings():
    """Suppress Pydantic deprecation warnings during tests."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        yield


# Add a fixture to mock file operations in cost tracker
@pytest.fixture
def mock_file_operations():
    """Patch file operations for cost tracking."""
    with patch("app.services.model_optimizer._save_cost_report") as mock_save, \
         patch("app.services.model_optimizer._maybe_save_cost_report") as mock_maybe_save:
        mock_save.return_value = None
        mock_maybe_save.return_value = None
        yield


@pytest.fixture
def sample_resume() -> str:
    """Provide a small sample resume for tests."""
    return "EXPERIENCE\nWorked at Example Corp\nSKILLS\nPython, SQL"


@pytest.fixture
def sample_job_description() -> str:
    """Provide a simple job description for tests."""
    return "Looking for a Python engineer with SQL experience"


@pytest.fixture
def client():
    """Provide a TestClient with in-memory database."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.session import Base, get_db
    from app.api.endpoints import auth, jobs, resumes, export, requirements, websockets

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=f"{api_prefix}/auth")
    app.include_router(jobs.router, prefix=f"{api_prefix}/jobs")
    app.include_router(resumes.router, prefix=f"{api_prefix}/resumes")
    app.include_router(export.router, prefix=f"{api_prefix}/export")
    app.include_router(requirements.router, prefix=f"{api_prefix}/requirements")
    app.include_router(websockets.router, prefix=f"{api_prefix}/progress")

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
    app.dependency_overrides.clear()
