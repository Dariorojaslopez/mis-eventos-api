from app.providers.ai.base import AIProvider, EventDescriptionContext


class MockAIProvider(AIProvider):
    """Proveedor simulado: respuestas profesionales sin red ni API key."""

    @property
    def name(self) -> str:
        return "mock"

    async def generate_event_description(self, context: EventDescriptionContext) -> str:
        event_type = (context.event_type or "evento profesional").strip()
        location_clause = f" en {context.location.strip()}" if context.location else ""
        audience_clause = f", orientado a {context.audience.strip()}" if context.audience else ""

        return (
            f"{context.title.strip()} es un {event_type.lower()}{location_clause}"
            f"{audience_clause}. "
            "Este encuentro está diseñado para compartir conocimiento aplicable, "
            "fortalecer la colaboración entre profesionales y generar oportunidades "
            "de networking de alto valor. La agenda prioriza contenidos prácticos, "
            "casos reales y espacios de interacción que impulsen el aprendizaje "
            "y la innovación en el ecosistema tecnológico."
        )
