# Poetry GitHub Issue Analytics

**ENPM611 — Software Engineering Team Project**

This project extends the ENPM611 Python application template to analyze issue activity in the [Poetry](https://github.com/python-poetry/poetry) open-source repository. It uses a prepared JSON dataset of GitHub issues and timeline events to explore issue resolution, contributor activity, and discussion over time.

## Project goals

The team is developing three complementary analyses:

|Feature|Analysis|Question addressed|
|-|-|-|
|**1**|**Issue Resolution Time by Label**|Which issue categories take longer to close?|
|**2**|**Contributor Activity Analysis**|What insights can be gathered about contributor activity?|
|**3**|**Discussion Trend**|Has discussion on issues grown, shrunk, or stayed flat over time?|

The analyses are intended to produce interpretable findings, not just raw counts. Feature 1 supports a user-supplied label and displays summary statistics and a matplotlib chart. Feature 3 groups issue openings and human comments by month and displays a chart. Feature 2 counts issue creation and recorded comment activity by contributor, ranks the most active contributors, and generates a matplotlib chart.

## Requirements

* Python 3.10 or newer (recommended)
* Dependencies listed in `requirements.txt`
* A local copy of the prepared `poetry_issues.json` dataset

The provided model uses `python-dateutil` to parse dates; the analysis charts use `matplotlib`. Install dependencies from the repository's requirements file and ensure those packages are included.

## Setup

1. Clone the **team's fork** and open the project folder:

```bash
      git clone <TEAM_REPOSITORY_URL>
      cd <REPOSITORY_FOLDER>
   ```

2. Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell troubleshooting:**

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1


3. Install project dependencies:

```bash
      python -m pip install -r requirements.txt
   ```

4. Place the prepared dataset in the repository root (or update the configuration to its actual path). Set `config.json` to:

```json
      {
        "ENPM611_PROJECT_DATA_PATH": "poetry_issues_all.json"
      }
   ```

   Only one dataset path is active at a time. To use `poetry_issues_all.json` instead, change the configuration value to that filename and ensure the file exists locally.

## Run the analyses

Run all commands from the repository root with the virtual environment active.

### Feature 1 — Issue Resolution Time by Label

```bash
python run.py --feature 1 --label kind/bug
```

The optional `--label` argument selects a particular label. The dataset contains labels such as `kind/bug`; `bug` is not necessarily an equivalent label.

To display the top labels without selecting one:

```bash
python run.py --feature 1
```

**Method:** The analysis loads issue objects, identifies closed issues with usable dates, computes the elapsed time between `created_date` and the latest recorded `closed` event, groups results by label, and reports the count, mean, and median resolution time. A matplotlib bar chart compares median resolution times for the ten most frequent labels among the analyzed closed issues.

**Interpretation:** Median resolution time describes a typical closed issue, while the mean can be affected by unusually long-lived issues. Time to closure does not necessarily equal time to a confirmed fix. An issue with multiple labels can contribute to multiple label groups. Issues without usable closure timestamps are excluded.

Feature 1: Label Resolution Time Analysis — Sample Results

This feature analyzes how long GitHub issues take to resolve, grouped by issue labels. It calculates the average and median resolution times for closed issues.

How to Run

python run.py --feature 1 --label kind/bug

#### Sample Analysis Results

|Metric|Result|
|-|-:|
|Issue label|`kind/bug`|
|Number of closed issues|256|
|Median resolution time|0.91 days|
|Average resolution time|125.90 days|



Interpretation:

The median resolution time of 0.91 days indicates that half of the analyzed closed bug issues were resolved within approximately 22 hours. The considerably higher average suggests that some issues remained open much longer, creating a right-skewed distribution.

Resolution Time Visualization

Figure 1: Comparison of median resolution times across GitHub issue labels.

![Label Resolution Time Chart](images/label_resolution_chart.png)

Note: These results are from the previously analyzed dataset.

### Feature 2 — Contributor Activity Analysis

```bash
python run.py --feature 2
```

**Question:** Which contributors are most active in creating and discussing Poetry GitHub issues?

**Method:** The analysis processes issue authors and issue timeline events. For each identifiable contributor, it counts issues opened and recorded comment events (`commented`, `comment`, or `issue_comment`). Combined activity is calculated as issues opened plus recorded comments. Bot accounts identified by common bot username suffixes are excluded from contributor rankings by default.

**Output:** The terminal displays the total issues analyzed, number of comment events, number of identified contributors, and the ten most active contributors with their issues-opened, comments-recorded, and combined-activity counts.

**Interpretation:** The ranking highlights contributors with the most recorded issue and discussion activity. These counts reflect the prepared dataset and do not measure contribution quality or capture every type of GitHub contribution.

Feature 2: Contributor Activity Analysis — Results

The analysis was executed successfully against the configured Poetry dataset and produced contributor names and activity counts. Exact totals are not included here because they have not been supplied for this README update.

Contributor Activity Visualization

Figure 2: Top ten contributors by combined recorded activity. Horizontal stacked bars distinguish issues opened from comments recorded.

![Contributor Activity Chart](images/contributor_activity_chart.png)

**Unit tests:** `tests/test_contributor_activity_analysis.py`

```bash
python -m unittest discover -s tests -p "test_contributor_activity_analysis.py" -v
```

### Feature 3 — Discussion Trend

```bash
python run.py --feature 3
python run.py --feature 3 --label kind/bug
```

**Question:** Has discussion on Poetry issues grown, shrunk, or stayed flat over time?

**Method:** Issues are counted in the month of `created_date`. Human `commented` events are counted in the month of `event_date`. Bot accounts are ignored. `comments_per_issue` divides a month's human comments by the number of issues opened that month. A comment can belong to an older issue, so that ratio compares volume. It does not mean the comments were written on the issues opened that month. The optional `--label` argument limits both counts to issues carrying that label.

**Output:** A comparison of the earlier half of the timeline with the later half, the five months with the most human comments, and a two-line chart of issues opened and human comments.

On `poetry_issues_all.json`, February 2018 through May 2021 had 2,686 issues opened and 3.89 human comments per issue opened. June 2021 through October 2024 had 2,887 issues opened and 4.77 human comments per issue opened. The busiest comment month was September 2022, with 920 human comments.

Figure 3: Monthly issue openings and human comments. Each series uses its own axis.

![Monthly issue openings and human discussion](images/discussion_trend_chart.png)

## Data model

The starter application reads JSON records and converts them into `Issue` and `Event` objects:

* `Issue.created_date`: issue creation timestamp
* `Issue.state`: open or closed status
* `Issue.labels`: list of label names
* `Issue.events`: timeline events, including `closed`, `labeled`, and `commented`
* `Event.event_date`: timestamp for the event
* `Event.event_type`: type of timeline event

For Feature 1, the closure timestamp comes from a `closed` event, **not** from `updated_date`. Updating an issue after closure does not change its resolution time.

## Project structure

```text
project-root/
├── run.py                         # CLI entry point and feature dispatch
├── config.py                      # Configuration reader
├── config.json                    # Active dataset path
├── data_loader.py                 # Loads JSON as Issue objects
├── model.py                       # Issue and Event models
├── example_analysis.py            # Starter example
├── issue_analysis_utils.py        # Shared analysis helpers
├── label_resolution_analysis.py   # Feature 1
├── contributor_activity_analysis.py # Feature 2
├── discussion_trend_analysis.py   # Feature 3
├── requirements.txt               # Python dependencies
├── README.md
├── poetry_issues.json             # Local dataset; usually not committed
└── tests/
    ├── test_label_resolution_analysis.py
    ├── test_contributor_activity_analysis.py
    └── test_discussion_trend_analysis.py
└── images/
    ├── label_resolution_chart.png
    ├── contributor_activity_chart.png
    └── discussion_trend_chart.png
```

The Feature 2 module and its tests are implemented on `feature/contributor-activity-analysis` and should be merged into `main` after review.

## Testing

Run the test suite from the project root:

```bash
python -m unittest discover -s tests -v
```

Then perform a manual end-to-end check:

```bash
python run.py --feature 1 --label kind/bug
python run.py --feature 2
```

Confirm that the command loads the configured JSON dataset, prints meaningful statistics, and displays the matplotlib chart. Unit tests using synthetic issue records do not by themselves verify compatibility with the actual Poetry JSON schema.

## Team collaboration

Development takes place in the team's fork of the starter repository. Each team member should work on a feature branch, commit meaningful changes, push the branch, open a pull request targeting `main`, and participate in review before merging.

Example workflow for Feature 1:

```bash
git checkout feature/label-resolution-analysis
git status
git add README.md run.py config.json issue_analysis_utils.py label_resolution_analysis.py tests/test_label_resolution_analysis.py
git commit -m "Document and implement label resolution analysis"
git push -u origin feature/label-resolution-analysis
```

Stage only files that exist and belong to your change. Do not commit `.venv/`, credentials, or large dataset files. If a pull request already exists for the branch, new pushed commits appear in that same pull request.

## ENPM611 milestones

1. **Design:** Component diagrams, sequence diagram, and repository URL.
2. **Implementation:** Three completed analyses and an updated README in the team repository.
3. **Testing:** Test another team's application, report failures and defects, and document coverage.
4. **Presentation:** Present the analyses, findings, design, testing results, and a live demonstration.

## Limitations

* Findings reflect the provided dataset, not necessarily all current GitHub issues.
* An issue can have multiple labels, so label-group counts should not be summed to estimate unique issues.
* Closed issues lacking a valid recorded closure event cannot be assigned a reliable resolution duration using this method.
* Correlation between discussion activity and resolution time does not establish causation.
* Feature 2 counts only identifiable issue authors and supported comment events; it excludes common bot usernames from rankings by default.
* Feature 3 excludes bot comments. Comments are dated by the comment event, so a busy comment month is not necessarily a month when many new issues were opened.

## Team Contributions

|Feature|Contribution|Team Member|
|-|-|-|
| Feature 1 | Label Resolution Time Analysis | Bala Govindaraju |
| Feature 2 | Contributors Dashboard | Jael Andre |
| Feature 3 | Discussion Trend Analysis | Bhargav Nallamothu |

## Project attribution

Developed as a three-member team project for **ENPM611**, using the course-provided application template and prepared GitHub issue data from the Poetry open-source project.