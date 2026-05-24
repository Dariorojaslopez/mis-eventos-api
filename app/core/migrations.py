"""Ejecución de migraciones Alembic en arranque (producción)."""

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import get_logger

logger = get_logger(__name__)
_MIGRATION_LOCK_ID = 8_723_641


def _run_alembic_upgrade() -> None:
    project_root = Path(__file__).resolve().parents[2]
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.is_file():
        raise FileNotFoundError(f"Alembic config not found: {alembic_ini}")

    alembic_cfg = Config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")


async def apply_pending_migrations() -> None:
    """Aplica migraciones pendientes con lock de PostgreSQL (multi-worker safe)."""
    settings = get_settings()
    if not settings.run_db_migrations_on_startup:
        return

    async with engine.connect() as connection:
        locked = await connection.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _MIGRATION_LOCK_ID},
        )
        if not locked:
            logger.info("database_migrations_skipped", reason="another_worker_is_running")
            return

        try:
            logger.info("database_migrations_starting")
            await asyncio.to_thread(_run_alembic_upgrade)
            logger.info("database_migrations_completed")
        finally:
            await connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": _MIGRATION_LOCK_ID},
            )
