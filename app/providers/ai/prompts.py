from app.providers.ai.base import EventDescriptionContext


def build_event_description_system_prompt() -> str:
    return (
        "Eres un redactor corporativo especializado en eventos profesionales. "
        "Redactas descripciones claras, persuasivas y en tono formal para convocatorias. "
        "Escribe en español neutro, entre 80 y 180 palabras, sin viñetas ni emojis. "
        "Destaca valor para la audiencia, objetivos del evento y experiencia esperada."
    )


def build_event_description_user_prompt(context: EventDescriptionContext) -> str:
    lines = [f"Título del evento: {context.title}"]
    if context.event_type:
        lines.append(f"Tipo de evento: {context.event_type}")
    if context.location:
        lines.append(f"Ubicación: {context.location}")
    if context.audience:
        lines.append(f"Audiencia objetivo: {context.audience}")
    lines.append("Genera una descripción profesional lista para publicar en la ficha del evento.")
    return "\n".join(lines)


def build_event_description_messages(
    context: EventDescriptionContext,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": build_event_description_system_prompt()},
        {"role": "user", "content": build_event_description_user_prompt(context)},
    ]
