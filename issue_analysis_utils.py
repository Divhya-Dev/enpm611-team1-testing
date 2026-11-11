"""Shared helpers for GitHub Issue objects from the ENPM611 template."""
from datetime import datetime, timezone


def field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def timestamp(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def issue_labels(issue):
    raw = field(issue, 'labels', []) or []
    if isinstance(raw, str):
        raw = [raw]
    names = []
    for item in raw:
        name = field(item, 'name', item if isinstance(item, str) else None)
        if name is not None:
            names.append(str(name))
    return names


def is_issue(issue):
    return not bool(field(issue, 'pull_request'))


def resolution_days(issue):
    """Days from creation to the final recorded closure event."""
    created = timestamp(field(issue, 'created_date') or field(issue, 'created_at'))
    closed = timestamp(field(issue, 'closed_at'))
    if closed is None:
        state = field(issue, 'state', '')
        if str(getattr(state, 'value', state)).lower() != 'closed':
            return None
        closure_dates = [
            timestamp(field(event, 'event_date'))
            for event in (field(issue, 'events', []) or [])
            if field(event, 'event_type') == 'closed'
        ]
        closure_dates = [date for date in closure_dates if date is not None]
        closed = max(closure_dates, default=None)
    if created is None or closed is None or closed < created:
        return None
    return (closed - created).total_seconds() / 86400


def comment_count(issue):
    value = field(issue, 'comments', 0)
    if isinstance(value, bool):
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
