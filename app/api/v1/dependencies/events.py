from typing import Annotated

from fastapi import Depends

from app.api.v1.dependencies.auth import DbSession
from app.services.event_service import EventService


async def get_event_service(session: DbSession) -> EventService:
    return EventService(session)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]
