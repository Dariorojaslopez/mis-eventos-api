from app.models.event import Event, EventStatus

ALLOWED_STATUS_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DRAFT: frozenset({EventStatus.PUBLISHED, EventStatus.CANCELLED}),
    EventStatus.PUBLISHED: frozenset({EventStatus.CANCELLED, EventStatus.FINISHED}),
    EventStatus.CANCELLED: frozenset(),
    EventStatus.FINISHED: frozenset(),
}


def can_transition(current: EventStatus, target: EventStatus) -> bool:
    if current == target:
        return True
    return target in ALLOWED_STATUS_TRANSITIONS.get(current, frozenset())


def is_publishable(event: Event) -> bool:
    """Valida que un evento cumpla requisitos mínimos para publicarse."""
    now_fields_ok = (
        bool(event.title and event.title.strip())
        and bool(event.description and event.description.strip())
        and bool(event.location and event.location.strip())
        and event.end_date >= event.start_date
        and event.max_capacity > 0
        and event.available_slots >= 0
        and event.available_slots <= event.max_capacity
    )
    return now_fields_ok
