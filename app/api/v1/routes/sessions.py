from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.dependencies.sessions import SessionServiceDep
from app.schemas.session import SessionRead, SessionUpdate

router = APIRouter()


@router.get(
    "/{session_id}",
    response_model=SessionRead,
    summary="Detalle de sesión",
)
async def get_session(session_id: UUID, service: SessionServiceDep) -> SessionRead:
    return await service.get_session(session_id)


@router.put(
    "/{session_id}",
    response_model=SessionRead,
    summary="Actualizar sesión",
    description="Solo organizador del evento o administrador.",
)
async def update_session(
    session_id: UUID,
    data: SessionUpdate,
    service: SessionServiceDep,
    current_user: CurrentUser,
) -> SessionRead:
    return await service.update_session(session_id, data, current_user)


@router.delete(
    "/{session_id}",
    response_model=SessionRead,
    summary="Eliminar sesión (cancelación lógica)",
    description="Marca la sesión como cancelled.",
)
async def delete_session(
    session_id: UUID,
    service: SessionServiceDep,
    current_user: CurrentUser,
) -> SessionRead:
    return await service.delete_session(session_id, current_user)
