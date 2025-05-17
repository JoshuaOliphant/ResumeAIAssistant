import asyncio
import importlib
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
class TestPydanticAIService:
    @pytest.fixture(autouse=True)
    async def setup(self, mock_file_operations):
        # Mock environment variables instead of using real ones
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "test", "OPENAI_API_KEY": "test", "GEMINI_API_KEY": "test"}
        ):
            # Use importlib.reload to ensure the mocked environment is used
            import app.services.pydanticai_service as svc
            importlib.reload(svc)
            
            # Also mock any external service calls in the module
            with patch.object(svc, 'Agent'):
                self.svc_module = svc
                self.service = svc.PydanticAIService()
        
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
        
        # Call the async function directly with await
        result = await self.service._run_with_retry(mock_agent, "msg")
        
        # Check the results
        assert result == {"ok": True}
        assert mock_agent.run.await_count == 2
