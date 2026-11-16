"""Feature 1: Compare issue resolution times by label."""
import os
from collections import defaultdict
from statistics import median, mean

from issue_analysis_utils import issue_labels, is_issue, resolution_days


def analyze(issues, selected_label=None):
    groups = defaultdict(list)
    for issue in issues:
        if not is_issue(issue):
            continue
        duration = resolution_days(issue)
        if duration is None:
            continue
        for label in set(issue_labels(issue)) or {'Unlabeled'}:
            groups[label].append(duration)

    rows = [
        dict(
            label=label,
            count=len(values),
            median_days=round(median(values), 2),
            mean_days=round(mean(values), 2),
        )
        for label, values in groups.items()
    ]
    rows.sort(key=lambda row: (-row['count'], row['label'].lower()))

    selected = None
    if selected_label:
        selected = next(
            (
                row for row in rows
                if row['label'].casefold() == selected_label.casefold()
            ),
            None,
        )

    return {'rows': rows, 'selected': selected}


def run(issues, label=None, show_chart=True):
    result = analyze(issues, label)

    if not result['rows']:
        print('No closed issues with valid creation and closing dates were found.')
        return result

    if label:
        if result['selected']:
            row = result['selected']
            print(
                f"Selected label '{row['label']}': {row['count']} closed issues, "
                f"median {row['median_days']} days, mean {row['mean_days']} days."
            )
        else:
            print(f"No closed issues found for label '{label}'.")

    print('Resolution time by label (top 10 labels by closed-issue count):')
    for row in result['rows'][:10]:
        print(
            f"  {row['label']}: n={row['count']}, "
            f"median={row['median_days']} days, mean={row['mean_days']} days"
        )

    if show_chart:
        import matplotlib.pyplot as plt

        top = result['rows'][:10]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(
            [row['label'] for row in top],
            [row['median_days'] for row in top],
        )
        ax.set(
            title='Median Issue Resolution Time by Label',
            xlabel='Issue label',
            ylabel='Median days to close',
        )
        ax.tick_params(axis='x', labelrotation=35)
        fig.tight_layout()

        # Ensure the output directory exists before saving the chart.
        os.makedirs("images", exist_ok=True)
        chart_path = os.path.join("images", "label_resolution_chart.png")
        fig.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.show()

    return result
