import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from datetime import UTC, datetime, timedelta

from app.schemas.session import SessionCreate, SessionListParams

NOW = datetime.now(UTC)


def test_session_create_valid() -> None:
    session = SessionCreate(
        title="Taller FastAPI",
        description="Sesión práctica de APIs async.",
        speaker_name="Ana López",
        room="Sala B",
        start_time=NOW,
        end_time=NOW + timedelta(hours=1),
        capacity=30,
    )
    assert session.capacity == 30


def test_session_create_invalid_time_range() -> None:
    with pytest.raises(ValidationError):
        SessionCreate(
            title="Taller FastAPI",
            description="Sesión práctica de APIs async.",
            speaker_name="Ana López",
            room="Sala B",
            start_time=NOW + timedelta(hours=2),
            end_time=NOW,
            capacity=30,
        )


def test_session_list_params_normalizes_status() -> None:
    params = SessionListParams(status="SCHEDULED")
    assert params.status.value == "scheduled"
