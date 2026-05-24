from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.event import EventStatus
from app.models.event_registration import RegistrationStatus


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_id: UUID
    status: RegistrationStatus
    registered_at: datetime
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrganizerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr


class MyRegisteredEventRead(BaseModel):
    registration_id: UUID
    registration_status: RegistrationStatus
    registered_at: datetime
    cancelled_at: datetime | None

    event_id: UUID
    event_title: str
    event_description: str
    event_location: str
    event_start_date: datetime
    event_end_date: datetime
    event_status: EventStatus

    organizer: OrganizerSummary

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "registration_id": "550e8400-e29b-41d4-a716-446655440000",
                "registration_status": "registered",
                "registered_at": "2026-09-01T12:00:00Z",
                "cancelled_at": None,
                "event_id": "660e8400-e29b-41d4-a716-446655440001",
                "event_title": "Conferencia Python",
                "event_description": "Evento técnico anual",
                "event_location": "Bogotá",
                "event_start_date": "2026-09-15T09:00:00Z",
                "event_end_date": "2026-09-15T18:00:00Z",
                "event_status": "published",
                "organizer": {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "full_name": "Ana Organizadora",
                    "email": "ana@example.com",
                },
            }
        }
    )


class AttendeeRead(BaseModel):
    registration_id: UUID
    registration_status: RegistrationStatus
    registered_at: datetime
    cancelled_at: datetime | None

    user_id: UUID
    full_name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)
