"""Feature 3: Monthly trend of issue openings and human discussion."""
import os
from collections import Counter

from issue_analysis_utils import field, is_issue, issue_labels, timestamp


def _is_bot(author):
    if not author:
        return True
    name = str(author).lower()
    return name.endswith("[bot]") or name.endswith("-bot")


def _month_key(value):
    when = timestamp(value)
    if when is None:
        return None
    return when.strftime("%Y-%m")


def _matches_label(labels, selected_label):
    if not selected_label:
        return True
    wanted = selected_label.casefold()
    return any(label.casefold() == wanted for label in labels)


def _period_stats(rows):
    opened = sum(row["issues_opened"] for row in rows)
    comments = sum(row["human_comments"] for row in rows)
    return {
        "months": len(rows),
        "issues_opened": opened,
        "human_comments": comments,
        "comments_per_issue": round(comments / opened, 2) if opened else None,
    }


def analyze(issues, selected_label=None):
    opened_by_month = Counter()
    comments_by_month = Counter()
    for issue in issues:
        if not is_issue(issue):
            continue
        labels = issue_labels(issue)
        if not _matches_label(labels, selected_label):
            continue
        created = _month_key(field(issue, "created_date") or field(issue, "created_at"))
        if created:
            opened_by_month[created] += 1
        for event in field(issue, "events", []) or []:
            if field(event, "event_type") != "commented":
                continue
            if _is_bot(field(event, "author")):
                continue
            commented = _month_key(field(event, "event_date"))
            if commented:
                comments_by_month[commented] += 1

    rows = []
    for month in sorted(set(opened_by_month) | set(comments_by_month)):
        opened = opened_by_month[month]
        comments = comments_by_month[month]
        rows.append({
            "month": month,
            "issues_opened": opened,
            "human_comments": comments,
            "comments_per_issue": round(comments / opened, 2) if opened else None,
        })
    midpoint = len(rows) // 2
    return {
        "selected_label": selected_label,
        "rows": rows,
        "early": _period_stats(rows[:midpoint]),
        "late": _period_stats(rows[midpoint:]),
    }


def _rate_clause(rate):
    if rate is None:
        return "no issues opened"
    return f"{rate} human comments per issue opened"


def _finding(result):
    rows = result["rows"]
    if not rows:
        return "No issues with dates or human comments were found."
    early = result["early"]
    late = result["late"]
    if not early["months"]:
        return f"Only {rows[0]['month']} has activity, so there is no earlier period to compare."
    return (
        f"From {rows[0]['month']} through {rows[early['months'] - 1]['month']}, "
        f"the project opened {early['issues_opened']} issues and recorded "
        f"{_rate_clause(early['comments_per_issue'])}. "
        f"From {rows[early['months']]['month']} through {rows[-1]['month']}, "
        f"it opened {late['issues_opened']} issues and recorded "
        f"{_rate_clause(late['comments_per_issue'])}. "
        "Comments are counted in the month they were written, which can be later than the month the issue opened."
    )


def run(issues, label=None, show_chart=True):
    result = analyze(issues, label)
    print("Question: has discussion on Poetry issues grown, shrunk, or stayed flat over time?")
    print("Method: group issues by created month and human comment events by comment month.")
    print("Bot accounts are ignored. comments_per_issue divides that month's comments by issues opened that month.")
    if label and not result["rows"]:
        print(f"No issues found for label '{label}'.")
        return result
    if label:
        print(f"Filtered to label '{label}'.")
    print(_finding(result))
    busiest = sorted(result["rows"], key=lambda row: (-row["human_comments"], row["month"]))[:5]
    if busiest:
        print("Months with the most human comments:")
        for row in busiest:
            rate = row["comments_per_issue"]
            rate_text = "n/a" if rate is None else str(rate)
            print(
                f"  {row['month']}: issues opened={row['issues_opened']}, "
                f"human comments={row['human_comments']}, comments per issue opened={rate_text}"
            )
    if show_chart and result["rows"]:
        _show_chart(result)
    return result


def _show_chart(result):
    import matplotlib.pyplot as plt

    rows = result["rows"]
    positions = list(range(len(rows)))
    fig, ax_issues = plt.subplots(figsize=(11, 5))
    ax_comments = ax_issues.twinx()
    issue_line, = ax_issues.plot(
        positions,
        [row["issues_opened"] for row in rows],
        color="#1d4ed8",
        label="Issues opened",
    )
    comment_line, = ax_comments.plot(
        positions,
        [row["human_comments"] for row in rows],
        color="#b00020",
        label="Human comments",
    )
    step = max(1, len(rows) // 12)
    shown = positions[::step]
    ax_issues.set_xticks(shown)
    ax_issues.set_xticklabels([rows[i]["month"] for i in shown], rotation=45, ha="right")
    ax_issues.set_xlabel("Month")
    ax_issues.set_ylabel("Issues opened")
    ax_comments.set_ylabel("Human comments")
    ax_issues.set_title("Monthly issue openings and human discussion")
    ax_issues.legend([issue_line, comment_line], ["Issues opened", "Human comments"], loc="upper left")
    fig.tight_layout()
    os.makedirs("images", exist_ok=True)
    fig.savefig("images/discussion_trend_chart.png", dpi=150, bbox_inches="tight")
    plt.show()
