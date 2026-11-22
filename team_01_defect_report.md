# Team 01 Defect Report

Application under test: `enpm611-team1-testing` (copy of the assigned team's project), `testing` branch.
Environment: Python 3.12, `coverage`, `unittest`. All defects below were reproduced from a clean checkout with:

```
python -m unittest discover -v
```

Full output is in `team_01_test_failures.txt` (219 tests run, 4 failures, 3 distinct defects).

---

## Defect 1: Deleted-account placeholder "ghost" is ranked as a contributor

- **Affected module / feature:** `contributor_activity_analysis.py` — `analyze_contributor_activity()` (Feature 2)
- **Associated test cases:**
  - `tests.test_contributor_activity_analysis.TestAnalyzeContributorActivity.test_ghost_placeholder_not_ranked_as_a_contributor`
  - `tests.test_contributor_activity_analysis.TestWithMockedPoetryData.test_top_ten_excludes_deleted_user_placeholder`
- **Preconditions / test data:** Issues or comment events whose author is `"ghost"` (GitHub's placeholder for deleted accounts). The second test uses the Poetry issue data, where `ghost` appears as an author.
- **Steps to reproduce:**
  1. Build five issues created by `ghost` and one issue by `alice` with a comment by `ghost`.
  2. Call `analyze_contributor_activity(issues)` with default arguments (`include_bots=False`).
  3. Inspect `result["contributors"]`.
- **Expected result:** `ghost` is not counted as a contributor (it is many different deleted people, not one person); `total_contributors == 1`.
- **Actual result:** `ghost` is counted as a contributor and ranks first in the top ten for the real data.
- **Relevant failure output:**
  ```
  AssertionError: 'ghost' unexpectedly found in Counter({'ghost': 6, 'alice': 1})
  AssertionError: 'ghost' unexpectedly found in ['ghost', 'abn', 'dimbleby', 'dbrtly', 'turbotimon', 'radoering']
  ```

## Defect 2: Whitespace-only username is returned as an empty string

- **Affected module / feature:** `contributor_activity_analysis.py` — `get_username()` (Feature 2)
- **Associated test case:** `tests.test_contributor_activity_analysis.TestGetUsername.test_whitespace_only_login_returns_none`
- **Preconditions / test data:** A user object (dict) whose `login` is `"   "`.
- **Steps to reproduce:**
  1. `from contributor_activity_analysis import get_username`
  2. Call `get_username({"login": "   "})`.
- **Expected result:** `None`, as for a missing username and as for a whitespace-only plain string (`get_username("   ")` returns `None`).
- **Actual result:** `''` (empty string). The dict-path does not apply the `.strip() or None` normalization used for the string path, so blank names can be treated as a valid contributor.
- **Relevant failure output:**
  ```
  AssertionError: '' is not None
  ```

## Defect 3: Feature 3 does not treat the `_bot` suffix as a bot (inconsistent with Feature 2)

- **Affected module / feature:** `discussion_trend_analysis.py` — `_is_bot()` (Feature 3) vs. `contributor_activity_analysis.py` — `is_bot()` (Feature 2)
- **Associated test case:** `tests.test_discussion_trend_analysis.TestHelpers.test_bot_detection_matches_feature_2`
- **Preconditions / test data:** Username `"release_bot"`.
- **Steps to reproduce:**
  1. Import both modules.
  2. Call `discussion_trend_analysis._is_bot("release_bot")` and `contributor_activity_analysis.is_bot("release_bot")`.
- **Expected result:** Both functions agree (`True`).
- **Actual result:** Feature 2 returns `True` (it checks `[bot]`, `-bot`, `_bot`); Feature 3 returns `False` (it checks only `[bot]` and `-bot`). A `_bot` account is therefore excluded from Feature 2 but counted as a human in Feature 3.
- **Relevant failure output:**
  ```
  AssertionError: False != True
  ```
