from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.session import SessionStatus

TITLE_MIN = 3
TITLE_MAX = 255
DESCRIPTION_MIN = 10
SPEAKER_MIN = 2
ROOM_MIN = 2
ROOM_MAX = 255


class SessionBase(BaseModel):
    title: str = Field(min_length=TITLE_MIN, max_length=TITLE_MAX)
    description: str = Field(min_length=DESCRIPTION_MIN)
    speaker_name: str = Field(min_length=SPEAKER_MIN, max_length=255)
    room: str = Field(min_length=ROOM_MIN, max_length=ROOM_MAX)
    start_time: datetime
    end_time: datetime
    capacity: int = Field(gt=0, le=50_000)

    @field_validator("title", "speaker_name", "room")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_time_range(self) -> "SessionBase":
        if self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class SessionCreate(SessionBase):
    status: SessionStatus = SessionStatus.SCHEDULED

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Introducción a FastAPI",
                "description": "Sesión introductoria sobre APIs async con FastAPI.",
                "speaker_name": "Juan Pérez",
                "room": "Sala A",
                "start_time": "2026-09-15T10:00:00Z",
                "end_time": "2026-09-15T11:00:00Z",
                "capacity": 40,
                "status": "scheduled",
            }
        }
    )


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=TITLE_MIN, max_length=TITLE_MAX)
    description: str | None = Field(default=None, min_length=DESCRIPTION_MIN)
    speaker_name: str | None = Field(default=None, min_length=SPEAKER_MIN, max_length=255)
    room: str | None = Field(default=None, min_length=ROOM_MIN, max_length=ROOM_MAX)
    start_time: datetime | None = None
    end_time: datetime | None = None
    capacity: int | None = Field(default=None, gt=0, le=50_000)
    available_slots: int | None = Field(default=None, ge=0)
    status: SessionStatus | None = None

    @field_validator("title", "speaker_name", "room")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_partial_times(self) -> "SessionUpdate":
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return self


class SessionRead(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    available_slots: int
    status: SessionStatus
    event_id: UUID
    created_at: datetime
    updated_at: datetime


class SessionListParams(BaseModel):
    status: SessionStatus | None = None
    room: str | None = Field(default=None, max_length=ROOM_MAX)
    speaker: str | None = Field(default=None, max_length=255)
    include_cancelled: bool = False

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | SessionStatus | None) -> SessionStatus | None:
        if value is None or isinstance(value, SessionStatus):
            return value
        return SessionStatus(str(value).strip().lower())

    @field_validator("room", "speaker")
    @classmethod
    def strip_filters(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
