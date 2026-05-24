#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Mis Eventos API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2
