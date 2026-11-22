"""Unit tests for model.py."""
import unittest
from datetime import datetime

from model import Event, Issue, State


class TestState(unittest.TestCase):

    def test_values(self):
        self.assertEqual(State.open.value, "open")
        self.assertEqual(State.closed.value, "closed")

    def test_state_compares_equal_to_plain_string(self):
        self.assertEqual(State.open, "open")

    def test_lookup_by_name(self):
        self.assertIs(State["closed"], State.closed)


class TestEvent(unittest.TestCase):

    def test_defaults_when_no_json(self):
        event = Event(None)
        self.assertIsNone(event.event_type)
        self.assertIsNone(event.author)
        self.assertIsNone(event.event_date)
        self.assertIsNone(event.label)
        self.assertIsNone(event.comment)

    def test_all_fields_parsed(self):
        event = Event({
            "event_type": "labeled",
            "author": "ada",
            "event_date": "2024-03-02T10:30:00Z",
            "label": "kind/bug",
            "comment": "hello",
        })
        self.assertEqual(event.event_type, "labeled")
        self.assertEqual(event.author, "ada")
        self.assertEqual(event.label, "kind/bug")
        self.assertEqual(event.comment, "hello")
        self.assertIsInstance(event.event_date, datetime)
        self.assertEqual((event.event_date.year, event.event_date.month, event.event_date.day), (2024, 3, 2))
        self.assertIsNotNone(event.event_date.tzinfo)

    def test_missing_date_leaves_none(self):
        self.assertIsNone(Event({"event_type": "closed"}).event_date)

    def test_unparseable_date_leaves_none(self):
        self.assertIsNone(Event({"event_date": "not a date"}).event_date)

    def test_missing_keys_default_to_none(self):
        event = Event({})
        self.assertIsNone(event.event_type)
        self.assertIsNone(event.author)


class TestIssue(unittest.TestCase):

    def _json(self, **overrides):
        base = {
            "url": "https://example.test/issues/9",
            "creator": "ada",
            "labels": ["kind/bug", "area/docs"],
            "state": "closed",
            "assignees": ["bob"],
            "title": "A title",
            "text": "Body",
            "number": 9,
            "created_date": "2024-01-01T00:00:00Z",
            "updated_date": "2024-02-01T00:00:00Z",
            "timeline_url": "https://example.test/timeline",
            "events": [
                {"event_type": "commented", "author": "bob", "event_date": "2024-01-02T00:00:00Z"},
                {"event_type": "closed", "author": "bob", "event_date": "2024-01-03T00:00:00Z"},
            ],
        }
        base.update(overrides)
        return base

    def test_defaults_when_no_json(self):
        issue = Issue()
        self.assertEqual(issue.number, -1)
        self.assertEqual(issue.labels, [])
        self.assertEqual(issue.assignees, [])
        self.assertEqual(issue.events, [])
        self.assertIsNone(issue.state)
        self.assertIsNone(issue.created_date)

    def test_all_fields_parsed(self):
        issue = Issue(self._json())
        self.assertEqual(issue.url, "https://example.test/issues/9")
        self.assertEqual(issue.creator, "ada")
        self.assertEqual(issue.labels, ["kind/bug", "area/docs"])
        self.assertEqual(issue.state, State.closed)
        self.assertEqual(issue.assignees, ["bob"])
        self.assertEqual(issue.title, "A title")
        self.assertEqual(issue.text, "Body")
        self.assertEqual(issue.number, 9)
        self.assertEqual(issue.created_date.year, 2024)
        self.assertEqual(issue.updated_date.month, 2)
        self.assertEqual(issue.timeline_url, "https://example.test/timeline")

    def test_events_are_converted_to_event_objects(self):
        issue = Issue(self._json())
        self.assertEqual(len(issue.events), 2)
        self.assertTrue(all(isinstance(e, Event) for e in issue.events))
        self.assertEqual([e.event_type for e in issue.events], ["commented", "closed"])

    def test_number_given_as_string_is_converted(self):
        self.assertEqual(Issue(self._json(number="42")).number, 42)

    def test_invalid_number_falls_back_to_minus_one(self):
        self.assertEqual(Issue(self._json(number="abc")).number, -1)
        self.assertEqual(Issue(self._json(number=None)).number, -1)

    def test_missing_dates_leave_none(self):
        data = self._json()
        del data["created_date"]
        del data["updated_date"]
        issue = Issue(data)
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)

    def test_invalid_dates_leave_none(self):
        issue = Issue(self._json(created_date="garbage", updated_date="??"))
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)

    def test_missing_optional_lists_default_to_empty(self):
        data = {"state": "open"}
        issue = Issue(data)
        self.assertEqual(issue.labels, [])
        self.assertEqual(issue.assignees, [])
        self.assertEqual(issue.events, [])

    def test_open_state(self):
        self.assertEqual(Issue({"state": "open"}).state, State.open)

    def test_unknown_state_raises_key_error(self):
        with self.assertRaises(KeyError):
            Issue({"state": "merged"})

    def test_missing_state_raises_key_error(self):
        with self.assertRaises(KeyError):
            Issue({"number": 1})


if __name__ == "__main__":
    unittest.main()
