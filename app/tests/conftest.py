"""Configuración global de pytest para Mis Eventos."""

pytest_plugins = [
    "app.tests.fixtures.database",
    "app.tests.fixtures.client",
    "app.tests.fixtures.users",
    "app.tests.fixtures.events",
    "app.tests.fixtures.sessions",
    "app.tests.fixtures.registrations",
    "app.tests.fixtures.ai",
]
