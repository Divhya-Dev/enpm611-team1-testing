
import unittest
from datetime import datetime, timezone

from label_resolution_analysis import analyze


class TestLabelResolutionAnalysis(unittest.TestCase):

    def setUp(self):
        # Sample GitHub issues for testing
        self.issues = [
            {
                "number": 1,
                "state": "closed",
                "created_at": "2026-01-01T00:00:00Z",
                "closed_at": "2026-01-06T00:00:00Z",
                "labels": [{"name": "bug"}],
            },
            {
                "number": 2,
                "state": "closed",
                "created_at": "2026-01-01T00:00:00Z",
                "closed_at": "2026-01-11T00:00:00Z",
                "labels": [{"name": "bug"}],
            },
            {
                "number": 3,
                "state": "open",
                "created_at": "2026-01-01T00:00:00Z",
                "closed_at": None,
                "labels": [{"name": "bug"}],
            },
        ]

    def test_closed_issues_count(self):
        result = analyze(self.issues, selected_label="bug")
        self.assertEqual(result["selected"]["count"], 2)

    def test_average_resolution_time(self):
        result = analyze(self.issues, selected_label="bug")
        self.assertAlmostEqual(result["selected"]["mean_days"], 7.5)

    def test_median_resolution_time(self):
        result = analyze(self.issues, selected_label="bug")
        self.assertAlmostEqual(result["selected"]["median_days"], 7.5)

    def test_open_issues_excluded(self):
        result = analyze(self.issues, selected_label="bug")
        self.assertEqual(result["selected"]["count"], 2)

    def test_unknown_label(self):
        result = analyze(self.issues, selected_label="nonexistent")
        self.assertIsNone(result["selected"])


if __name__ == "__main__":
    unittest.main()
