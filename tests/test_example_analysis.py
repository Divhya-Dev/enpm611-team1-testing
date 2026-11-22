"""White-box unit tests for example_analysis.py (Feature 0)
"""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import example_analysis  # noqa: E402
from example_analysis import ExampleAnalysis  # noqa: E402
from model import Issue  # noqa: E402


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def event(author, event_type="commented"):
    return {
        "event_type": event_type,
        "author": author,
        "event_date": "2024-01-01T00:00:00+00:00",
    }


def raw_issue(creator, events=None, number=1):
    return {
        "url": f"https://github.com/python-poetry/poetry/issues/{number}",
        "creator": creator,
        "labels": [],
        "state": "open",
        "assignees": [],
        "title": f"Issue {number}",
        "text": "",
        "number": number,
        "created_date": "2024-01-01T00:00:00+00:00",
        "updated_date": "2024-01-02T00:00:00+00:00",
        "timeline_url": "",
        "events": events or [],
    }


def model_issue(creator, events=None, number=1):
    return Issue(raw_issue(creator, events, number))


SAMPLE_RAW = [
    raw_issue("alice", [event("alice"), event("bob"),
                        event("alice", "labeled")], number=1),
    raw_issue("alice", [event("bob", "closed"), event("carol")], number=2),
    raw_issue("bob", [event("alice", "mentioned")], number=3),
]


class ExampleAnalysisTestCase(unittest.TestCase):
    """Mocks config, DataLoader and plt.show for every test."""

    user = None

    def setUp(self):
        self.get_parameter = mock.patch.object(
            example_analysis.config, "get_parameter", return_value=self.user
        ).start()
        self.loader_cls = mock.patch.object(
            example_analysis, "DataLoader"
        ).start()
        self.show = mock.patch.object(example_analysis.plt, "show").start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(plt.close, "all")
        self.set_issues([Issue(r) for r in SAMPLE_RAW])

    def set_issues(self, issues):
        self.loader_cls.return_value.get_issues.return_value = issues

    def run_analysis(self):
        """Run the analysis; return (printed_text, chart_axes)."""
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ExampleAnalysis().run()
        return buffer.getvalue(), plt.gca()

    @staticmethod
    def bars(ax):
        names = [t.get_text() for t in ax.get_xticklabels()]
        heights = [int(p.get_height()) for p in ax.patches]
        return list(zip(names, heights))


# --------------------------------------------------------------------------
# __init__
# --------------------------------------------------------------------------
class TestInit(ExampleAnalysisTestCase):

    def test_user_defaults_to_none(self):
        analysis = ExampleAnalysis()
        self.get_parameter.assert_called_once_with("user")
        self.assertIsNone(analysis.USER)

    def test_user_is_read_from_config(self):
        self.get_parameter.return_value = "alice"
        self.assertEqual(ExampleAnalysis().USER, "alice")

    def test_constructor_does_not_load_data(self):
        ExampleAnalysis()
        self.loader_cls.assert_not_called()


# --------------------------------------------------------------------------
# run(): event counting without a user filter
# --------------------------------------------------------------------------
class TestEventCountAllUsers(ExampleAnalysisTestCase):

    def test_issues_come_from_data_loader(self):
        self.run_analysis()
        self.loader_cls.assert_called_once_with()
        self.loader_cls.return_value.get_issues.assert_called_once_with()

    def test_counts_every_event_of_every_type(self):
        out, _ = self.run_analysis()
        self.assertIn("Found 6 events across 3 issues.", out)

    def test_message_has_no_user_suffix(self):
        out, _ = self.run_analysis()
        self.assertNotIn(" for ", out)

    def test_message_is_padded_with_blank_lines(self):
        out, _ = self.run_analysis()
        self.assertTrue(out.startswith("\n\nFound 6 events"))
        self.assertIn("issues.\n\n\n", out)

    def test_issues_without_events(self):
        self.set_issues([model_issue("alice", number=1),
                         model_issue("bob", number=2)])
        out, _ = self.run_analysis()
        self.assertIn("Found 0 events across 2 issues.", out)


# --------------------------------------------------------------------------
# run(): event counting with a user filter
# --------------------------------------------------------------------------
class TestEventCountForUser(ExampleAnalysisTestCase):

    user = "alice"

    def test_counts_only_that_users_events(self):
        out, _ = self.run_analysis()
        # alice: commented + labeled (issue 1) + mentioned (issue 3)
        self.assertIn("Found 3 events across 3 issues for alice.", out)

    def test_other_user(self):
        self.get_parameter.return_value = "bob"
        out, _ = self.run_analysis()
        self.assertIn("Found 2 events across 3 issues for bob.", out)

    def test_unknown_user_has_zero_events(self):
        self.get_parameter.return_value = "nobody"
        out, _ = self.run_analysis()
        self.assertIn("Found 0 events across 3 issues for nobody.", out)

    def test_match_is_case_sensitive(self):
        self.get_parameter.return_value = "Alice"
        out, _ = self.run_analysis()
        self.assertIn("Found 0 events across 3 issues for Alice.", out)

    def test_user_filter_does_not_affect_issue_total_or_chart(self):
        out, ax = self.run_analysis()
        self.assertIn("across 3 issues", out)
        self.assertEqual(self.bars(ax), [("alice", 2), ("bob", 1)])


# --------------------------------------------------------------------------
# run(): bar chart of top issue creators
# --------------------------------------------------------------------------
class TestCreatorChart(ExampleAnalysisTestCase):

    def test_chart_is_shown(self):
        self.run_analysis()
        self.show.assert_called_once_with()

    def test_title_and_axis_labels(self):
        _, ax = self.run_analysis()
        self.assertEqual(ax.get_title(), "Top 50 issue creators")
        self.assertEqual(ax.get_xlabel(), "Creator Names")
        self.assertEqual(ax.get_ylabel(), "# of issues created")

    def test_figure_size(self):
        _, ax = self.run_analysis()
        self.assertEqual(tuple(ax.figure.get_size_inches()), (14.0, 8.0))

    def test_bars_count_issues_per_creator_sorted_descending(self):
        self.set_issues([
            model_issue("carol", number=1),
            model_issue("alice", number=2),
            model_issue("alice", number=3),
            model_issue("bob", number=4),
            model_issue("alice", number=5),
            model_issue("bob", number=6),
        ])
        _, ax = self.run_analysis()
        self.assertEqual(self.bars(ax),
                         [("alice", 3), ("bob", 2), ("carol", 1)])

    def test_chart_counts_issues_not_events(self):
        self.set_issues([model_issue("alice", [event("carol")] * 5)])
        _, ax = self.run_analysis()
        self.assertEqual(self.bars(ax), [("alice", 1)])

    def test_only_top_50_creators_are_plotted(self):
        issues, number = [], 0
        for i in range(60):
            for _ in range(60 - i):
                number += 1
                issues.append(model_issue(f"creator{i:02d}", number=number))
        self.set_issues(issues)

        _, ax = self.run_analysis()
        bars = self.bars(ax)
        self.assertEqual(len(bars), 50)
        self.assertEqual(bars[0], ("creator00", 60))
        self.assertEqual(bars[-1], ("creator49", 11))
        self.assertNotIn("creator50", [name for name, _ in bars])

    def test_issues_without_creator_are_not_plotted(self):
        self.set_issues([model_issue("alice", number=1),
                         model_issue(None, number=2)])
        out, ax = self.run_analysis()
        self.assertIn("across 2 issues", out)
        self.assertEqual(self.bars(ax), [("alice", 1)])

    def test_empty_dataset_raises_key_error(self):
        # Current behaviour: with no issues the DataFrame has no "creator" column, so building the chart fails after the summary is printed.
        self.set_issues([])
        buffer = io.StringIO()
        with redirect_stdout(buffer), self.assertRaises(KeyError):
            ExampleAnalysis().run()
        self.assertIn("Found 0 events across 0 issues.", buffer.getvalue())
        self.show.assert_not_called()


# --------------------------------------------------------------------------
# Mocked JSON file
# --------------------------------------------------------------------------
class TestWithMockedPoetryFile(unittest.TestCase):
    """Uses the real DataLoader with open() mocked, so no file is read."""

    def setUp(self):
        import data_loader

        mock.patch.object(data_loader, "_ISSUES", None).start()
        mock.patch.object(
            example_analysis.config, "get_parameter",
            side_effect=lambda name, default=None: {
                "ENPM611_PROJECT_DATA_PATH": "mock_poetry_issues.json",
                "user": "alice",
            }.get(name, default),
        ).start()
        self.mocked_open = mock.patch(
            "data_loader.open",
            mock.mock_open(read_data=json.dumps(SAMPLE_RAW)),
            create=True,
        ).start()
        self.show = mock.patch.object(example_analysis.plt, "show").start()
        self.addCleanup(mock.patch.stopall)
        self.addCleanup(plt.close, "all")

    def test_full_run(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ExampleAnalysis().run()
        out = buffer.getvalue()

        self.mocked_open.assert_called_once_with("mock_poetry_issues.json", "r")
        self.assertIn("Loaded 3 issues from mock_poetry_issues.json.", out)
        self.assertIn("Found 3 events across 3 issues for alice.", out)
        ax = plt.gca()
        self.assertEqual(
            [(t.get_text(), int(p.get_height()))
             for t, p in zip(ax.get_xticklabels(), ax.patches)],
            [("alice", 2), ("bob", 1)],
        )
        self.show.assert_called_once_with()


# --------------------------------------------------------------------------
# Running the module directly (python example_analysis.py)
# --------------------------------------------------------------------------
class TestMainBlock(unittest.TestCase):

    def test_running_module_as_script_runs_analysis(self):
        import runpy

        issues = [Issue(r) for r in SAMPLE_RAW]
        with mock.patch("data_loader.DataLoader") as loader_cls, \
                mock.patch("config.get_parameter", return_value=None), \
                mock.patch("matplotlib.pyplot.show") as show:
            loader_cls.return_value.get_issues.return_value = issues
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                runpy.run_path(example_analysis.__file__, run_name="__main__")
        self.addCleanup(plt.close, "all")

        self.assertIn("Found 6 events across 3 issues.", buffer.getvalue())
        show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
