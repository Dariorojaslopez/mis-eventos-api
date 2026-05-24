from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.dependencies.events import EventServiceDep
from app.schemas.common import PaginatedResponse
from app.schemas.event import EventCreate, EventListParams, EventRead, EventUpdate

router = APIRouter()


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear evento",
    description="Crea un evento. El organizador es el usuario autenticado.",
)
async def create_event(
    data: EventCreate,
    service: EventServiceDep,
    current_user: CurrentUser,
) -> EventRead:
    return await service.create_event(data, current_user)


@router.get(
    "",
    response_model=PaginatedResponse[EventRead],
    summary="Listar eventos",
    description="Listado paginado con búsqueda, filtros por estado/fecha y orden por start_date.",
)
async def list_events(
    service: EventServiceDep,
    params: Annotated[EventListParams, Depends()],
) -> PaginatedResponse[EventRead]:
    return await service.list_events(params)


@router.get(
    "/{event_id}",
    response_model=EventRead,
    summary="Detalle de evento",
)
async def get_event(event_id: UUID, service: EventServiceDep) -> EventRead:
    return await service.get_event(event_id)


@router.put(
    "/{event_id}",
    response_model=EventRead,
    summary="Actualizar evento",
    description="Solo el organizador dueño o un administrador.",
)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    service: EventServiceDep,
    current_user: CurrentUser,
) -> EventRead:
    return await service.update_event(event_id, data, current_user)


@router.delete(
    "/{event_id}",
    response_model=EventRead,
    summary="Eliminar evento (cancelación lógica)",
    description="Marca el evento como CANCELLED. Solo organizador dueño o admin.",
)
async def delete_event(
    event_id: UUID,
    service: EventServiceDep,
    current_user: CurrentUser,
) -> EventRead:
    return await service.delete_event(event_id, current_user)
