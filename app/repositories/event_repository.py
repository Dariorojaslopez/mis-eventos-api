from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, EventStatus
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Event)

    async def get_by_id_for_update(self, event_id: UUID) -> Event | None:
        stmt = select(Event).where(Event.id == event_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_organizer(self, event_id: UUID) -> Event | None:
        stmt = select(Event).options(selectinload(Event.organizer)).where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_events(
        self,
        *,
        page: int,
        limit: int,
        search: str | None,
        status: EventStatus | None,
        start_date_from: datetime | None,
        start_date_to: datetime | None,
        sort_desc: bool,
        exclude_cancelled: bool = False,
    ) -> tuple[list[Event], int]:
        filters = []

        if exclude_cancelled:
            filters.append(Event.status != EventStatus.CANCELLED)

        if status is not None:
            filters.append(Event.status == status)

        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    Event.title.ilike(pattern),
                    Event.description.ilike(pattern),
                )
            )

        if start_date_from is not None:
            filters.append(Event.start_date >= start_date_from)

        if start_date_to is not None:
            filters.append(Event.start_date <= start_date_to)

        count_stmt = select(func.count()).select_from(Event)
        if filters:
            count_stmt = count_stmt.where(*filters)

        total_result = await self._session.execute(count_stmt)
        total = int(total_result.scalar_one())

        order_clause = Event.start_date.desc() if sort_desc else Event.start_date.asc()
        offset = (page - 1) * limit

        items_stmt = (
            select(Event).where(*filters).order_by(order_clause).offset(offset).limit(limit)
        )
        items_result = await self._session.execute(items_stmt)
        items = list(items_result.scalars().all())

        return items, total

    async def update(self, event: Event) -> Event:
        await self._session.flush()
        await self._session.refresh(event)
        return event
