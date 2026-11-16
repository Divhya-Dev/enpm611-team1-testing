"""
Runtime data model for GitHub issues.
"""

from typing import List
from enum import Enum
from datetime import datetime
from dateutil import parser


class State(str, Enum):
    """Whether an issue is open or closed."""
    open = 'open'
    closed = 'closed'


class Event:
    def __init__(self, jobj: any):
        self.event_type: str = None
        self.author: str = None
        self.event_date: datetime = None
        self.label: str = None
        self.comment: str = None
        if jobj is not None:
            self.from_json(jobj)

    def from_json(self, jobj: any):
        self.event_type = jobj.get('event_type')
        self.author = jobj.get('author')
        try:
            value = jobj.get('event_date')
            self.event_date = parser.parse(value) if value else None
        except (TypeError, ValueError):
            self.event_date = None
        self.label = jobj.get('label')
        self.comment = jobj.get('comment')


class Issue:
    def __init__(self, jobj: any = None):
        self.url: str = None
        self.creator: str = None
        self.labels: List[str] = []
        self.state: State = None
        self.assignees: List[str] = []
        self.title: str = None
        self.text: str = None
        self.number: int = -1
        self.created_date: datetime = None
        self.updated_date: datetime = None
        self.closed_at: datetime = None
        self.closed_date: datetime = None
        self.timeline_url: str = None
        self.events: List[Event] = []
        if jobj is not None:
            self.from_json(jobj)

    def from_json(self, jobj: any):
        self.url = jobj.get('url')
        self.creator = jobj.get('creator')
        self.labels = jobj.get('labels', [])
        state = jobj.get('state')
        self.state = State[state] if state in State.__members__ else None
        self.assignees = jobj.get('assignees', [])
        self.title = jobj.get('title')
        self.text = jobj.get('text')

        try:
            self.number = int(jobj.get('number', '-1'))
        except (TypeError, ValueError):
            pass

        try:
            created = jobj.get('created_date') or jobj.get('created_at')
            self.created_date = parser.parse(created) if created else None
        except (TypeError, ValueError):
            self.created_date = None

        try:
            updated = jobj.get('updated_date') or jobj.get('updated_at')
            self.updated_date = parser.parse(updated) if updated else None
        except (TypeError, ValueError):
            self.updated_date = None

        # The shared resolution_days helper reads the closed_at attribute.
        try:
            closed = jobj.get('closed_at') or jobj.get('closed_date')
            self.closed_at = parser.parse(closed) if closed else None
            self.closed_date = self.closed_at
        except (TypeError, ValueError):
            self.closed_at = None
            self.closed_date = None

        self.timeline_url = jobj.get('timeline_url')
        self.events = [Event(event) for event in jobj.get('events', [])]
