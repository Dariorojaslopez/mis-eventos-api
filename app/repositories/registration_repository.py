from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.event_registration import EventRegistration, RegistrationStatus
from app.repositories.base import BaseRepository


class RegistrationRepository(BaseRepository[EventRegistration]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventRegistration)

    async def get_active_registration(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> EventRegistration | None:
        stmt = select(EventRegistration).where(
            EventRegistration.user_id == user_id,
            EventRegistration.event_id == event_id,
            EventRegistration.status == RegistrationStatus.REGISTERED,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_event(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> EventRegistration | None:
        stmt = select(EventRegistration).where(
            EventRegistration.user_id == user_id,
            EventRegistration.event_id == event_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attendees_by_event(self, event_id: UUID) -> list[EventRegistration]:
        stmt = (
            select(EventRegistration)
            .options(selectinload(EventRegistration.user))
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == RegistrationStatus.REGISTERED,
            )
            .order_by(EventRegistration.registered_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_registered_events_for_user(
        self,
        user_id: UUID,
    ) -> list[EventRegistration]:
        stmt = (
            select(EventRegistration)
            .options(
                selectinload(EventRegistration.event).selectinload(Event.organizer),
            )
            .where(
                EventRegistration.user_id == user_id,
                EventRegistration.status == RegistrationStatus.REGISTERED,
            )
            .order_by(EventRegistration.registered_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
