"""Label Resolution Analysis Feature 1 - White Box Testing"""
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import label_resolution_analysis as lra
from model import Issue


def _issue(number, created, closed=None, labels=None, events=None, **extra):
    """helper to build a mock issue dictionary with creation, closure, and labels."""
    record = {
        "number": number,
        "state": "closed" if closed else "open",
        "created_date": created,
        "closed_date": closed,
        "labels": labels or [],
        "events": events or []
    }
    record.update(extra)
    return record


class TestAnalyze(unittest.TestCase):

    def test_empty_input(self):
        """analyze handles empty issue lists gracefully."""
        result = lra.analyze([])
        self.assertEqual(result["rows"], [])
        self.assertIsNone(result["selected"])

    def test_single_label_resolution_metrics(self):
        """verify correct aggregation of median and mean resolution days for a specific label."""
        issues = [
            _issue(1, "2024-04-10T00:00:00Z", closed="2024-04-12T00:00:00Z", labels=["bug"]),
            _issue(2, "2024-04-10T00:00:00Z", closed="2024-04-14T00:00:00Z", labels=["bug"]),
        ]
        result = lra.analyze(issues)
        bug_rows = [r for r in result["rows"] if str(r.get("label", "")).lower() == "bug"]
        self.assertTrue(len(bug_rows) > 0)
        self.assertEqual(bug_rows[0]["count"], 2)
        self.assertEqual(bug_rows[0]["median_days"], 2.0)
        self.assertEqual(bug_rows[0]["mean_days"], 2.0)

    def test_issue_with_multiple_labels_contributes_to_each(self):
        """an issue with multiple labels should count toward the metrics of each individual label."""
        issues = [
            _issue(1, "2024-04-10T00:00:00Z", closed="2024-04-12T00:00:00Z", labels=["bug", "priority"]),
        ]
        result = lra.analyze(issues)
        labels_found = {str(r.get("label", "")).lower(): r["median_days"] for r in result["rows"]}
        self.assertIn("bug", labels_found)
        self.assertIn("priority", labels_found)
        self.assertEqual(labels_found["bug"], 2.0)
        self.assertEqual(labels_found["priority"], 2.0)

    def test_selected_label_filter(self):
        """filtering by a specific label restricts analysis output correctly."""
        issues = [
            _issue(1, "2024-04-10T00:00:00Z", closed="2024-04-12T00:00:00Z", labels=["bug"]),
            _issue(2, "2024-04-10T00:00:00Z", closed="2024-04-13T00:00:00Z", labels=["docs"]),
        ]
        result = lra.analyze(issues, selected_label="bug")
        self.assertIsNotNone(result["selected"])
        self.assertEqual(str(result["selected"]["label"]).lower(), "bug")
        self.assertEqual(result["selected"]["median_days"], 2.0)

    def test_works_with_issue_model_objects(self):
        """ensure the analyzer correctly processes native Issue model instances."""
        issue = Issue({
            "number": 1,
            "state": "closed",
            "created_date": "2024-04-10T00:00:00Z",
            "closed_date": "2024-04-14T00:00:00Z",
            "labels": ["enhancement"],
            "events": []
        })
        result = lra.analyze([issue])
        self.assertTrue(len(result["rows"]) > 0)
        self.assertEqual(result["rows"][0]["mean_days"], 4.0)


class TestRun(unittest.TestCase):

    def _run(self, issues, **kwargs):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = lra.run(issues, **kwargs)
        return result, buffer.getvalue()

    def test_prints_question_method_and_finding(self):
        """run output prints proper metrics summary when valid data is present."""
        _, printed = self._run([_issue(1, "2024-04-10T00:00:00Z", closed="2024-04-12T00:00:00Z", labels=["bug"])], show_chart=False)
        self.assertIn("Resolution time by label", printed)
        self.assertIn("bug", printed.lower())

    def test_label_with_no_matches_prints_notice(self):
        """run output notifies when a filtered label has no matching data."""
        _, printed = self._run([], label="nonexistent", show_chart=False)
        self.assertIn("No closed issues with valid creation and closing dates were found.", printed)

    def test_chart_is_saved_in_images_directory(self):
        """ensure analysis generates and saves visual charts safely into the images folder."""
        issues = [_issue(n, f"2024-04-0{n}T00:00:00Z", closed=f"2024-04-0{n+2}T00:00:00Z", labels=["bug"]) for n in range(1, 4)]
        with tempfile.TemporaryDirectory() as tmp, mock.patch("matplotlib.pyplot.show") as show:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self._run(issues, show_chart=True)
                self.assertTrue(os.path.isfile(os.path.join("images", "label_resolution_chart.png")))
            finally:
                os.chdir(old)
        show.assert_called_once()

    def test_chart_skipped_when_empty(self):
        """chart generation is bypassed safely if there is no data to plot."""
        with mock.patch("matplotlib.pyplot.subplots") as mock_subplots:
            lra.run([], show_chart=True)
        mock_subplots.assert_not_called()


if __name__ == "__main__":
    unittest.main()
