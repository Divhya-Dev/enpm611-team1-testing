
import unittest

from contributor_activity_analysis import (
    analyze_contributor_activity,
    get_username,
    is_bot,
)


class TestContributorActivityAnalysis(unittest.TestCase):

    def setUp(self):
        self.issues = [
            {
                "user": {"login": "alice"},
                "events": [
                    {
                        "event_type": "commented",
                        "actor": {"login": "bob"},
                    },
                    {
                        "event_type": "commented",
                        "actor": {"login": "alice"},
                    },
                ],
            },
            {
                "user": {"login": "bob"},
                "events": [
                    {
                        "event_type": "commented",
                        "actor": {"login": "bob"},
                    }
                ],
            },
        ]

    def test_total_issues(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["total_issues"], 2)

    def test_total_comments(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["total_comments"], 3)

    def test_total_contributors(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["total_contributors"], 2)

    def test_issues_opened(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["issues_opened"]["alice"], 1)
        self.assertEqual(result["issues_opened"]["bob"], 1)

    def test_comments_recorded(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["comments_recorded"]["bob"], 2)
        self.assertEqual(result["comments_recorded"]["alice"], 1)

    def test_combined_activity(self):
        result = analyze_contributor_activity(self.issues)
        self.assertEqual(result["contributors"]["bob"], 3)
        self.assertEqual(result["contributors"]["alice"], 2)

    def test_empty_dataset(self):
        result = analyze_contributor_activity([])
        self.assertEqual(result["total_contributors"], 0)

    def test_username_extraction(self):
        self.assertEqual(
            get_username({"login": "alice"}),
            "alice"
        )

    def test_bot_detection(self):
        self.assertTrue(is_bot("dependabot[bot]"))
        self.assertFalse(is_bot("alice"))

    def test_bot_exclusion(self):
        issues = [
            {
                "user": {"login": "dependabot[bot]"},
                "events": []
            }
        ]

        result = analyze_contributor_activity(issues)
        self.assertEqual(result["total_contributors"], 0)


if __name__ == "__main__":
    unittest.main()
