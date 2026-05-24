from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class EventDescriptionContext(BaseModel):
    """Contexto de negocio para generar la descripción de un evento."""

    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    event_type: str | None = Field(default=None, max_length=100)
    audience: str | None = Field(default=None, max_length=200)


class AIProvider(ABC):
    """Contrato desacoplado para proveedores de generación con IA."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador del proveedor (mock, openai, ...)."""

    @abstractmethod
    async def generate_event_description(self, context: EventDescriptionContext) -> str:
        """Genera una descripción profesional para el evento."""
