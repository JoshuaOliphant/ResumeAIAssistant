import unittest
from app.services.thinking_budget import ThinkingBudget
from app.services.evidence_tracker import EvidenceTracker


class ThinkingBudgetTest(unittest.TestCase):
    def test_allocation_and_tracking(self):
        budget = ThinkingBudget(1000)
        self.assertEqual(sum(budget.allocations.values()), 1000)
        budget.record("evaluation", 100)
        self.assertEqual(budget.remaining("evaluation"), budget.allocations["evaluation"] - 100)


class EvidenceTrackerTest(unittest.TestCase):
    def test_verify_changes(self):
        original = "Worked at Acme Corp\nBuilt API"
        tracker = EvidenceTracker(original)
        updated = "Worked at Acme Corp\nBuilt API\nLed team"
        missing = tracker.verify(updated)
        self.assertIn("Led team", missing)
        self.assertNotIn("Worked at Acme Corp", missing)


if __name__ == '__main__':
    unittest.main()
