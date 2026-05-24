from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.v1.dependencies.auth import DbSession
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Verifica el estado de la API y la conectividad con PostgreSQL.",
)
async def health_check(session: DbSession) -> dict:
    db_status = "healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" else "degraded"

    return {
        "status": overall,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
    }
