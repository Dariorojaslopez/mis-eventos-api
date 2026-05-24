from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.event import Event, EventStatus
from app.models.user import UserRole
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.event import (
    EventCreate,
    EventListParams,
    EventRead,
    EventSortOrder,
    EventUpdate,
)
from app.schemas.user import UserRead
from app.utils.event_rules import can_transition, is_publishable

logger = get_logger(__name__)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._users = UserRepository(session)

    async def create_event(self, data: EventCreate, current_user: UserRead) -> EventRead:
        await self._ensure_organizer_exists(current_user.id)

        if data.status not in {EventStatus.DRAFT, EventStatus.PUBLISHED}:
            raise AppException(
                "New events can only be created as draft or published",
                code="invalid_initial_status",
            )

        event = Event(
            title=data.title.strip(),
            description=data.description.strip(),
            location=data.location.strip(),
            start_date=data.start_date,
            end_date=data.end_date,
            max_capacity=data.max_capacity,
            available_slots=data.max_capacity,
            status=data.status,
            organizer_id=current_user.id,
        )

        if event.status == EventStatus.PUBLISHED and not is_publishable(event):
            raise AppException(
                "Event cannot be published: incomplete or invalid data",
                code="invalid_publish",
            )

        created = await self._events.add(event)
        self._log_event_action("event_created", event_id=created.id, user_id=current_user.id)
        return EventRead.model_validate(created)

    async def list_events(self, params: EventListParams) -> PaginatedResponse[EventRead]:
        exclude_cancelled = params.status is None
        items, total = await self._events.list_events(
            page=params.page,
            limit=params.limit,
            search=params.search,
            status=params.status,
            start_date_from=params.start_date_from,
            start_date_to=params.start_date_to,
            sort_desc=params.sort == EventSortOrder.DESC,
            exclude_cancelled=exclude_cancelled,
        )
        return PaginatedResponse.build(
            items=[EventRead.model_validate(item) for item in items],
            total=total,
            page=params.page,
            limit=params.limit,
        )

    async def get_event(self, event_id: UUID) -> EventRead:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")
        return EventRead.model_validate(event)

    async def update_event(
        self,
        event_id: UUID,
        data: EventUpdate,
        current_user: UserRead,
    ) -> EventRead:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")

        self._ensure_can_manage(event, current_user)

        if event.status == EventStatus.FINISHED:
            raise AppException(
                "Finished events cannot be modified",
                code="event_finished",
                status_code=409,
            )

        update_data = data.model_dump(exclude_unset=True)
        new_status = update_data.pop("status", None)

        for field, value in update_data.items():
            setattr(event, field, value)

        if "max_capacity" in update_data and "available_slots" not in update_data:
            event.available_slots = min(event.available_slots, event.max_capacity)

        if "available_slots" in update_data and event.available_slots > event.max_capacity:
            raise AppException(
                "available_slots cannot exceed max_capacity",
                code="invalid_slots",
            )

        if event.end_date < event.start_date:
            raise AppException(
                "end_date must be greater than or equal to start_date",
                code="invalid_date_range",
            )

        if new_status is not None:
            await self._apply_status_transition(event, new_status)

        if event.status == EventStatus.PUBLISHED and not is_publishable(event):
            raise AppException(
                "Event cannot be published: incomplete or invalid data",
                code="invalid_publish",
            )

        updated = await self._events.update(event)
        self._log_event_action("event_updated", event_id=updated.id, user_id=current_user.id)
        return EventRead.model_validate(updated)

    async def delete_event(self, event_id: UUID, current_user: UserRead) -> EventRead:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")

        self._ensure_can_manage(event, current_user)

        if event.status == EventStatus.FINISHED:
            raise AppException(
                "Finished events cannot be deleted",
                code="event_finished",
                status_code=409,
            )

        if event.status != EventStatus.CANCELLED:
            await self._apply_status_transition(event, EventStatus.CANCELLED)

        updated = await self._events.update(event)
        self._log_event_action("event_deleted", event_id=updated.id, user_id=current_user.id)
        return EventRead.model_validate(updated)

    async def _ensure_organizer_exists(self, user_id: UUID) -> None:
        user = await self._users.get_active_by_id(user_id)
        if user is None:
            raise NotFoundError("Organizer user not found or inactive")

    def _ensure_can_manage(self, event: Event, current_user: UserRead) -> None:
        is_owner = event.organizer_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_owner or is_admin):
            raise ForbiddenError("You are not allowed to manage this event")

    async def _apply_status_transition(self, event: Event, target: EventStatus) -> None:
        if not can_transition(event.status, target):
            raise AppException(
                f"Invalid status transition from '{event.status.value}' to '{target.value}'",
                code="invalid_status_transition",
                details={
                    "current_status": event.status.value,
                    "target_status": target.value,
                },
            )

        if target == EventStatus.PUBLISHED and not is_publishable(event):
            raise AppException(
                "Event cannot be published: incomplete or invalid data",
                code="invalid_publish",
            )

        event.status = target

    def _log_event_action(self, event_name: str, *, event_id: UUID, user_id: UUID) -> None:
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        logger.info(
            event_name,
            event_id=str(event_id),
            user_id=str(user_id),
            request_id=request_id,
        )
