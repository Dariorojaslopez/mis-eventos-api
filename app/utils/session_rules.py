from datetime import datetime

from app.models.event import Event, EventStatus
from app.models.session import Session, SessionStatus

ALLOWED_SESSION_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.SCHEDULED: frozenset(
        {SessionStatus.IN_PROGRESS, SessionStatus.FINISHED, SessionStatus.CANCELLED}
    ),
    SessionStatus.IN_PROGRESS: frozenset({SessionStatus.FINISHED, SessionStatus.CANCELLED}),
    SessionStatus.FINISHED: frozenset(),
    SessionStatus.CANCELLED: frozenset(),
}

IMMUTABLE_EVENT_STATUSES = frozenset({EventStatus.FINISHED, EventStatus.CANCELLED})
IMMUTABLE_SESSION_STATUSES = frozenset({SessionStatus.FINISHED, SessionStatus.CANCELLED})


def times_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    return start_a < end_b and start_b < end_a


def is_within_event_window(
    session_start: datetime,
    session_end: datetime,
    event: Event,
) -> bool:
    return session_start >= event.start_date and session_end <= event.end_date


def can_transition_session(current: SessionStatus, target: SessionStatus) -> bool:
    if current == target:
        return True
    return target in ALLOWED_SESSION_TRANSITIONS.get(current, frozenset())


def is_event_mutable(event: Event) -> bool:
    return event.status not in IMMUTABLE_EVENT_STATUSES


def is_session_mutable(session: Session) -> bool:
    return session.status not in IMMUTABLE_SESSION_STATUSES


def normalize_label(value: str) -> str:
    return value.strip().lower()
