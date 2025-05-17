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
    original_warning = logfire.warning
    original_debug = logfire.debug
    
    # Patch all logfire methods to no-ops for tests
    def noop_log(*args, **kwargs):
        pass
    
    logfire.info = noop_log
    logfire.error = noop_log
    logfire.warning = noop_log
    logfire.debug = noop_log
    
    yield
    
    # Restore original methods after the test
    logfire.info = original_info
    logfire.error = original_error
    logfire.warning = original_warning
    logfire.debug = original_debug


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
        # Make these do nothing to avoid file system operations during tests
        mock_save.return_value = None
        mock_maybe_save.return_value = None
        yield