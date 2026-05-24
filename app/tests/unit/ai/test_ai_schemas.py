import pytest
from pydantic import ValidationError

from app.schemas.ai import GenerateEventDescriptionRequest

pytestmark = pytest.mark.unit


def test_generate_event_description_request_valid() -> None:
    payload = GenerateEventDescriptionRequest(
        title="FastAPI Summit 2026",
        location="Bogotá",
        event_type="Technology Conference",
        audience="Backend Developers",
    )
    assert payload.title == "FastAPI Summit 2026"


def test_generate_event_description_strips_and_sanitizes_html() -> None:
    payload = GenerateEventDescriptionRequest(
        title="  <b>Evento</b>  ",
        location="<script>x</script>Bogotá",
    )
    assert payload.title == "Evento"
    assert payload.location == "xBogotá"


def test_generate_event_description_title_too_short() -> None:
    with pytest.raises(ValidationError):
        GenerateEventDescriptionRequest(title="ab")


def test_generate_event_description_title_too_long() -> None:
    with pytest.raises(ValidationError):
        GenerateEventDescriptionRequest(title="x" * 201)
