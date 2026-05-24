import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.event import _enum_values

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class RegistrationStatus(StrEnum):
    REGISTERED = "registered"
    CANCELLED = "cancelled"
    WAITLIST = "waitlist"


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (
        Index("ix_event_registrations_user_id", "user_id"),
        Index("ix_event_registrations_event_id", "event_id"),
        Index("ix_event_registrations_status", "status"),
        Index(
            "uq_event_registrations_user_event_active",
            "user_id",
            "event_id",
            unique=True,
            postgresql_where=text("status = 'registered'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(
            RegistrationStatus,
            name="registration_status",
            native_enum=True,
            values_callable=_enum_values,
        ),
        default=RegistrationStatus.REGISTERED,
        nullable=False,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    user: Mapped["User"] = relationship("User", back_populates="event_registrations")
    event: Mapped["Event"] = relationship("Event", back_populates="registrations")

    def __repr__(self) -> str:
        return (
            f"<EventRegistration id={self.id} user_id={self.user_id} "
            f"event_id={self.event_id} status={self.status}>"
        )
