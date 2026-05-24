from fastapi import APIRouter, Request, status

from app.api.v1.dependencies.ai import AIServiceDep
from app.api.v1.dependencies.auth import CurrentUser
from app.schemas.ai import GenerateEventDescriptionRequest, GenerateEventDescriptionResponse

router = APIRouter()


@router.post(
    "/generate-event-description",
    response_model=GenerateEventDescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generar descripción de evento con IA",
    description=(
        "Genera una descripción profesional a partir del título y contexto del evento. "
        "Usa el proveedor configurado (`AI_PROVIDER`) con fallback automático a mock."
    ),
    responses={
        200: {"description": "Descripción generada correctamente"},
        401: {"description": "No autenticado"},
        422: {"description": "Payload inválido"},
        429: {"description": "Límite de solicitudes IA excedido"},
        502: {"description": "Fallo al generar contenido"},
    },
)
async def generate_event_description(
    data: GenerateEventDescriptionRequest,
    service: AIServiceDep,
    current_user: CurrentUser,
    request: Request,
) -> GenerateEventDescriptionResponse:
    request_id = getattr(request.state, "request_id", None)
    return await service.generate_event_description(
        data,
        user_id=current_user.id,
        request_id=request_id,
    )
