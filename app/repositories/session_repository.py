from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session, SessionStatus
from app.repositories.base import BaseRepository
from app.utils.session_rules import normalize_label


class SessionRepository(BaseRepository[Session]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Session)

    async def get_by_id_with_event(self, session_id: UUID) -> Session | None:
        stmt = select(Session).options(selectinload(Session.event)).where(Session.id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_event(
        self,
        event_id: UUID,
        *,
        status: SessionStatus | None = None,
        room: str | None = None,
        speaker: str | None = None,
        include_cancelled: bool = False,
    ) -> list[Session]:
        filters = [Session.event_id == event_id]

        if not include_cancelled and status != SessionStatus.CANCELLED:
            filters.append(Session.status != SessionStatus.CANCELLED)

        if status is not None:
            filters.append(Session.status == status)

        if room:
            filters.append(func.lower(Session.room) == normalize_label(room))

        if speaker:
            filters.append(func.lower(Session.speaker_name) == normalize_label(speaker))

        stmt = select(Session).where(*filters).order_by(Session.start_time.asc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_speaker_conflict(
        self,
        *,
        event_id: UUID,
        speaker_name: str,
        start_time: datetime,
        end_time: datetime,
        exclude_session_id: UUID | None = None,
    ) -> Session | None:
        return await self._find_schedule_conflict(
            event_id=event_id,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=exclude_session_id,
            match_column=Session.speaker_name,
            match_value=speaker_name,
        )

    async def find_room_conflict(
        self,
        *,
        event_id: UUID,
        room: str,
        start_time: datetime,
        end_time: datetime,
        exclude_session_id: UUID | None = None,
    ) -> Session | None:
        return await self._find_schedule_conflict(
            event_id=event_id,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=exclude_session_id,
            match_column=Session.room,
            match_value=room,
        )

    async def _find_schedule_conflict(
        self,
        *,
        event_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_session_id: UUID | None,
        match_column,
        match_value: str,
    ) -> Session | None:
        overlap = and_(Session.start_time < end_time, Session.end_time > start_time)
        stmt = select(Session).where(
            Session.event_id == event_id,
            Session.status != SessionStatus.CANCELLED,
            func.lower(match_column) == normalize_label(match_value),
            overlap,
        )
        if exclude_session_id is not None:
            stmt = stmt.where(Session.id != exclude_session_id)

        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def update(self, session: Session) -> Session:
        await self._session.flush()
        await self._session.refresh(session)
        return session
