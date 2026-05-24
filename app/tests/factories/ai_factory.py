def generate_event_description_payload(
    *,
    title: str = "FastAPI Summit 2026",
    location: str | None = "Bogotá",
    event_type: str | None = "Technology Conference",
    audience: str | None = "Backend Developers",
) -> dict[str, str | None]:
    return {
        "title": title,
        "location": location,
        "event_type": event_type,
        "audience": audience,
    }
