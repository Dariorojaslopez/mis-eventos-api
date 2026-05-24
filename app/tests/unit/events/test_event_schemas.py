import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from datetime import UTC, datetime, timedelta

from app.schemas.event import EventCreate

NOW = datetime.now(UTC)


def test_event_create_valid() -> None:
    event = EventCreate(
        title="Python Meetup",
        description="Comunidad local de desarrolladores Python.",
        location="Medellín",
        start_date=NOW,
        end_date=NOW + timedelta(hours=3),
        max_capacity=80,
    )
    assert event.max_capacity == 80


def test_event_create_invalid_date_range() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            title="Python Meetup",
            description="Comunidad local de desarrolladores Python.",
            location="Medellín",
            start_date=NOW + timedelta(days=1),
            end_date=NOW,
            max_capacity=80,
        )


def test_event_create_invalid_capacity() -> None:
    with pytest.raises(ValidationError):
        EventCreate(
            title="Python Meetup",
            description="Comunidad local de desarrolladores Python.",
            location="Medellín",
            start_date=NOW,
            end_date=NOW + timedelta(hours=1),
            max_capacity=0,
        )
