from datetime import datetime, timedelta

from app.tests.factories.event_factory import NOW

DEFAULT_EVENT_START = NOW + timedelta(days=14)


def build_session_payload(
    *,
    event_start: datetime = DEFAULT_EVENT_START,
    **overrides,
) -> dict:
    start = event_start + timedelta(hours=1)
    end = start + timedelta(hours=1)
    data = {
        "title": "Sesión principal",
        "description": "Contenido de la sesión con duración válida.",
        "speaker_name": "Juan Pérez",
        "room": "Sala A",
        "start_time": start.isoformat().replace("+00:00", "Z"),
        "end_time": end.isoformat().replace("+00:00", "Z"),
        "capacity": 40,
        "status": "scheduled",
    }
    data.update(overrides)
    return data
