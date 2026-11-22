"""Additional white-box tests for discussion_trend_analysis.py (Feature 3)."""
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

import contributor_activity_analysis as caa
import discussion_trend_analysis as dta
from model import Issue


def _issue(number, created, labels=None, events=None, **extra):
    record = {"number": number, "state": "open", "created_date": created,
              "labels": labels or [], "events": events or []}
    record.update(extra)
    return record


def _comment(author, when):
    return {"event_type": "commented", "author": author, "event_date": when}


class TestHelpers(unittest.TestCase):

    def test_is_bot(self):
        self.assertTrue(dta._is_bot(None))
        self.assertTrue(dta._is_bot(""))
        self.assertTrue(dta._is_bot("github-actions[bot]"))
        self.assertTrue(dta._is_bot("release-bot"))
        self.assertFalse(dta._is_bot("ada"))

    def test_bot_detection_matches_feature_2(self):
        """DEFECT: Feature 3 does not treat the '_bot' suffix as a bot, but
        Feature 2 does, so the two features disagree about who is a human."""
        self.assertEqual(dta._is_bot("release_bot"), caa.is_bot("release_bot"))

    def test_month_key(self):
        self.assertEqual(dta._month_key("2024-03-15T00:00:00Z"), "2024-03")
        self.assertEqual(dta._month_key(datetime(2023, 12, 31, tzinfo=timezone.utc)), "2023-12")
        self.assertIsNone(dta._month_key(None))
        self.assertIsNone(dta._month_key("nonsense"))

    def test_month_key_converts_to_utc_before_bucketing(self):
        self.assertEqual(dta._month_key("2024-03-31T23:30:00-05:00"), "2024-04")

    def test_matches_label(self):
        self.assertTrue(dta._matches_label([], None))
        self.assertTrue(dta._matches_label(["Kind/Bug"], "kind/bug"))
        self.assertFalse(dta._matches_label(["kind/bug"], "docs"))
        self.assertFalse(dta._matches_label([], "docs"))

    def test_period_stats(self):
        rows = [{"issues_opened": 2, "human_comments": 3}, {"issues_opened": 1, "human_comments": 0}]
        self.assertEqual(dta._period_stats(rows),
                         {"months": 2, "issues_opened": 3, "human_comments": 3, "comments_per_issue": 1.0})

    def test_period_stats_without_issues_has_no_rate(self):
        stats = dta._period_stats([{"issues_opened": 0, "human_comments": 4}])
        self.assertIsNone(stats["comments_per_issue"])

    def test_period_stats_empty(self):
        stats = dta._period_stats([])
        self.assertEqual((stats["months"], stats["issues_opened"], stats["human_comments"]), (0, 0, 0))
        self.assertIsNone(stats["comments_per_issue"])

    def test_rate_clause(self):
        self.assertEqual(dta._rate_clause(None), "no issues opened")
        self.assertEqual(dta._rate_clause(2.5), "2.5 human comments per issue opened")


class TestAnalyze(unittest.TestCase):

    def test_empty_input(self):
        result = dta.analyze([])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["early"]["months"], 0)
        self.assertEqual(result["late"]["months"], 0)
        self.assertIsNone(result["selected_label"])

    def test_single_month_leaves_early_period_empty(self):
        result = dta.analyze([_issue(1, "2024-01-10T00:00:00Z")])
        self.assertEqual(result["early"]["months"], 0)
        self.assertEqual(result["late"]["months"], 1)

    def test_odd_number_of_months_gives_extra_month_to_late_period(self):
        issues = [_issue(n, f"2024-0{n}-01T00:00:00Z") for n in (1, 2, 3)]
        result = dta.analyze(issues)
        self.assertEqual((result["early"]["months"], result["late"]["months"]), (1, 2))

    def test_issue_without_created_date_is_not_counted_as_opened(self):
        result = dta.analyze([_issue(1, None, events=[_comment("ada", "2024-02-01T00:00:00Z")])])
        row = result["rows"][0]
        self.assertEqual((row["month"], row["issues_opened"], row["human_comments"]), ("2024-02", 0, 1))

    def test_created_at_alias_is_accepted(self):
        issue = {"number": 1, "created_at": "2024-05-01T00:00:00Z", "labels": [], "events": []}
        self.assertEqual(dta.analyze([issue])["rows"][0]["month"], "2024-05")

    def test_comment_with_missing_author_or_date_is_ignored(self):
        issue = _issue(1, "2024-01-01T00:00:00Z", events=[
            {"event_type": "commented", "event_date": "2024-01-02T00:00:00Z"},
            {"event_type": "commented", "author": "ada"},
        ])
        self.assertEqual(dta.analyze([issue])["rows"][0]["human_comments"], 0)

    def test_only_commented_events_count(self):
        issue = _issue(1, "2024-01-01T00:00:00Z", events=[
            {"event_type": "labeled", "author": "ada", "event_date": "2024-01-02T00:00:00Z"},
            _comment("ada", "2024-01-03T00:00:00Z"),
        ])
        self.assertEqual(dta.analyze([issue])["rows"][0]["human_comments"], 1)

    def test_label_filter_applies_to_comments_too(self):
        issues = [
            _issue(1, "2024-01-01T00:00:00Z", labels=["kind/bug"], events=[_comment("ada", "2024-01-02T00:00:00Z")]),
            _issue(2, "2024-01-01T00:00:00Z", labels=["kind/feature"],
                   events=[_comment("ada", "2024-01-02T00:00:00Z"), _comment("bob", "2024-01-03T00:00:00Z")]),
        ]
        result = dta.analyze(issues, selected_label="KIND/BUG")
        self.assertEqual(result["selected_label"], "KIND/BUG")
        self.assertEqual(result["rows"][0]["human_comments"], 1)

    def test_months_without_activity_are_omitted(self):
        issues = [_issue(1, "2024-01-01T00:00:00Z"), _issue(2, "2024-06-01T00:00:00Z")]
        self.assertEqual([r["month"] for r in dta.analyze(issues)["rows"]], ["2024-01", "2024-06"])

    def test_rows_are_sorted_chronologically(self):
        issues = [_issue(1, "2024-03-01T00:00:00Z"), _issue(2, "2023-12-01T00:00:00Z")]
        self.assertEqual([r["month"] for r in dta.analyze(issues)["rows"]], ["2023-12", "2024-03"])

    def test_works_with_issue_model_objects(self):
        issue = Issue({
            "state": "open", "created_date": "2024-01-05T00:00:00Z", "labels": ["kind/bug"],
            "events": [{"event_type": "commented", "author": "ada", "event_date": "2024-01-06T00:00:00Z"}],
        })
        row = dta.analyze([issue])["rows"][0]
        self.assertEqual((row["issues_opened"], row["human_comments"], row["comments_per_issue"]), (1, 1, 1.0))


class TestFinding(unittest.TestCase):

    def test_no_rows(self):
        self.assertEqual(dta._finding(dta.analyze([])), "No issues with dates or human comments were found.")

    def test_single_month(self):
        text = dta._finding(dta.analyze([_issue(1, "2024-01-01T00:00:00Z")]))
        self.assertEqual(text, "Only 2024-01 has activity, so there is no earlier period to compare.")

    def test_two_periods(self):
        issues = [
            _issue(1, "2024-01-01T00:00:00Z", events=[_comment("a", "2024-01-02T00:00:00Z")]),
            _issue(2, "2024-02-01T00:00:00Z", events=[_comment("a", "2024-02-02T00:00:00Z"),
                                                      _comment("b", "2024-02-03T00:00:00Z")]),
        ]
        text = dta._finding(dta.analyze(issues))
        self.assertIn("From 2024-01 through 2024-01", text)
        self.assertIn("1.0 human comments per issue opened", text)
        self.assertIn("From 2024-02 through 2024-02", text)
        self.assertIn("2.0 human comments per issue opened", text)

    def test_period_with_comments_but_no_openings(self):
        issues = [
            _issue(1, None, events=[_comment("a", "2024-01-02T00:00:00Z")]),
            _issue(2, "2024-02-01T00:00:00Z"),
        ]
        self.assertIn("no issues opened", dta._finding(dta.analyze(issues)))


class TestRun(unittest.TestCase):

    def _run(self, issues, **kwargs):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            result = dta.run(issues, **kwargs)
        return result, buffer.getvalue()

    def test_prints_question_method_and_finding(self):
        _, printed = self._run([_issue(1, "2024-01-01T00:00:00Z")], show_chart=False)
        self.assertIn("Question: has discussion on Poetry issues grown, shrunk, or stayed flat over time?", printed)
        self.assertIn("Method:", printed)
        self.assertIn("Only 2024-01 has activity", printed)

    def test_label_with_no_matches(self):
        result, printed = self._run([_issue(1, "2024-01-01T00:00:00Z")], label="nope", show_chart=False)
        self.assertEqual(result["rows"], [])
        self.assertIn("No issues found for label 'nope'.", printed)
        self.assertNotIn("Months with the most human comments", printed)

    def test_label_with_matches_prints_filter_notice(self):
        issues = [_issue(1, "2024-01-01T00:00:00Z", labels=["kind/bug"])]
        _, printed = self._run(issues, label="kind/bug", show_chart=False)
        self.assertIn("Filtered to label 'kind/bug'.", printed)

    def test_no_data_without_label(self):
        _, printed = self._run([], show_chart=False)
        self.assertIn("No issues with dates or human comments were found.", printed)

    def test_busiest_months_are_ranked_and_capped_at_five(self):
        issues = [
            _issue(n, f"2024-{n:02d}-01T00:00:00Z",
                   events=[_comment("ada", f"2024-{n:02d}-02T00:00:00Z")] * n)
            for n in range(1, 8)
        ]
        _, printed = self._run(issues, show_chart=False)
        listed = [line for line in printed.splitlines() if line.startswith("  2024-")]
        self.assertEqual(len(listed), 5)
        self.assertTrue(listed[0].startswith("  2024-07"))

    def test_month_without_openings_prints_na(self):
        _, printed = self._run([_issue(1, None, events=[_comment("a", "2024-01-02T00:00:00Z")])], show_chart=False)
        self.assertIn("comments per issue opened=n/a", printed)

    def test_chart_is_saved_in_images_directory(self):
        issues = [_issue(n, f"2024-{n:02d}-01T00:00:00Z", events=[_comment("a", f"2024-{n:02d}-05T00:00:00Z")])
                  for n in range(1, 6)]
        with tempfile.TemporaryDirectory() as tmp, mock.patch("matplotlib.pyplot.show") as show:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self._run(issues)
                self.assertTrue(os.path.isfile(os.path.join("images", "discussion_trend_chart.png")))
            finally:
                os.chdir(old)
        show.assert_called_once()

    def test_chart_skipped_when_there_is_nothing_to_plot(self):
        with mock.patch("discussion_trend_analysis._show_chart") as chart:
            self._run([], show_chart=True)
        chart.assert_not_called()

    def test_chart_thins_x_axis_labels_for_long_series(self):
        issues = [_issue(n, f"{2000 + n // 12}-{n % 12 + 1:02d}-01T00:00:00Z") for n in range(60)]
        with tempfile.TemporaryDirectory() as tmp, mock.patch("matplotlib.pyplot.show"):
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self._run(issues)
                self.assertTrue(os.path.isfile(os.path.join("images", "discussion_trend_chart.png")))
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
