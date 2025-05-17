import os
import asyncio
import unittest
from unittest.mock import MagicMock, patch
import importlib

class PydanticAIServiceTest(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test', 'OPENAI_API_KEY': 'test'}):
            import app.services.pydanticai_service as svc
            importlib.reload(svc)
            self.svc_module = svc
            self.service = svc.PydanticAIService()

    def test_create_agent_sets_fallback(self):
        with patch('app.services.pydanticai_service.Agent') as MockAgent:
            agent_instance = MockAgent.return_value
            agent = self.service._create_agent('test-model', 'prompt', output_type=dict)
            MockAgent.assert_called_once_with(
                'test-model',
                system_prompt='prompt',
                output_type=dict,
                temperature=self.service.temperature,
                max_tokens=self.service.max_tokens,
                thinking_config={'budget_tokens': self.service.thinking_budget, 'type': 'enabled'}
            )
            self.assertEqual(agent, agent_instance)
            self.assertEqual(agent.fallback_config, self.service.fallback_models)

    def test_run_with_retry_handles_modelretry(self):
        mock_agent = MagicMock(spec=self.svc_module.Agent)
        mock_agent.run.side_effect = [self.svc_module.ModelRetry('retry'), {'ok': True}]
        coro = self.service._run_with_retry(mock_agent, 'msg')
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        self.assertEqual(result, {'ok': True})
        self.assertEqual(mock_agent.run.call_count, 2)


if __name__ == '__main__':
    unittest.main()
