from datetime import UTC, datetime, timedelta

NOW = datetime.now(UTC)


def build_event_payload(**overrides) -> dict:
    start = NOW + timedelta(days=14)
    end = start + timedelta(hours=9)
    data = {
        "title": "Conferencia FastAPI",
        "description": "Taller avanzado de APIs async con FastAPI y SQLAlchemy.",
        "location": "Bogotá",
        "start_date": start.isoformat().replace("+00:00", "Z"),
        "end_date": end.isoformat().replace("+00:00", "Z"),
        "max_capacity": 100,
        "status": "draft",
    }
    data.update(overrides)
    return data
