from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.dependencies.registrations import RegistrationServiceDep
from app.schemas.registration import AttendeeRead, RegistrationRead

router = APIRouter()


@router.post(
    "/{event_id}/register",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrarse a un evento",
    description="Inscribe al usuario autenticado si hay cupo disponible.",
)
async def register_for_event(
    event_id: UUID,
    service: RegistrationServiceDep,
    current_user: CurrentUser,
) -> RegistrationRead:
    return await service.register_for_event(event_id, current_user)


@router.delete(
    "/{event_id}/register",
    response_model=RegistrationRead,
    summary="Cancelar inscripción",
    description="Cancela la inscripción activa y libera un cupo.",
)
async def cancel_registration(
    event_id: UUID,
    service: RegistrationServiceDep,
    current_user: CurrentUser,
) -> RegistrationRead:
    return await service.cancel_registration(event_id, current_user)


@router.get(
    "/{event_id}/attendees",
    response_model=list[AttendeeRead],
    summary="Listar asistentes del evento",
    description="Solo organizador del evento o administrador.",
)
async def list_event_attendees(
    event_id: UUID,
    service: RegistrationServiceDep,
    current_user: CurrentUser,
) -> list[AttendeeRead]:
    return await service.list_event_attendees(event_id, current_user)
