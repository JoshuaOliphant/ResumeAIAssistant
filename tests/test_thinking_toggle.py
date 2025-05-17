"""
Test the thinking toggle functionality.

This test verifies that the thinking budget configuration is properly
toggled based on the PYDANTICAI_ENABLE_THINKING setting.
"""

import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.model_selector import get_model_config_for_task
from app.services.thinking_budget import TaskComplexity, calculate_thinking_budget


class ThinkingToggleTest(unittest.TestCase):
    """Test cases for the thinking toggle functionality."""

    def test_thinking_budget_respects_toggle(self):
        """Test that calculate_thinking_budget respects the thinking toggle."""
        # Test with thinking enabled (default)
        with patch.object(settings, "PYDANTICAI_ENABLE_THINKING", True):
            budget, config = calculate_thinking_budget(
                task_complexity=TaskComplexity.COMPLEX,
                model_provider="google",
                max_budget=10000,
            )
            # When enabled, we should get a non-zero budget for COMPLEX tasks
            self.assertGreater(budget, 0)
            self.assertTrue(config)  # Config should be non-empty

        # Test with thinking disabled
        with patch.object(settings, "PYDANTICAI_ENABLE_THINKING", False):
            budget, config = calculate_thinking_budget(
                task_complexity=TaskComplexity.COMPLEX,
                model_provider="google",
                max_budget=10000,
            )
            # When disabled, we should get 0 budget
            self.assertEqual(budget, 0)
            self.assertEqual(config, {})  # Config should be empty

    @patch("app.services.model_selector.get_available_models")
    def test_model_selector_respects_toggle(self, mock_get_available_models):
        """Test that model selector respects the thinking toggle."""
        # Mock the available models
        mock_get_available_models.return_value = {
            "google:gemini-2.5-pro-preview-03-25": {
                "provider": "google",
                "tier": "premium",
                "capabilities": ["thinking", "structured_output"],
                "supports_thinking": True,
                "cost_per_1k_input": 0.000125,
                "cost_per_1k_output": 0.00375,
                "max_tokens": 1048576,
            }
        }

        # Test with thinking enabled
        with (
            patch.object(settings, "PYDANTICAI_ENABLE_THINKING", True),
            patch("app.services.model_selector.select_model_for_task") as mock_select,
            patch("app.services.model_selector.get_fallback_chain") as mock_fallback,
            patch(
                "app.services.model_selector.get_thinking_config_for_task"
            ) as mock_thinking,
        ):
            # Configure mocks
            mock_select.return_value = (
                "google:gemini-2.5-pro-preview-03-25",
                {
                    "provider": "google",
                    "tier": "premium",
                    "capabilities": ["thinking", "structured_output"],
                    "supports_thinking": True,
                },
            )
            mock_fallback.return_value = []
            mock_thinking.return_value = {"thinkingBudget": 5000}

            # Call the function
            config = get_model_config_for_task("resume_evaluation")

            # Verify thinking was included
            self.assertIn("thinking_config", config)
            self.assertTrue(
                mock_thinking.call_count >= 1,
                f"Expected get_thinking_config_for_task to be called at least once, but was called {mock_thinking.call_count} times",
            )

        # Test with thinking disabled
        with (
            patch.object(settings, "PYDANTICAI_ENABLE_THINKING", False),
            patch("app.services.model_selector.select_model_for_task") as mock_select,
            patch("app.services.model_selector.get_fallback_chain") as mock_fallback,
            patch(
                "app.services.model_selector.get_thinking_config_for_task"
            ) as mock_thinking,
        ):
            # Configure mocks
            mock_select.return_value = (
                "google:gemini-2.5-pro-preview-03-25",
                {
                    "provider": "google",
                    "tier": "premium",
                    "capabilities": ["thinking", "structured_output"],
                    "supports_thinking": True,
                },
            )
            mock_fallback.return_value = []

            # Call the function
            config = get_model_config_for_task("resume_evaluation")

            # Verify thinking was not included
            self.assertNotIn("thinking_config", config)
            self.assertEqual(
                mock_thinking.call_count,
                0,
                f"Expected get_thinking_config_for_task not to be called, but was called {mock_thinking.call_count} times",
            )


if __name__ == "__main__":
    unittest.main()
