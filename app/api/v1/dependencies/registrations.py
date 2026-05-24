from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.auth import DbSession
from app.services.registration_service import RegistrationService


async def get_registration_service(session: DbSession) -> RegistrationService:
    return RegistrationService(session)


RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]
