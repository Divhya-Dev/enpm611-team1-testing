
"""
Feature 2: Contributor Activity Analysis
ENPM611 - Poetry GitHub Issue Analytics

Analyzes:
- Issues opened by contributors
- Comments made by contributors
- Top 10 contributors
- Contributor activity visualization
"""

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


def get_field(obj, *names, default=None):
    """Read fields from dictionaries or Python objects."""
    if obj is None:
        return default

    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)

        if value is not None:
            return value

    return default


def get_username(value):
    """Extract a GitHub username."""
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip() or None

    username = get_field(
        value, "login", "username", "name"
    )

    return str(username).strip() if username else None


def is_bot(username):
    """Detect common bot account names."""
    if not username:
        return False

    username = username.lower()

    return (
        username.endswith("[bot]")
        or username.endswith("-bot")
        or username.endswith("_bot")
    )


def analyze_contributor_activity(issues, include_bots=False):
    """Calculate contributor activity statistics."""

    issues_opened = Counter()
    comments_recorded = Counter()

    total_issues = 0
    total_comments = 0

    for issue in issues:
        total_issues += 1

        author = get_username(
            get_field(issue, "user", "author", "creator")
        )

        if author and (include_bots or not is_bot(author)):
            issues_opened[author] += 1

        events = get_field(issue, "events", default=[]) or []

        for event in events:
            event_type = get_field(
                event, "event_type", "type"
            )

            if event_type not in (
                "commented", "comment", "issue_comment"
            ):
                continue

            total_comments += 1

            contributor = get_username(
                get_field(event, "actor", "user", "author")
            )

            if contributor and (
                include_bots or not is_bot(contributor)
            ):
                comments_recorded[contributor] += 1

    contributors = issues_opened + comments_recorded

    return {
        "total_issues": total_issues,
        "total_comments": total_comments,
        "total_contributors": len(contributors),
        "issues_opened": issues_opened,
        "comments_recorded": comments_recorded,
        "contributors": contributors,
    }


def display_results(results):
    """Print contributor activity statistics."""

    print("\n" + "=" * 65)
    print("FEATURE 2: CONTRIBUTOR ACTIVITY ANALYSIS")
    print("=" * 65)

    print(f"Total issues: {results['total_issues']}")
    print(f"Comment events: {results['total_comments']}")
    print(
        f"Identified contributors: "
        f"{results['total_contributors']}"
    )

    print("\nTOP 10 CONTRIBUTORS")
    print("-" * 65)

    print(
        f"{'Contributor':<25}"
        f"{'Issues':>10}"
        f"{'Comments':>12}"
        f"{'Total':>10}"
    )

    print("-" * 65)

    for username, total in (
        results["contributors"].most_common(10)
    ):
        opened = results["issues_opened"][username]
        comments = results["comments_recorded"][username]

        print(
            f"{username:<25}"
            f"{opened:>10}"
            f"{comments:>12}"
            f"{total:>10}"
        )

    if not results["contributors"]:
        print(
            "No identifiable contributors found. "
            "Check the dataset and model fields."
        )


def create_chart(results, show_chart=True):
    """Create a stacked horizontal bar chart."""

    top = results["contributors"].most_common(10)

    if not top:
        print("Chart skipped: no contributor data.")
        return None

    usernames = [name for name, _ in top][::-1]

    opened = [
        results["issues_opened"][name]
        for name in usernames
    ]

    comments = [
        results["comments_recorded"][name]
        for name in usernames
    ]

    fig, ax = plt.subplots(figsize=(11, 6))

    ax.barh(
        usernames,
        opened,
        label="Issues Opened"
    )

    ax.barh(
        usernames,
        comments,
        left=opened,
        label="Comments"
    )

    ax.set_title("Top 10 Poetry GitHub Contributors")
    ax.set_xlabel("Recorded Activity")
    ax.set_ylabel("Contributor")
    ax.legend()

    fig.tight_layout()

    output_dir = Path(__file__).resolve().parent / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = (
        output_dir / "contributor_activity_chart.png"
    )

    fig.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )

    print(f"\nChart saved: {output_path}")

    if show_chart:
        plt.show()

    plt.close(fig)

    return output_path


def run(issues, show_chart=True, include_bots=False):
    """Execute Feature 2 analysis."""

    results = analyze_contributor_activity(
        issues,
        include_bots=include_bots
    )

    display_results(results)
    create_chart(results, show_chart=show_chart)

    return results
