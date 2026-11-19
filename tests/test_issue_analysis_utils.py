"""White-box unit tests for issue_analysis_utils.py
"""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from issue_analysis_utils import (
    comment_count,
    field,
    is_issue,
    issue_labels,
    resolution_days,
    timestamp,
)
from model import Issue, State

UTC = timezone.utc


def raw_issue(state="closed", created="2024-01-01T00:00:00+00:00",
              events=None, **extra):
    """Raw issue dict in the dataset's JSON format."""
    record = {
        "url": "https://github.com/example/repository/issues/1",
        "creator": "alice",
        "labels": [],
        "state": state,
        "assignees": [],
        "title": "Issue 1",
        "text": "",
        "number": 1,
        "created_date": created,
        "updated_date": created,
        "timeline_url": "",
        "events": events or [],
    }
    record.update(extra)
    return record


def closed_event(date):
    return {"event_type": "closed", "author": "abn", "event_date": date}


# --------------------------------------------------------------------------
# field function
# --------------------------------------------------------------------------
class TestField(unittest.TestCase):

    def test_dict_key_present(self):
        self.assertEqual(field({"a": 1}, "a"), 1)

    def test_dict_key_missing_returns_default(self):
        self.assertIsNone(field({}, "a"))
        self.assertEqual(field({}, "a", "dflt"), "dflt")

    def test_dict_key_with_none_value_returns_none_not_default(self):
        self.assertIsNone(field({"a": None}, "a", "dflt"))

    def test_object_attribute_present(self):
        self.assertEqual(field(SimpleNamespace(a=2), "a"), 2)

    def test_object_attribute_missing_returns_default(self):
        self.assertEqual(field(SimpleNamespace(), "a", []), [])

    def test_model_issue_attribute(self):
        issue = Issue(raw_issue())
        self.assertEqual(field(issue, "creator"), "alice")
        self.assertEqual(field(issue, "pull_request", "none"), "none")


# --------------------------------------------------------------------------
# timestamp function
# --------------------------------------------------------------------------
class TestTimestamp(unittest.TestCase):

    def test_none_and_empty_string_return_none(self):
        self.assertIsNone(timestamp(None))
        self.assertIsNone(timestamp(""))

    def test_naive_datetime_is_treated_as_utc(self):
        result = timestamp(datetime(2024, 1, 2, 3, 4, 5))
        self.assertEqual(result, datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC))
        self.assertIs(result.tzinfo, UTC)

    def test_aware_datetime_is_converted_to_utc(self):
        est = timezone(timedelta(hours=-5))
        result = timestamp(datetime(2024, 1, 1, 20, 0, tzinfo=est))
        self.assertEqual(result, datetime(2024, 1, 2, 1, 0, tzinfo=UTC))
        self.assertIs(result.tzinfo, UTC)

    def test_iso_string_with_z_suffix(self):
        self.assertEqual(timestamp("2024-03-01T12:30:00Z"),
                         datetime(2024, 3, 1, 12, 30, tzinfo=UTC))

    def test_iso_string_with_offset_is_converted(self):
        self.assertEqual(timestamp("2024-03-01T12:30:00+02:00"),
                         datetime(2024, 3, 1, 10, 30, tzinfo=UTC))

    def test_dataset_style_string(self):
        self.assertEqual(timestamp("2024-08-18T07:32:47+00:00"),
                         datetime(2024, 8, 18, 7, 32, 47, tzinfo=UTC))

    def test_naive_string_is_treated_as_utc(self):
        self.assertEqual(timestamp("2024-03-01T12:30:00"),
                         datetime(2024, 3, 1, 12, 30, tzinfo=UTC))

    def test_date_only_string(self):
        self.assertEqual(timestamp("2024-03-01"),
                         datetime(2024, 3, 1, tzinfo=UTC))

    def test_unparsable_values_return_none(self):
        for value in ("not a date", "2024-13-45", 1700000000, 3.5):
            with self.subTest(value=value):
                self.assertIsNone(timestamp(value))


# --------------------------------------------------------------------------
# issue_labels function
# --------------------------------------------------------------------------
class TestIssueLabels(unittest.TestCase):

    def test_list_of_strings_from_dataset(self):
        issue = {"labels": ["kind/bug", "status/triage"]}
        self.assertEqual(issue_labels(issue), ["kind/bug", "status/triage"])

    def test_model_issue(self):
        issue = Issue(raw_issue(labels=["kind/feature"]))
        self.assertEqual(issue_labels(issue), ["kind/feature"])

    def test_list_of_github_api_dicts(self):
        issue = {"labels": [{"name": "kind/bug", "color": "red"},
                            {"name": "area/cli"}]}
        self.assertEqual(issue_labels(issue), ["kind/bug", "area/cli"])

    def test_list_of_objects_with_name(self):
        issue = SimpleNamespace(labels=[SimpleNamespace(name="kind/docs")])
        self.assertEqual(issue_labels(issue), ["kind/docs"])

    def test_single_string_is_wrapped(self):
        self.assertEqual(issue_labels({"labels": "kind/bug"}), ["kind/bug"])

    def test_missing_none_or_empty_labels(self):
        self.assertEqual(issue_labels({}), [])
        self.assertEqual(issue_labels({"labels": None}), [])
        self.assertEqual(issue_labels({"labels": []}), [])
        self.assertEqual(issue_labels(SimpleNamespace()), [])

    def test_items_without_name_are_skipped(self):
        issue = {"labels": [{"color": "red"}, None, 42, "kind/bug"]}
        self.assertEqual(issue_labels(issue), ["kind/bug"])

    def test_non_string_names_are_converted(self):
        self.assertEqual(issue_labels({"labels": [{"name": 7}]}), ["7"])

    def test_duplicates_and_order_are_kept(self):
        issue = {"labels": ["b", "a", "b"]}
        self.assertEqual(issue_labels(issue), ["b", "a", "b"])


# --------------------------------------------------------------------------
# is_issue function
# --------------------------------------------------------------------------
class TestIsIssue(unittest.TestCase):

    def test_dataset_issue_without_pull_request_field(self):
        self.assertTrue(is_issue(raw_issue()))
        self.assertTrue(is_issue(Issue(raw_issue())))

    def test_falsy_pull_request_values_are_issues(self):
        for value in (None, False, {}, "", 0):
            with self.subTest(value=value):
                self.assertTrue(is_issue({"pull_request": value}))

    def test_truthy_pull_request_values_are_not_issues(self):
        for value in (True, {"url": "https://x/pulls/1"}, "yes", 1):
            with self.subTest(value=value):
                self.assertFalse(is_issue({"pull_request": value}))

    def test_object_with_pull_request_attribute(self):
        self.assertFalse(is_issue(SimpleNamespace(pull_request=True)))


# --------------------------------------------------------------------------
# resolution_days function
# --------------------------------------------------------------------------
class TestResolutionDays(unittest.TestCase):

    def test_closed_at_is_used_when_present(self):
        issue = {"created_date": "2024-01-01T00:00:00Z",
                 "closed_at": "2024-01-03T12:00:00Z",
                 "state": "open",  # state is not checked on this path
                 "events": [closed_event("2024-02-01T00:00:00Z")]}
        self.assertEqual(resolution_days(issue), 2.5)

    def test_created_at_is_used_when_created_date_missing(self):
        issue = {"created_at": "2024-01-01T00:00:00Z",
                 "closed_at": "2024-01-02T00:00:00Z"}
        self.assertEqual(resolution_days(issue), 1.0)

    def test_open_issue_returns_none(self):
        issue = raw_issue(state="open",
                          events=[closed_event("2024-01-05T00:00:00+00:00")])
        self.assertIsNone(resolution_days(issue))
        self.assertIsNone(resolution_days(Issue(issue)))

    def test_missing_state_returns_none(self):
        self.assertIsNone(resolution_days({"created_date": "2024-01-01"}))

    def test_closed_dict_uses_closed_event(self):
        issue = raw_issue(events=[closed_event("2024-01-08T00:00:00+00:00")])
        self.assertEqual(resolution_days(issue), 7.0)

    def test_state_string_is_case_insensitive(self):
        issue = raw_issue(state="CLOSED",
                          events=[closed_event("2024-01-02T00:00:00+00:00")])
        self.assertEqual(resolution_days(issue), 1.0)

    def test_model_issue_with_state_enum(self):
        issue = Issue(raw_issue(
            events=[closed_event("2024-01-01T06:00:00+00:00")]))
        self.assertIs(issue.state, State.closed)
        self.assertEqual(resolution_days(issue), 0.25)

    def test_latest_closed_event_is_used_after_reopening(self):
        issue = Issue(raw_issue(events=[
            closed_event("2024-01-02T00:00:00+00:00"),
            {"event_type": "reopened", "author": "bob",
             "event_date": "2024-01-03T00:00:00+00:00"},
            closed_event("2024-01-11T00:00:00+00:00"),
        ]))
        self.assertEqual(resolution_days(issue), 10.0)

    def test_non_closed_events_are_ignored(self):
        issue = raw_issue(events=[
            {"event_type": "commented", "author": "a",
             "event_date": "2024-06-01T00:00:00+00:00"},
            {"event_type": "locked", "author": "a",
             "event_date": "2024-07-01T00:00:00+00:00"},
            closed_event("2024-01-04T00:00:00+00:00"),
        ])
        self.assertEqual(resolution_days(issue), 3.0)

    def test_undated_closed_events_are_ignored(self):
        issue = raw_issue(events=[
            closed_event(None),
            closed_event("2024-01-03T00:00:00+00:00"),
        ])
        self.assertEqual(resolution_days(issue), 2.0)

    def test_closed_without_dated_closed_event_returns_none(self):
        # Seen in the Poetry data: closed issues converted to discussions have no "closed" event, and some "closed" events have no date.
        self.assertIsNone(resolution_days(raw_issue(events=[
            {"event_type": "converted_to_discussion", "author": "a",
             "event_date": "2024-01-02T00:00:00+00:00"}])))
        self.assertIsNone(resolution_days(Issue(raw_issue(
            events=[closed_event(None)]))))

    def test_events_none_returns_none(self):
        issue = raw_issue()
        issue["events"] = None
        self.assertIsNone(resolution_days(issue))

    def test_missing_created_date_returns_none(self):
        issue = raw_issue(created=None,
                          events=[closed_event("2024-01-02T00:00:00+00:00")])
        self.assertIsNone(resolution_days(issue))

    def test_closed_before_created_returns_none(self):
        issue = raw_issue(created="2024-02-01T00:00:00+00:00",
                          events=[closed_event("2024-01-01T00:00:00+00:00")])
        self.assertIsNone(resolution_days(issue))

    def test_closed_at_same_moment_is_zero_days(self):
        issue = raw_issue(events=[closed_event("2024-01-01T00:00:00+00:00")])
        self.assertEqual(resolution_days(issue), 0.0)

    def test_mixed_timezones_are_compared_in_utc(self):
        issue = raw_issue(created="2024-01-01T00:00:00+00:00",
                          events=[closed_event("2024-01-02T02:00:00+02:00")])
        self.assertEqual(resolution_days(issue), 1.0)


# --------------------------------------------------------------------------
# comment_count function
# --------------------------------------------------------------------------
class TestCommentCount(unittest.TestCase):

    def test_missing_field_is_zero(self):
        self.assertEqual(comment_count({}), 0)
        self.assertEqual(comment_count(Issue(raw_issue())), 0)

    def test_integer_and_numeric_string(self):
        self.assertEqual(comment_count({"comments": 5}), 5)
        self.assertEqual(comment_count({"comments": "12"}), 12)

    def test_float_is_truncated(self):
        self.assertEqual(comment_count({"comments": 3.9}), 3)

    def test_negative_is_clamped_to_zero(self):
        self.assertEqual(comment_count({"comments": -4}), 0)

    def test_bool_is_zero(self):
        self.assertEqual(comment_count({"comments": True}), 0)
        self.assertEqual(comment_count({"comments": False}), 0)

    def test_collections_are_counted_by_length(self):
        self.assertEqual(comment_count({"comments": ["a", "b", "c"]}), 3)
        self.assertEqual(comment_count({"comments": ("a",)}), 1)
        self.assertEqual(comment_count({"comments": {"1": "a", "2": "b"}}), 2)

    def test_invalid_values_are_zero(self):
        for value in (None, "many", object()):
            with self.subTest(value=value):
                self.assertEqual(comment_count({"comments": value}), 0)

    def test_object_attribute(self):
        self.assertEqual(comment_count(SimpleNamespace(comments=7)), 7)


if __name__ == "__main__":
    unittest.main()
