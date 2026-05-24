from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.event import Event, EventStatus
from app.models.session import Session, SessionStatus
from app.models.user import UserRole
from app.repositories.event_repository import EventRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import SessionCreate, SessionListParams, SessionRead, SessionUpdate
from app.schemas.user import UserRead
from app.utils.session_rules import (
    can_transition_session,
    is_event_mutable,
    is_session_mutable,
    is_within_event_window,
)

logger = get_logger(__name__)


class SessionService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session
        self._sessions = SessionRepository(db_session)
        self._events = EventRepository(db_session)

    async def create_session(
        self,
        event_id: UUID,
        data: SessionCreate,
        current_user: UserRead,
    ) -> SessionRead:
        event = await self._get_mutable_event(event_id)
        self._ensure_can_manage_event(event, current_user)

        if data.status not in {SessionStatus.SCHEDULED}:
            raise AppException(
                "New sessions can only be created with status 'scheduled'",
                code="invalid_initial_status",
            )

        session = Session(
            title=data.title.strip(),
            description=data.description.strip(),
            speaker_name=data.speaker_name.strip(),
            room=data.room.strip(),
            start_time=data.start_time,
            end_time=data.end_time,
            capacity=data.capacity,
            available_slots=data.capacity,
            status=data.status,
            event_id=event.id,
        )

        await self._validate_session_rules(session, event, user_id=current_user.id)
        created = await self._sessions.add(session)
        self._log_session_action(
            "session_created",
            session_id=created.id,
            event_id=event.id,
            user_id=current_user.id,
        )
        return SessionRead.model_validate(created)

    async def list_sessions_by_event(
        self,
        event_id: UUID,
        params: SessionListParams,
    ) -> list[SessionRead]:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")

        sessions = await self._sessions.list_by_event(
            event_id,
            status=params.status,
            room=params.room,
            speaker=params.speaker,
            include_cancelled=params.include_cancelled,
        )
        return [SessionRead.model_validate(item) for item in sessions]

    async def get_session(self, session_id: UUID) -> SessionRead:
        session = await self._sessions.get_by_id(session_id)
        if session is None or session.status == SessionStatus.CANCELLED:
            raise NotFoundError("Session not found")
        return SessionRead.model_validate(session)

    async def update_session(
        self,
        session_id: UUID,
        data: SessionUpdate,
        current_user: UserRead,
    ) -> SessionRead:
        session = await self._sessions.get_by_id_with_event(session_id)
        if session is None or session.status == SessionStatus.CANCELLED:
            raise NotFoundError("Session not found")

        event = session.event
        if event is None:
            raise NotFoundError("Event not found")

        self._ensure_event_allows_changes(event)
        self._ensure_can_manage_event(event, current_user)

        if not is_session_mutable(session):
            raise AppException(
                "Finished sessions cannot be modified",
                code="session_finished",
                status_code=409,
            )

        update_data = data.model_dump(exclude_unset=True)
        new_status = update_data.pop("status", None)

        for field, value in update_data.items():
            setattr(session, field, value)

        if "capacity" in update_data and "available_slots" not in update_data:
            session.available_slots = min(session.available_slots, session.capacity)

        if session.available_slots > session.capacity:
            raise AppException(
                "available_slots cannot exceed capacity",
                code="invalid_slots",
            )

        if session.end_time < session.start_time:
            raise AppException(
                "end_time must be greater than or equal to start_time",
                code="invalid_time_range",
            )

        if new_status is not None:
            self._apply_status_transition(session, new_status)

        await self._validate_session_rules(
            session,
            event,
            exclude_session_id=session.id,
            user_id=current_user.id,
        )

        updated = await self._sessions.update(session)
        self._log_session_action(
            "session_updated",
            session_id=updated.id,
            event_id=event.id,
            user_id=current_user.id,
        )
        return SessionRead.model_validate(updated)

    async def delete_session(self, session_id: UUID, current_user: UserRead) -> SessionRead:
        session = await self._sessions.get_by_id_with_event(session_id)
        if session is None or session.status == SessionStatus.CANCELLED:
            raise NotFoundError("Session not found")

        event = session.event
        if event is None:
            raise NotFoundError("Event not found")

        self._ensure_event_allows_changes(event)
        self._ensure_can_manage_event(event, current_user)

        if session.status == SessionStatus.FINISHED:
            raise AppException(
                "Finished sessions cannot be deleted",
                code="session_finished",
                status_code=409,
            )

        if session.status != SessionStatus.CANCELLED:
            self._apply_status_transition(session, SessionStatus.CANCELLED)

        updated = await self._sessions.update(session)
        self._log_session_action(
            "session_deleted",
            session_id=updated.id,
            event_id=event.id,
            user_id=current_user.id,
        )
        return SessionRead.model_validate(updated)

    async def _get_mutable_event(self, event_id: UUID) -> Event:
        event = await self._events.get_by_id(event_id)
        if event is None or event.status == EventStatus.CANCELLED:
            raise NotFoundError("Event not found")
        self._ensure_event_allows_changes(event)
        return event

    def _ensure_event_allows_changes(self, event: Event) -> None:
        if not is_event_mutable(event):
            raise AppException(
                "Sessions cannot be modified on finished or cancelled events",
                code="event_not_mutable",
                status_code=409,
            )

    def _ensure_can_manage_event(self, event: Event, current_user: UserRead) -> None:
        is_owner = event.organizer_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        if not (is_owner or is_admin):
            raise ForbiddenError("You are not allowed to manage sessions for this event")

    async def _validate_session_rules(
        self,
        session: Session,
        event: Event,
        *,
        exclude_session_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> None:
        if not is_within_event_window(session.start_time, session.end_time, event):
            raise AppException(
                "Session schedule must be within the event time window",
                code="session_outside_event_window",
                details={
                    "event_start": event.start_date.isoformat(),
                    "event_end": event.end_date.isoformat(),
                    "session_start": session.start_time.isoformat(),
                    "session_end": session.end_time.isoformat(),
                },
            )

        speaker_conflict = await self._sessions.find_speaker_conflict(
            event_id=event.id,
            speaker_name=session.speaker_name,
            start_time=session.start_time,
            end_time=session.end_time,
            exclude_session_id=exclude_session_id,
        )
        if speaker_conflict is not None:
            self._log_session_action(
                "session_conflict_detected",
                session_id=session.id,
                event_id=event.id,
                user_id=str(user_id) if user_id else None,
                conflict_type="speaker",
                conflicting_session_id=str(speaker_conflict.id),
            )
            raise AppException(
                "Speaker schedule conflict detected for this event",
                code="session_speaker_conflict",
                status_code=409,
                details={
                    "speaker_name": session.speaker_name,
                    "conflicting_session_id": str(speaker_conflict.id),
                },
            )

        room_conflict = await self._sessions.find_room_conflict(
            event_id=event.id,
            room=session.room,
            start_time=session.start_time,
            end_time=session.end_time,
            exclude_session_id=exclude_session_id,
        )
        if room_conflict is not None:
            self._log_session_action(
                "session_conflict_detected",
                session_id=session.id,
                event_id=event.id,
                user_id=str(user_id) if user_id else None,
                conflict_type="room",
                conflicting_session_id=str(room_conflict.id),
            )
            raise AppException(
                "Room schedule conflict detected for this event",
                code="session_room_conflict",
                status_code=409,
                details={
                    "room": session.room,
                    "conflicting_session_id": str(room_conflict.id),
                },
            )

    def _apply_status_transition(self, session: Session, target: SessionStatus) -> None:
        if not can_transition_session(session.status, target):
            raise AppException(
                f"Invalid status transition from '{session.status.value}' to '{target.value}'",
                code="invalid_status_transition",
                details={
                    "current_status": session.status.value,
                    "target_status": target.value,
                },
            )
        session.status = target

    def _log_session_action(self, event_name: str, **kwargs: object) -> None:
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        logger.info(event_name, request_id=request_id, **kwargs)
