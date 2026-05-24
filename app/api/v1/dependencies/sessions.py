from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.auth import DbSession
from app.services.session_service import SessionService


async def get_session_service(session: DbSession) -> SessionService:
    return SessionService(session)


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
