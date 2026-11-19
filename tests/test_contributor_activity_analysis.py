"""White-box unit tests for contributor_activity_analysis.py (Feature 2)."""

import io
import json
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  

import contributor_activity_analysis as caa  
from contributor_activity_analysis import (  
    analyze_contributor_activity,
    create_chart,
    display_results,
    get_field,
    get_username,
    is_bot,
    run,
)
from model import Issue  


# --------------------------------------------------------------------------
# Helper code
# --------------------------------------------------------------------------
def comment(author, event_type="commented"):
    """Build a raw event dictionary in the dataset's JSON format."""
    return {
        "event_type": event_type,
        "author": author,
        "event_date": "2024-01-01T00:00:00+00:00",
    }


def raw_issue(creator, events=None, number=1):
    """Build a raw issue dictionary in the dataset's JSON format."""
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
    """Build a model.Issue object, exactly as DataLoader would."""
    return Issue(raw_issue(creator, events, number))


def quiet(func, *args, **kwargs):
    """Call func with stdout captured; return (result, printed_text)."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


# --------------------------------------------------------------------------
# get_field function
# --------------------------------------------------------------------------
class TestGetField(unittest.TestCase):

    def test_none_object_returns_default(self):
        self.assertEqual(get_field(None, "a", default="dflt"), "dflt")

    def test_none_object_without_default_returns_none(self):
        self.assertIsNone(get_field(None, "a"))

    def test_reads_key_from_dict(self):
        self.assertEqual(get_field({"a": 1}, "a"), 1)

    def test_reads_attribute_from_object(self):
        self.assertEqual(get_field(SimpleNamespace(a=2), "a"), 2)

    def test_first_non_none_name_wins_in_dict(self):
        obj = {"a": None, "b": "second", "c": "third"}
        self.assertEqual(get_field(obj, "a", "b", "c"), "second")

    def test_first_non_none_name_wins_in_object(self):
        obj = SimpleNamespace(b="second", c="third")  # no attribute "a"
        self.assertEqual(get_field(obj, "a", "b", "c"), "second")

    def test_all_names_missing_returns_default(self):
        self.assertEqual(get_field({"x": 1}, "a", "b", default=[]), [])

    def test_false_values_other_than_none_are_returned(self):
        # 0 and False are legitimate values and must not trigger fallback.
        self.assertEqual(get_field({"a": 0, "b": 5}, "a", "b"), 0)
        self.assertIs(get_field({"a": False, "b": True}, "a", "b"), False)


# --------------------------------------------------------------------------
# get_username function
# --------------------------------------------------------------------------
class TestGetUsername(unittest.TestCase):

    def test_none_returns_none(self):
        self.assertIsNone(get_username(None))

    def test_plain_string_is_returned(self):
        self.assertEqual(get_username("alice"), "alice")

    def test_string_is_stripped(self):
        self.assertEqual(get_username("  alice \n"), "alice")

    def test_blank_string_returns_none(self):
        self.assertIsNone(get_username(""))
        self.assertIsNone(get_username("   "))

    def test_dict_login_is_preferred(self):
        value = {"login": "alice", "username": "u", "name": "Alice A."}
        self.assertEqual(get_username(value), "alice")

    def test_dict_falls_back_to_username_then_name(self):
        self.assertEqual(get_username({"username": "bob"}), "bob")
        self.assertEqual(get_username({"name": " carol "}), "carol")

    def test_object_with_login_attribute(self):
        self.assertEqual(get_username(SimpleNamespace(login="dave")), "dave")

    def test_dict_without_known_keys_returns_none(self):
        self.assertIsNone(get_username({"id": 42}))

    def test_dict_with_blank_login_returns_none(self):
        self.assertIsNone(get_username({"login": ""}))

    def test_non_string_login_is_converted_to_string(self):
        self.assertEqual(get_username({"login": 1234}), "1234")

    def test_whitespace_only_login_returns_none(self):
        #Defect 1
        self.assertIsNone(get_username({"login": "   "}))
        self.assertIsNone(get_username(SimpleNamespace(login="\t")))


# --------------------------------------------------------------------------
# is_bot function
# --------------------------------------------------------------------------
class TestIsBot(unittest.TestCase):

    def test_empty_or_none_is_not_bot(self):
        self.assertFalse(is_bot(None))
        self.assertFalse(is_bot(""))

    def test_bracket_bot_suffix(self):
        self.assertTrue(is_bot("github-actions[bot]"))
        self.assertTrue(is_bot("stale[bot]"))

    def test_dash_bot_suffix(self):
        self.assertTrue(is_bot("facebook-github-bot"))

    def test_underscore_bot_suffix(self):
        self.assertTrue(is_bot("ci_bot"))

    def test_suffix_check_is_case_insensitive(self):
        self.assertTrue(is_bot("Dependabot[BOT]"))
        self.assertTrue(is_bot("Release-Bot"))

    def test_human_names_containing_bot_are_not_bots(self):
        for name in ("turbotimon", "Tobotimus", "cpbotha", "Gobot1234"):
            with self.subTest(name=name):
                self.assertFalse(is_bot(name))

    def test_regular_human_name(self):
        self.assertFalse(is_bot("dimbleby"))


# --------------------------------------------------------------------------
# analyze_contributor_activity function
# --------------------------------------------------------------------------
class TestAnalyzeContributorActivity(unittest.TestCase):

    def setUp(self):
        self.issues = [
            model_issue("alice", [
                comment("bob"),
                comment("alice"),
                comment("alice", event_type="labeled"),
                comment("github-actions[bot]"),
            ], number=1),
            model_issue("bob", [comment("bob")], number=2),
            model_issue("dependabot[bot]", [comment("carol")], number=3),
        ]

    def test_empty_input(self):
        result = analyze_contributor_activity([])
        self.assertEqual(result["total_issues"], 0)
        self.assertEqual(result["total_comments"], 0)
        self.assertEqual(result["total_contributors"], 0)
        self.assertEqual(result["contributors"], Counter())

    def test_result_has_expected_keys(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(set(result), {
            "total_issues", "total_comments", "total_contributors",
            "issues_opened", "comments_recorded", "contributors",
        })

    def test_counts_with_model_objects(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["total_issues"], 3)
        self.assertEqual(result["total_comments"], 5)
        self.assertEqual(result["issues_opened"], Counter(alice=1, bob=1))
        self.assertEqual(
            result["comments_recorded"], Counter(bob=2, alice=1, carol=1)
        )
        self.assertEqual(
            result["contributors"], Counter(bob=3, alice=2, carol=1)
        )
        self.assertEqual(result["total_contributors"], 3)

    def test_bots_are_excluded_by_default(self):
        result = analyze_contributor_activity(self.issues)
        self.assertNotIn("dependabot[bot]", result["issues_opened"])
        self.assertNotIn("github-actions[bot]", result["comments_recorded"])

    def test_bot_comments_counted_in_total_comment_events(self):
        default = analyze_contributor_activity(self.issues)
        with_bots = analyze_contributor_activity(self.issues, include_bots=True)
        self.assertEqual(default["total_comments"], with_bots["total_comments"])

    def test_bots_included_when_requested(self):
        result = analyze_contributor_activity(self.issues, include_bots=True)
        self.assertEqual(result["issues_opened"]["dependabot[bot]"], 1)
        self.assertEqual(result["comments_recorded"]["github-actions[bot]"], 1)
        self.assertEqual(result["total_contributors"], 5)

    def test_all_comment_event_type_spellings_counted(self):
        issue = {
            "creator": "alice",
            "events": [
                {"event_type": "commented", "author": "a"},
                {"event_type": "comment", "author": "b"},
                {"type": "issue_comment", "author": "c"},
            ],
        }
        result = analyze_contributor_activity([issue])
        self.assertEqual(result["total_comments"], 3)
        self.assertEqual(result["comments_recorded"], Counter(a=1, b=1, c=1))

    def test_non_comment_events_are_ignored(self):
        events = [comment("x", event_type=t) for t in (
            "labeled", "closed", "mentioned", "subscribed",
            "cross-referenced", "comment_deleted", None,
        )]
        result = analyze_contributor_activity([model_issue("alice", events)])
        self.assertEqual(result["total_comments"], 0)
        self.assertEqual(result["comments_recorded"], Counter())

    def test_github_api_style_dicts(self):
        issue = {
            "user": {"login": "alice"},
            "events": [{"event_type": "commented", "actor": {"login": "bob"}}],
        }
        result = analyze_contributor_activity([issue])
        self.assertEqual(result["issues_opened"], Counter(alice=1))
        self.assertEqual(result["comments_recorded"], Counter(bob=1))

    def test_issue_without_author_and_events(self):
        result = analyze_contributor_activity([{}])
        self.assertEqual(result["total_issues"], 1)
        self.assertEqual(result["total_contributors"], 0)

    def test_events_set_to_none_is_handled(self):
        result = analyze_contributor_activity(
            [{"creator": "alice", "events": None}]
        )
        self.assertEqual(result["issues_opened"], Counter(alice=1))
        self.assertEqual(result["total_comments"], 0)

    def test_comment_without_author_counts_as_event_only(self):
        issue = {"creator": "alice", "events": [{"event_type": "commented"}]}
        result = analyze_contributor_activity([issue])
        self.assertEqual(result["total_comments"], 1)
        self.assertEqual(result["comments_recorded"], Counter())

    def test_contributor_names_stripped_and_merged(self):
        issues = [
            {"creator": "alice ", "events": [comment(" alice")]},
        ]
        result = analyze_contributor_activity(issues)
        self.assertEqual(result["contributors"], Counter(alice=2))

    def test_input_issues_not_modified(self):
        issue = raw_issue("alice", [comment("bob")])
        snapshot = json.dumps(issue, sort_keys=True)
        analyze_contributor_activity([issue])
        self.assertEqual(json.dumps(issue, sort_keys=True), snapshot)

    def test_accepts_generator_input(self):
        result = analyze_contributor_activity(
            model_issue(f"user{i}", number=i) for i in range(4)
        )
        self.assertEqual(result["total_issues"], 4)
        self.assertEqual(result["total_contributors"], 4)

    def test_ghost_placeholder_not_ranked_as_a_contributor(self):
        # DEFECT: GitHub replaces every deleted account with ghost
        issues = [model_issue("ghost", number=i) for i in range(5)]
        issues.append(model_issue("alice", [comment("ghost")], number=99))
        result = analyze_contributor_activity(issues)
        self.assertNotIn("ghost", result["contributors"])
        self.assertEqual(result["total_contributors"], 1)


# --------------------------------------------------------------------------
# display_results function
# --------------------------------------------------------------------------
class TestDisplayResults(unittest.TestCase):

    def test_summary_and_table_rows(self):
        results = analyze_contributor_activity([
            model_issue("alice", [comment("bob"), comment("bob")]),
        ])
        _, out = quiet(display_results, results)

        self.assertIn("FEATURE 2: CONTRIBUTOR ACTIVITY ANALYSIS", out)
        self.assertIn("Total issues: 1", out)
        self.assertIn("Comment events: 2", out)
        self.assertIn("Identified contributors: 2", out)
        self.assertIn("TOP 10 CONTRIBUTORS", out)

        rows = {line.split()[0]: line.split()[1:] for line in out.splitlines()
                if line.startswith(("alice", "bob"))}
        self.assertEqual(rows["bob"], ["0", "2", "2"])
        self.assertEqual(rows["alice"], ["1", "0", "1"])
        self.assertNotIn("No identifiable contributors", out)

    def test_rows_sorted_by_total_descending(self):
        # Totals: high=3, mid=2, low=1 (one opened issue).
        results = analyze_contributor_activity([
            model_issue("low", [comment("high")] * 3 + [comment("mid")] * 2),
        ])
        _, out = quiet(display_results, results)
        names = [line.split()[0] for line in out.splitlines()
                 if line.startswith(("high", "mid", "low"))]
        self.assertEqual(names, ["high", "mid", "low"])

    def test_only_top_ten_listed(self):
        issues = [
            model_issue(f"user{i:02d}", [comment(f"user{i:02d}")] * i, i)
            for i in range(1, 13)
        ]
        _, out = quiet(display_results, analyze_contributor_activity(issues))
        for i in range(3, 13):
            self.assertIn(f"user{i:02d}", out)
        self.assertNotIn("user01", out)
        self.assertNotIn("user02", out)

    def test_empty_results_print_hint(self):
        _, out = quiet(display_results, analyze_contributor_activity([]))
        self.assertIn("Identified contributors: 0", out)
        self.assertIn("No identifiable contributors found.", out)


# --------------------------------------------------------------------------
# create_chart function
# --------------------------------------------------------------------------
class ChartTestCase(unittest.TestCase):
    """Redirects the chart output folder to a temporary directory."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_dir = Path(tmp.name).resolve()

        # create_chart builds its output path from the module's __file__.
        patcher = mock.patch.object(
            caa, "__file__", str(self.tmp_dir / "contributor_activity_analysis.py")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.show = mock.patch.object(caa.plt, "show").start()
        self.addCleanup(mock.patch.stopall)

        # Keep a handle on the figure/axes the function creates.
        real_subplots = plt.subplots
        self.created = {}

        def capture(*args, **kwargs):
            fig, ax = real_subplots(*args, **kwargs)
            self.created["fig"], self.created["ax"] = fig, ax
            return fig, ax

        mock.patch.object(caa.plt, "subplots", side_effect=capture).start()
        self.addCleanup(plt.close, "all")


class TestCreateChart(ChartTestCase):

    def setUp(self):
        super().setUp()
        self.results = analyze_contributor_activity([
            model_issue("alice", [comment("bob"), comment("bob"),
                                  comment("alice")], number=1),
            model_issue("carol", number=2),
        ])

    def test_empty_results_skip_chart(self):
        path, out = quiet(create_chart, analyze_contributor_activity([]))
        self.assertIsNone(path)
        self.assertIn("Chart skipped: no contributor data.", out)
        self.assertNotIn("fig", self.created)
        self.assertFalse((self.tmp_dir / "images").exists())

    def test_chart_file_is_saved(self):
        path, out = quiet(create_chart, self.results, show_chart=False)
        expected = self.tmp_dir / "images" / "contributor_activity_chart.png"
        self.assertEqual(path, expected)
        self.assertTrue(expected.is_file())
        self.assertGreater(expected.stat().st_size, 0)
        self.assertIn(f"Chart saved: {expected}", out)

    def test_show_chart_false_does_not_display(self):
        quiet(create_chart, self.results, show_chart=False)
        self.show.assert_not_called()

    def test_show_chart_true_displays(self):
        quiet(create_chart, self.results, show_chart=True)
        self.show.assert_called_once()

    def test_titles_axes_and_legend(self):
        quiet(create_chart, self.results, show_chart=False)
        ax = self.created["ax"]
        self.assertEqual(ax.get_title(), "Top 10 Poetry GitHub Contributors")
        self.assertEqual(ax.get_xlabel(), "Recorded Activity")
        self.assertEqual(ax.get_ylabel(), "Contributor")
        legend = [t.get_text() for t in ax.get_legend().get_texts()]
        self.assertEqual(legend, ["Issues Opened", "Comments"])

    def test_bars_stacked_with_correct_values(self):
        quiet(create_chart, self.results, show_chart=False)
        ax = self.created["ax"]
        opened_bars, comment_bars = ax.containers

        # Highest total is plotted last (top of a horizontal bar chart).
        names = [t.get_text() for t in ax.get_yticklabels()]
        self.assertEqual(names[-1], "alice")  # alice: 1 issue + 1 comment = 2
        self.assertEqual(set(names), {"alice", "bob", "carol"})

        by_name = {
            name: (o.get_width(), c.get_width(), c.get_x())
            for name, o, c in zip(names, opened_bars, comment_bars)
        }
        self.assertEqual(by_name["bob"], (0, 2, 0))
        self.assertEqual(by_name["alice"], (1, 1, 1))  # comments start after issues
        self.assertEqual(by_name["carol"], (1, 0, 1))

    def test_chart_limited_to_ten_contributors(self):
        issues = [model_issue(f"user{i:02d}", number=i) for i in range(15)]
        quiet(create_chart, analyze_contributor_activity(issues),
              show_chart=False)
        self.assertEqual(len(self.created["ax"].get_yticklabels()), 10)

    def test_figure_closed(self):
        quiet(create_chart, self.results, show_chart=False)
        self.assertFalse(plt.fignum_exists(self.created["fig"].number))


# --------------------------------------------------------------------------
# run function
# --------------------------------------------------------------------------
class TestRun(ChartTestCase):

    def test_run_returns_results_produces_all_output(self):
        issues = [model_issue("alice", [comment("bob")])]
        results, out = quiet(run, issues, show_chart=False)

        self.assertEqual(results["contributors"], Counter(alice=1, bob=1))
        self.assertIn("FEATURE 2", out)
        self.assertIn("Chart saved:", out)
        self.assertTrue(
            (self.tmp_dir / "images" / "contributor_activity_chart.png").is_file()
        )
        self.show.assert_not_called()

    def test_run_forwards_include_bots(self):
        issues = [model_issue("renovate[bot]")]
        excluded, _ = quiet(run, issues, show_chart=False)
        included, _ = quiet(run, issues, show_chart=False, include_bots=True)
        self.assertEqual(excluded["total_contributors"], 0)
        self.assertEqual(included["total_contributors"], 1)

    def test_run_shows_chart_by_default(self):
        quiet(run, [model_issue("alice")])
        self.show.assert_called_once()


# --------------------------------------------------------------------------
# Mock the dataset and load through DataLoader
# --------------------------------------------------------------------------
def _event(event_type, author, date="2024-05-01T10:00:00+00:00", **extra):
    return {"event_type": event_type, "author": author,
            "event_date": date, **extra}

MOCK_POETRY_ISSUES = [
    {
        **raw_issue("dbrtly", number=9785),
        "labels": ["kind/bug", "status/triage"],
        "state": "closed",
        "title": "python version resolution is incorrect",
        "events": [
            _event("labeled", "dbrtly", label="kind/bug"),
            _event("commented", "dimbleby", comment="Check your python range."),
            _event("commented", "dbrtly", comment="Thanks, that fixed it."),
            _event("commented", "dimbleby", comment="Closing."),
            _event("closed", "dimbleby"),
            _event("commented", "github-actions[bot]", comment="Locked."),
            _event("locked", "github-actions[bot]"),
        ],
    },
    {
        **raw_issue("abn", number=9001),
        "labels": ["kind/feature"],
        "events": [
            _event("subscribed", "radoering"),
            _event("mentioned", "radoering"),
            _event("commented", "radoering", comment="Looks good."),
            _event("commented", "abn", comment="Merged upstream."),
            _event("cross-referenced", "dimbleby"),
        ],
    },
    {
        **raw_issue("ghost", number=4000),
        "labels": ["kind/bug"],
        "events": [
            _event("commented", "stale[bot]", comment="Marked as stale."),
            _event("commented", "dimbleby", comment="Duplicate of #3999."),
            _event("marked_as_duplicate", "dimbleby"),
        ],
    },
    {**raw_issue("ghost", number=4001), "events": [
        _event("commented", "ghost", comment="Any update?"),
    ]},
    {**raw_issue("ghost", number=4002)},
    {**raw_issue("turbotimon", number=8123), "events": [
        _event("commented", "abn", comment="Can you share a reproducer?"),
        _event("unlabeled", "abn", label="status/triage"),
    ]},
]


class TestWithMockedPoetryData(unittest.TestCase):
    """End-to-end over DataLoader -> model.Issue -> analysis, with the
    dataset file replaced by MOCK_POETRY_ISSUES (no real file is read)."""

    def setUp(self):
        import data_loader

        mock.patch.object(data_loader, "_ISSUES", None).start()
        mock.patch.object(data_loader.config, "get_parameter",
                          return_value="mock_poetry_issues.json").start()
        self.mocked_open = mock.patch(
            "data_loader.open",
            mock.mock_open(read_data=json.dumps(MOCK_POETRY_ISSUES)),
            create=True,
        ).start()
        self.addCleanup(mock.patch.stopall)

        self.issues, self.load_output = quiet(
            data_loader.DataLoader().get_issues
        )
        self.results = analyze_contributor_activity(self.issues)

    def test_mock_file_loaded(self):
        self.mocked_open.assert_called_once_with("mock_poetry_issues.json", "r")
        self.assertIn("Loaded 6 issues from mock_poetry_issues.json.",
                      self.load_output)
        self.assertTrue(all(isinstance(i, Issue) for i in self.issues))

    def test_totals(self):
        self.assertEqual(self.results["total_issues"], 6)
        self.assertEqual(self.results["total_comments"], 10)

    def test_issue_comment_counts_per_contributor(self):
        self.assertEqual(
            self.results["issues_opened"],
            Counter(ghost=3, dbrtly=1, abn=1, turbotimon=1),
        )
        self.assertEqual(
            self.results["comments_recorded"],
            Counter(dimbleby=3, abn=2, dbrtly=1, radoering=1, ghost=1),
        )

    def test_non_comment_events_do_not_create_contributors(self):
        self.assertEqual(self.results["contributors"]["radoering"], 1)

    def test_bots_are_not_ranked(self):
        for name in self.results["contributors"]:
            self.assertFalse(is_bot(name), name)
        self.assertEqual(self.results["total_contributors"], 6)

    def test_bots_ranked_when_included(self):
        results = analyze_contributor_activity(self.issues, include_bots=True)
        self.assertEqual(results["comments_recorded"]["github-actions[bot]"], 1)
        self.assertEqual(results["comments_recorded"]["stale[bot]"], 1)
        self.assertEqual(results["total_contributors"], 8)

    def test_display_rows_sorted_by_total_with_correct_columns(self):
        _, out = quiet(display_results, self.results)
        rows = [line.split() for line in out.splitlines()
                if line.split() and line.split()[0] in self.results["contributors"]]
        totals = [int(row[3]) for row in rows]
        self.assertEqual(totals, sorted(totals, reverse=True))
        by_name = {row[0]: row[1:] for row in rows}
        self.assertEqual(by_name["abn"], ["1", "2", "3"])
        self.assertEqual(by_name["dimbleby"], ["0", "3", "3"])
        self.assertEqual(by_name["dbrtly"], ["1", "1", "2"])
        self.assertEqual(by_name["radoering"], ["0", "1", "1"])
        self.assertEqual(by_name["turbotimon"], ["1", "0", "1"])

    def test_top_ten_excludes_deleted_user_placeholder(self):
        #DEFECT 2: The "ghost" placeholder for deleted accounts is ranked as a contributor
        top_ten = [n for n, _ in self.results["contributors"].most_common(10)]
        self.assertNotIn("ghost", top_ten)


if __name__ == "__main__":
    unittest.main()
