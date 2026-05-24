from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.dependencies.sessions import SessionServiceDep
from app.schemas.session import SessionCreate, SessionListParams, SessionRead

router = APIRouter()


@router.post(
    "/{event_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear sesión en un evento",
    description="Solo el organizador del evento o un administrador.",
)
async def create_session(
    event_id: UUID,
    data: SessionCreate,
    service: SessionServiceDep,
    current_user: CurrentUser,
) -> SessionRead:
    return await service.create_session(event_id, data, current_user)


@router.get(
    "/{event_id}/sessions",
    response_model=list[SessionRead],
    summary="Listar sesiones de un evento",
)
async def list_event_sessions(
    event_id: UUID,
    service: SessionServiceDep,
    params: Annotated[SessionListParams, Depends()],
) -> list[SessionRead]:
    return await service.list_sessions_by_event(event_id, params)
