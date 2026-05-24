from fastapi import APIRouter

from app.api.v1.dependencies.auth import CurrentUser
from app.api.v1.dependencies.registrations import RegistrationServiceDep
from app.schemas.registration import MyRegisteredEventRead

router = APIRouter()


@router.get(
    "/events",
    response_model=list[MyRegisteredEventRead],
    summary="Mis eventos registrados",
    description="Lista eventos en los que el usuario tiene inscripción activa.",
)
async def list_my_registered_events(
    service: RegistrationServiceDep,
    current_user: CurrentUser,
) -> list[MyRegisteredEventRead]:
    return await service.list_my_registered_events(current_user)
