import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.event import Event, EventStatus
from app.utils.event_rules import can_transition, is_publishable

NOW = datetime.now(UTC)
LATER = NOW + timedelta(hours=2)


def _sample_event(**overrides) -> Event:
    data = {
        "title": "Test Event",
        "description": "A valid description for the event.",
        "location": "Bogotá",
        "start_date": NOW,
        "end_date": LATER,
        "max_capacity": 50,
        "available_slots": 50,
        "status": EventStatus.DRAFT,
        "organizer_id": uuid4(),
    }
    data.update(overrides)
    return Event(**data)


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        (EventStatus.DRAFT, EventStatus.PUBLISHED, True),
        (EventStatus.DRAFT, EventStatus.CANCELLED, True),
        (EventStatus.DRAFT, EventStatus.FINISHED, False),
        (EventStatus.PUBLISHED, EventStatus.FINISHED, True),
        (EventStatus.PUBLISHED, EventStatus.DRAFT, False),
        (EventStatus.FINISHED, EventStatus.CANCELLED, False),
        (EventStatus.CANCELLED, EventStatus.DRAFT, False),
    ],
)
def test_status_transitions(current: EventStatus, target: EventStatus, expected: bool) -> None:
    assert can_transition(current, target) is expected


def test_is_publishable_valid_event() -> None:
    assert is_publishable(_sample_event()) is True


def test_is_publishable_invalid_dates() -> None:
    event = _sample_event(start_date=LATER, end_date=NOW)
    assert is_publishable(event) is False
