import unittest
from contextlib import redirect_stdout
from io import StringIO

from discussion_trend_analysis import analyze, run


def _issue(number, created, events=None, labels=None, pull_request=False):
    record = {
        "number": number,
        "state": "open",
        "created_date": created,
        "title": f"Issue {number}",
        "labels": labels or [],
        "events": events or [],
    }
    if pull_request:
        record["pull_request"] = True
    return record


class TestDiscussionTrendAnalysis(unittest.TestCase):

    def test_comments_are_counted_in_the_comment_month(self):
        issue = _issue(
            1,
            "2024-01-15T00:00:00+00:00",
            events=[{"event_type": "commented", "author": "ada", "event_date": "2024-03-02T00:00:00+00:00"}],
        )
        result = analyze([issue])
        by_month = {row["month"]: row for row in result["rows"]}
        self.assertEqual(by_month["2024-01"]["issues_opened"], 1)
        self.assertEqual(by_month["2024-01"]["human_comments"], 0)
        self.assertEqual(by_month["2024-03"]["issues_opened"], 0)
        self.assertEqual(by_month["2024-03"]["human_comments"], 1)
        self.assertIsNone(by_month["2024-03"]["comments_per_issue"])

    def test_bot_comments_and_pull_requests_are_ignored(self):
        issues = [
            _issue(
                1,
                "2024-01-01T00:00:00+00:00",
                events=[
                    {"event_type": "commented", "author": "github-actions[bot]", "event_date": "2024-01-02T00:00:00+00:00"},
                    {"event_type": "commented", "author": "ada", "event_date": "2024-01-03T00:00:00+00:00"},
                    {"event_type": "labeled", "author": "ada", "event_date": "2024-01-04T00:00:00+00:00"},
                ],
            ),
            _issue(2, "2024-01-05T00:00:00+00:00", pull_request=True),
        ]
        row = analyze(issues)["rows"][0]
        self.assertEqual(row["issues_opened"], 1)
        self.assertEqual(row["human_comments"], 1)
        self.assertEqual(row["comments_per_issue"], 1.0)

    def test_later_period_can_have_higher_intensity(self):
        issues = [
            _issue(1, "2024-01-01T00:00:00+00:00", events=[
                {"event_type": "commented", "author": "ada", "event_date": "2024-01-02T00:00:00+00:00"},
            ]),
            _issue(2, "2024-02-01T00:00:00+00:00", events=[
                {"event_type": "commented", "author": "ada", "event_date": "2024-02-02T00:00:00+00:00"},
                {"event_type": "commented", "author": "bea", "event_date": "2024-02-03T00:00:00+00:00"},
            ]),
        ]
        result = analyze(issues)
        self.assertEqual(result["early"]["comments_per_issue"], 1.0)
        self.assertEqual(result["late"]["comments_per_issue"], 2.0)
        self.assertEqual([row["month"] for row in result["rows"]], ["2024-01", "2024-02"])

    def test_label_filter(self):
        issues = [
            _issue(1, "2024-01-01T00:00:00+00:00", labels=["kind/bug"]),
            _issue(2, "2024-01-02T00:00:00+00:00", labels=["kind/feature"]),
        ]
        result = analyze(issues, selected_label="kind/bug")
        self.assertEqual(result["rows"][0]["issues_opened"], 1)
        self.assertEqual(analyze(issues, selected_label="missing")["rows"], [])

    def test_run_prints_the_comparison_without_a_chart(self):
        issues = [
            _issue(1, "2024-01-01T00:00:00+00:00"),
            _issue(2, "2024-02-01T00:00:00+00:00", events=[
                {"event_type": "commented", "author": "ada", "event_date": "2024-02-02T00:00:00+00:00"},
            ]),
        ]
        buffer = StringIO()
        with redirect_stdout(buffer):
            run(issues, show_chart=False)
        printed = buffer.getvalue()
        self.assertIn("2024-01", printed)
        self.assertIn("2024-02", printed)
        self.assertIn("human comments per issue opened", printed)


if __name__ == "__main__":
    unittest.main()
