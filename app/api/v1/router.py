from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    auth,
    event_registrations,
    event_sessions,
    events,
    health,
    me_events,
    sessions,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(me_events.router, prefix="/me", tags=["Registrations"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(
    event_sessions.router,
    prefix="/events",
    tags=["Sessions"],
)
api_router.include_router(
    event_registrations.router,
    prefix="/events",
    tags=["Registrations"],
)
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
