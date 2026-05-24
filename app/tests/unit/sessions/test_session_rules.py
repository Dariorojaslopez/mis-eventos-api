import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.event import Event, EventStatus
from app.utils.session_rules import is_within_event_window, times_overlap

NOW = datetime.now(UTC)


def _event() -> Event:
    return Event(
        id=uuid4(),
        title="Event",
        description="Valid event description here.",
        location="Bogotá",
        start_date=NOW,
        end_date=NOW + timedelta(hours=9),
        max_capacity=100,
        available_slots=100,
        status=EventStatus.PUBLISHED,
        organizer_id=uuid4(),
    )


def test_times_overlap_true() -> None:
    a_start, a_end = NOW, NOW + timedelta(hours=1)
    b_start, b_end = NOW + timedelta(minutes=30), NOW + timedelta(hours=2)
    assert times_overlap(a_start, a_end, b_start, b_end)


def test_times_overlap_false() -> None:
    a_start, a_end = NOW, NOW + timedelta(hours=1)
    b_start, b_end = NOW + timedelta(hours=2), NOW + timedelta(hours=3)
    assert not times_overlap(a_start, a_end, b_start, b_end)


def test_session_within_event_window() -> None:
    event = _event()
    assert is_within_event_window(
        NOW + timedelta(hours=1),
        NOW + timedelta(hours=2),
        event,
    )


def test_session_outside_event_window() -> None:
    event = _event()
    assert not is_within_event_window(
        NOW + timedelta(hours=8),
        NOW + timedelta(hours=10),
        event,
    )
