import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.event import _enum_values

if TYPE_CHECKING:
    from app.models.event import Event


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("end_time >= start_time", name="ck_sessions_end_after_start"),
        CheckConstraint("capacity > 0", name="ck_sessions_capacity_positive"),
        CheckConstraint(
            "available_slots >= 0 AND available_slots <= capacity",
            name="ck_sessions_available_slots_bounds",
        ),
        Index("ix_sessions_event_id", "event_id"),
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_start_time", "start_time"),
        Index("ix_sessions_event_speaker", "event_id", "speaker_name"),
        Index("ix_sessions_event_room", "event_id", "room"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    room: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        default=SessionStatus.SCHEDULED,
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped["Event"] = relationship("Event", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id} title={self.title!r} event_id={self.event_id}>"
