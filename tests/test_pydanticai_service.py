import asyncio
import importlib
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
class TestPydanticAIService:
    @pytest.fixture(autouse=True)
    async def setup(self, mock_file_operations):
        # Set up all the necessary mocks before importing the module
        self.patches = [
            patch('app.core.config.settings.ANTHROPIC_API_KEY', 'test'), 
            patch('app.core.config.settings.OPENAI_API_KEY', 'test'), 
            patch('app.core.config.settings.GEMINI_API_KEY', 'test'),
            patch('app.services.pydanticai_service.Agent'),
            patch('app.services.pydanticai_service.logfire')
        ]
        
        # Start all patches
        for p in self.patches:
            p.start()
        
        # Import the module after patching
        import app.services.pydanticai_service as svc
        importlib.reload(svc)
        
        # Set up the service
        self.svc_module = svc
        self.service = svc.PydanticAIService()
        
        yield
        
        # Clean up patches after test
        for p in self.patches:
            p.stop()
        
    async def test_run_with_retry_handles_modelretry(self):
        # Create a mock agent with side effects
        mock_agent = MagicMock(spec=self.svc_module.Agent)
        
        # Create an async mock for the run method
        mock_run = AsyncMock()
        mock_run.side_effect = [
            self.svc_module.ModelRetry("retry"),  
            {"ok": True}
        ]
        mock_agent.run = mock_run
        
        # Create a mock for logfire.warning
        mock_warning = MagicMock()
        
        # Patch the logfire module to prevent real logging
        with patch.object(self.svc_module.logfire, 'warning', mock_warning):
            # Call the async function directly with await
            result = await self.service._run_with_retry(mock_agent, "msg")
        
        # Check the results
        assert result == {"ok": True}
        assert mock_agent.run.await_count == 2
        
        # Verify that logfire.warning was called with the expected args
        assert mock_warning.call_count == 1
