# Team 01 Defect Report

## Defect 1: Deleted User Placeholder Included in Contributor Rankings
- **Component:** Contributor Activity Analysis (Feature 2)
- **Description:** The deleted-user placeholder "ghost" is included in contributor rankings.
- **Test Cases:** test_ghost_placeholder_not_ranked_as_a_contributor; test_top_ten_excludes_deleted_user_placeholder
- **Expected Result:** The deleted-user placeholder should not appear in contributor rankings.
- **Actual Result:** "ghost" appears in the contributor results and top-ten rankings.
- **Status:** Open

## Defect 2: Whitespace-Only Username Accepted
- **Component:** Contributor Activity Analysis (Feature 2)
- **Description:** A username containing only whitespace is converted into an empty string instead of being rejected.
- **Test Case:** test_whitespace_only_login_returns_none
- **Expected Result:** The function should return None for a whitespace-only username.
- **Actual Result:** The function returns an empty string.
- **Status:** Open

## Defect 3: Inconsistent Bot Detection
- **Component:** Discussion Trend Analysis (Feature 3)
- **Description:** Feature 3 does not identify usernames ending in "_bot" consistently with Feature 2.
- **Test Case:** test_bot_detection_matches_feature_2
- **Expected Result:** Both features should identify the same bot username consistently.
- **Actual Result:** Feature 3 returns False while Feature 2 returns True for "release_bot".
- **Status:** Open

## Defect 4: Missing Issue State Does Not Raise KeyError
- **Component:** Issue Model
- **Description:** Creating an issue without a state does not raise the expected KeyError.
- **Test Case:** test_missing_state_raises_key_error
- **Expected Result:** A KeyError should be raised when the issue state is missing.
- **Actual Result:** No KeyError is raised.
- **Status:** Open

## Defect 5: Unknown Issue State Does Not Raise KeyError
- **Component:** Issue Model
- **Description:** An unrecognized issue state does not raise the expected KeyError.
- **Test Case:** test_unknown_state_raises_key_error
- **Expected Result:** A KeyError should be raised when an unknown state is provided.
- **Actual Result:** No KeyError is raised.
- **Status:** Open
