from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.text_sanitize import sanitize_plain_text

TITLE_MIN = 3
TITLE_MAX = 200
FIELD_MAX = 200
EVENT_TYPE_MAX = 100


class GenerateEventDescriptionRequest(BaseModel):
    title: str = Field(
        min_length=TITLE_MIN,
        max_length=TITLE_MAX,
        description="Título del evento",
        examples=["FastAPI Summit 2026"],
    )
    location: str | None = Field(
        default=None,
        max_length=FIELD_MAX,
        description="Ciudad o sede del evento",
        examples=["Bogotá"],
    )
    event_type: str | None = Field(
        default=None,
        max_length=EVENT_TYPE_MAX,
        description="Tipo o categoría del evento",
        examples=["Technology Conference"],
    )
    audience: str | None = Field(
        default=None,
        max_length=FIELD_MAX,
        description="Perfil de la audiencia objetivo",
        examples=["Backend Developers"],
    )

    @field_validator("title", "location", "event_type", "audience", mode="before")
    @classmethod
    def sanitize_optional_strings(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        return sanitize_plain_text(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "FastAPI Summit 2026",
                "location": "Bogotá",
                "event_type": "Technology Conference",
                "audience": "Backend Developers",
            }
        }
    )


class GenerateEventDescriptionResponse(BaseModel):
    title: str = Field(description="Título del evento procesado")
    generated_description: str = Field(
        description="Descripción profesional generada por IA",
        min_length=20,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "FastAPI Summit 2026",
                "generated_description": (
                    "Evento especializado en arquitectura moderna con FastAPI, "
                    "diseñado para desarrolladores backend que buscan escalar APIs "
                    "async de forma enterprise."
                ),
            }
        }
    )
