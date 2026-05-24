from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.event import EventStatus

TITLE_MIN = 3
TITLE_MAX = 255
DESCRIPTION_MIN = 10
LOCATION_MIN = 3
LOCATION_MAX = 500


class EventSortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class EventBase(BaseModel):
    title: str = Field(min_length=TITLE_MIN, max_length=TITLE_MAX)
    description: str = Field(min_length=DESCRIPTION_MIN)
    location: str = Field(min_length=LOCATION_MIN, max_length=LOCATION_MAX)
    start_date: datetime
    end_date: datetime
    max_capacity: int = Field(gt=0, le=100_000)

    @field_validator("title", "location")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_date_range(self) -> "EventBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class EventCreate(EventBase):
    status: EventStatus = EventStatus.DRAFT

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Conferencia Python 2026",
                "description": "Evento técnico sobre Python, FastAPI y arquitectura async.",
                "location": "Bogotá — Centro de Convenciones",
                "start_date": "2026-09-15T09:00:00Z",
                "end_date": "2026-09-15T18:00:00Z",
                "max_capacity": 120,
                "status": "draft",
            }
        }
    )


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=TITLE_MIN, max_length=TITLE_MAX)
    description: str | None = Field(default=None, min_length=DESCRIPTION_MIN)
    location: str | None = Field(default=None, min_length=LOCATION_MIN, max_length=LOCATION_MAX)
    start_date: datetime | None = None
    end_date: datetime | None = None
    max_capacity: int | None = Field(default=None, gt=0, le=100_000)
    available_slots: int | None = Field(default=None, ge=0)
    status: EventStatus | None = None

    @field_validator("title", "location")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_partial_dates(self) -> "EventUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    available_slots: int
    status: EventStatus
    organizer_id: UUID
    created_at: datetime
    updated_at: datetime


class EventListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)
    search: str | None = Field(default=None, max_length=255)
    status: EventStatus | None = None
    start_date_from: datetime | None = None
    start_date_to: datetime | None = None
    sort: EventSortOrder = EventSortOrder.ASC

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | EventStatus | None) -> EventStatus | None:
        if value is None or isinstance(value, EventStatus):
            return value
        normalized = str(value).strip().lower()
        return EventStatus(normalized)

    @model_validator(mode="after")
    def validate_date_filters(self) -> "EventListParams":
        if (
            self.start_date_from
            and self.start_date_to
            and self.start_date_to < self.start_date_from
        ):
            raise ValueError("start_date_to must be greater than or equal to start_date_from")
        return self
