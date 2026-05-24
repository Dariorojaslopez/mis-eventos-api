from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.event import Event, EventStatus
from app.models.event_registration import EventRegistration, RegistrationStatus
from app.models.user import UserRole
from app.repositories.event_repository import EventRepository
from app.repositories.registration_repository import RegistrationRepository
from app.schemas.registration import (
    AttendeeRead,
    MyRegisteredEventRead,
    OrganizerSummary,
    RegistrationRead,
)
from app.schemas.user import UserRead

logger = get_logger(__name__)


class RegistrationService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session
        self._registrations = RegistrationRepository(db_session)
        self._events = EventRepository(db_session)

    async def register_for_event(
        self,
        event_id: UUID,
        current_user: UserRead,
    ) -> RegistrationRead:
        async with self._db.begin_nested():
            event = await self._events.get_by_id_for_update(event_id)
            if event is None:
                raise NotFoundError("Event not found")

            await self._validate_registration_allowed(event, current_user)

            existing_active = await self._registrations.get_active_registration(
                current_user.id,
                event_id,
            )
            if existing_active is not None:
                self._log_registration(
                    "registration_already_active",
                    user_id=current_user.id,
                    event_id=event_id,
                    registration_id=existing_active.id,
                )
                return RegistrationRead.model_validate(existing_active)

            if event.available_slots <= 0:
                self._log_registration(
                    "registration_denied_capacity",
                    user_id=current_user.id,
                    event_id=event_id,
                )
                raise AppException(
                    "No available slots for this event",
                    code="registration_denied_capacity",
                    status_code=409,
                )

            previous = await self._registrations.get_by_user_and_event(
                current_user.id,
                event_id,
            )
            now = datetime.now(UTC)

            if previous is not None and previous.status == RegistrationStatus.CANCELLED:
                registration = previous
                registration.status = RegistrationStatus.REGISTERED
                registration.registered_at = now
                registration.cancelled_at = None
                await self._db.flush()
                await self._db.refresh(registration)
            else:
                registration = EventRegistration(
                    user_id=current_user.id,
                    event_id=event_id,
                    status=RegistrationStatus.REGISTERED,
                    registered_at=now,
                )
                registration = await self._registrations.add(registration)

            event.available_slots -= 1
            await self._db.flush()

        self._log_registration(
            "registration_created",
            user_id=current_user.id,
            event_id=event_id,
            registration_id=registration.id,
        )
        return RegistrationRead.model_validate(registration)

    async def cancel_registration(
        self,
        event_id: UUID,
        current_user: UserRead,
    ) -> RegistrationRead:
        async with self._db.begin_nested():
            event = await self._events.get_by_id_for_update(event_id)
            if event is None:
                raise NotFoundError("Event not found")

            registration = await self._registrations.get_active_registration(
                current_user.id,
                event_id,
            )
            if registration is None:
                raise NotFoundError("Active registration not found for this event")

            now = datetime.now(UTC)
            registration.status = RegistrationStatus.CANCELLED
            registration.cancelled_at = now
            event.available_slots += 1
            await self._db.flush()
            await self._db.refresh(registration)

        self._log_registration(
            "registration_cancelled",
            user_id=current_user.id,
            event_id=event_id,
            registration_id=registration.id,
        )
        return RegistrationRead.model_validate(registration)

    async def list_my_registered_events(
        self,
        current_user: UserRead,
    ) -> list[MyRegisteredEventRead]:
        registrations = await self._registrations.list_registered_events_for_user(
            current_user.id,
        )
        return [self._to_my_registered_event(item) for item in registrations]

    async def list_event_attendees(
        self,
        event_id: UUID,
        current_user: UserRead,
    ) -> list[AttendeeRead]:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")

        self._ensure_can_view_attendees(event, current_user)

        attendees = await self._registrations.list_attendees_by_event(event_id)
        return [self._to_attendee_read(item) for item in attendees]

    async def _validate_registration_allowed(
        self,
        event: Event,
        current_user: UserRead,
    ) -> None:
        if event.status != EventStatus.PUBLISHED:
            raise AppException(
                "Only published events accept registrations",
                code="event_not_registerable",
                status_code=409,
            )

        if event.organizer_id == current_user.id:
            raise AppException(
                "Organizers cannot register for their own events",
                code="organizer_self_registration",
                status_code=409,
            )

    def _ensure_can_view_attendees(self, event: Event, current_user: UserRead) -> None:
        is_owner = event.organizer_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_owner or is_admin):
            raise ForbiddenError("You are not allowed to view attendees for this event")

    def _to_my_registered_event(
        self,
        registration: EventRegistration,
    ) -> MyRegisteredEventRead:
        event = registration.event
        organizer = event.organizer
        return MyRegisteredEventRead(
            registration_id=registration.id,
            registration_status=registration.status,
            registered_at=registration.registered_at,
            cancelled_at=registration.cancelled_at,
            event_id=event.id,
            event_title=event.title,
            event_description=event.description,
            event_location=event.location,
            event_start_date=event.start_date,
            event_end_date=event.end_date,
            event_status=event.status,
            organizer=OrganizerSummary.model_validate(organizer),
        )

    def _to_attendee_read(self, registration: EventRegistration) -> AttendeeRead:
        user = registration.user
        return AttendeeRead(
            registration_id=registration.id,
            registration_status=registration.status,
            registered_at=registration.registered_at,
            cancelled_at=registration.cancelled_at,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
        )

    def _log_registration(self, event_name: str, **kwargs: object) -> None:
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        logger.info(event_name, request_id=request_id, **{k: str(v) for k, v in kwargs.items()})
