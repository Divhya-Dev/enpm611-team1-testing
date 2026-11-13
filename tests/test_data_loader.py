"""Tests for loading the issue/event fields consumed by Label Resolution."""
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import data_loader
from model import Issue, State


class TestLabelResolutionDataLoader(unittest.TestCase):
    def setUp(self):
        self.original_issues = data_loader._ISSUES
        data_loader._ISSUES = None

    def tearDown(self):
        data_loader._ISSUES = self.original_issues

    def write_dataset(self, records):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(records, handle)
        handle.close()
        self.addCleanup(lambda: os.path.exists(handle.name) and os.unlink(handle.name))
        return handle.name

    def label_resolution_records(self):
        return [
            {
                "number": 101,
                "state": "closed",
                "created_date": "2026-01-01T00:00:00Z",
                "labels": ["bug", "backend"],
                "events": [
                    {"event_type": "closed", "event_date": "2026-01-06T00:00:00Z"}
                ],
            },
            {
                "number": 102,
                "state": "open",
                "created_date": "2026-01-02T00:00:00Z",
                "labels": ["bug"],
                "events": [],
            },
        ]

    def test_loader_reads_dataset_path_setting_used_by_analysis(self):
        with patch("data_loader.config.get_parameter", return_value="issues.json") as get_parameter:
            loader = data_loader.DataLoader()
        get_parameter.assert_called_once_with("ENPM611_PROJECT_DATA_PATH")
        self.assertEqual(loader.data_path, "issues.json")

    def test_load_creates_issue_objects_with_resolution_fields(self):
        path = self.write_dataset(self.label_resolution_records())
        loader = data_loader.DataLoader()
        loader.data_path = path

        issues = loader._load()

        self.assertEqual(len(issues), 2)
        self.assertTrue(all(isinstance(issue, Issue) for issue in issues))
        closed_issue = issues[0]
        self.assertEqual(closed_issue.number, 101)
        self.assertEqual(closed_issue.state, State.closed)
        self.assertEqual(closed_issue.labels, ["bug", "backend"])
        self.assertEqual(closed_issue.created_date, datetime.fromisoformat("2026-01-01T00:00:00+00:00"))
        self.assertEqual(len(closed_issue.events), 1)
        self.assertEqual(closed_issue.events[0].event_type, "closed")
        self.assertEqual(closed_issue.events[0].event_date, datetime.fromisoformat("2026-01-06T00:00:00+00:00"))

    def test_get_issues_caches_dataset_for_analysis(self):
        loader = data_loader.DataLoader()
        expected = [Issue(self.label_resolution_records()[0])]
        with patch.object(loader, "_load", return_value=expected) as load:
            first_result = loader.get_issues()
            second_result = loader.get_issues()

        self.assertIs(first_result, expected)
        self.assertIs(second_result, expected)
        load.assert_called_once_with()

    def test_load_raises_file_not_found_for_missing_dataset(self):
        loader = data_loader.DataLoader()
        loader.data_path = "/no/such/label-resolution-dataset.json"
        with self.assertRaises(FileNotFoundError):
            loader._load()


if __name__ == "__main__":
    unittest.main()
