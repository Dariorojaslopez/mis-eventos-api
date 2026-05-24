# Mis Eventos — Backend API

[![Backend CI](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/backend-ci.yml)
[![Docker Validation](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/docker-validation.yml/badge.svg)](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/docker-validation.yml)
[![Security Checks](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/security-checks.yml/badge.svg)](https://github.com/Dariorojaslopez/mis-eventos-api/actions/workflows/security-checks.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-red)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](https://mis-eventos-api-3625.onrender.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

API REST enterprise para **Mis Eventos** — plataforma de gestión de eventos corporativos. Backend async production-ready con reglas de negocio explícitas, seguridad hardened, observabilidad estructurada e integración de IA desacoplada del dominio.

**Documentación extendida:** [ARCHITECTURE.md](ARCHITECTURE.md) · [AI_USAGE.md](AI_USAGE.md)

---

## 🌐 Deploy

| Entorno | URL |
|---------|-----|
| **Backend API** | [https://mis-eventos-api-3625.onrender.com](https://mis-eventos-api-3625.onrender.com) |
| **Swagger UI** | [https://mis-eventos-api-3625.onrender.com/docs](https://mis-eventos-api-3625.onrender.com/docs) |
| **ReDoc** | [https://mis-eventos-api-3625.onrender.com/redoc](https://mis-eventos-api-3625.onrender.com/redoc) |
| **OpenAPI JSON** | [https://mis-eventos-api-3625.onrender.com/openapi.json](https://mis-eventos-api-3625.onrender.com/openapi.json) |
| **Health (liveness)** | [https://mis-eventos-api-3625.onrender.com/health](https://mis-eventos-api-3625.onrender.com/health) |
| **Frontend (SPA)** | [https://mis-eventos-web.vercel.app/](https://mis-eventos-web.vercel.app/) |

Prefijo API: `/api/v1`

---

## Tabla de contenidos

- [Descripción](#descripción)
- [Features](#features)
- [Arquitectura](#arquitectura)
- [Seguridad](#seguridad)
- [JWT Authentication](#jwt-authentication)
- [PostgreSQL](#postgresql)
- [SQLAlchemy Async](#sqlalchemy-async)
- [Alembic](#alembic)
- [Docker](#docker)
- [CI/CD](#cicd)
- [Testing](#testing)
- [IA](#ia)
- [OpenAPI](#openapi)
- [Observabilidad](#observabilidad)
- [Stack tecnológico](#stack-tecnológico)
- [Setup local](#setup-local)
- [Variables de entorno](#variables-de-entorno)
- [API REST (v1)](#api-rest-v1)
- [Licencia](#licencia)

---

## Descripción

**Mis Eventos Backend** es el núcleo de la plataforma full stack desplegada en producción (Render + Vercel). Expone una API REST versionada que cubre autenticación, eventos, sesiones, inscripciones y generación asistida de contenido con IA.

No es un CRUD genérico: incorpora **máquinas de estado**, control de **cupos concurrentes**, validación de **solapamientos de sesiones**, elegibilidad de **inscripciones**, errores HTTP **estructurados** y trazabilidad por `request_id`.

Diseñado con **Clean Architecture pragmática**: capas desacopladas, async end-to-end, contratos Pydantic/OpenAPI como fuente de verdad y PostgreSQL como única fuente de persistencia en todos los entornos.

Para el diseño completo del sistema (frontend + backend + infraestructura), ver [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Features

| Dominio | Capacidades |
|---------|-------------|
| **Auth & usuarios** | Registro, login JWT, perfil `/me`, roles (`admin`, `organizer`, `attendee`) |
| **Eventos** | CRUD, estados (`draft` → `published` → `finished` / `cancelled`), capacidad y cupos |
| **Sesiones** | Agenda por evento, validación de solapamientos (ponente / sala) |
| **Inscripciones** | Registro de asistentes, control de cupos, cancelación, idempotencia, `/me/events` |
| **IA** | Generación de descripciones con OpenAI o mock, rate limit, fallback automático |
| **Operaciones** | Health checks, logs JSON, migraciones automáticas en producción, security headers |

---

## Arquitectura

Monolito modular async con separación estricta de responsabilidades:

```
                    ┌─────────────────────────────────────┐
                    │         Cliente (React SPA)          │
                    │         Vercel · TanStack Query      │
                    └──────────────────┬──────────────────┘
                                       │ HTTPS / JSON / JWT
                    ┌──────────────────▼──────────────────┐
  HTTP Layer        │  Routes + Dependencies + Middleware  │
                    │  app/api/v1/ · app/core/middleware   │
                    ├─────────────────────────────────────┤
  Application       │  Services — reglas de negocio        │
                    │  app/services/                       │
                    ├─────────────────────────────────────┤
  Persistence       │  Repositories + Models (SQLAlchemy)  │
                    │  app/repositories/ · app/models/     │
                    ├─────────────────────────────────────┤
  Infrastructure    │  Core + Providers                  │
                    │  config · security · logging · AI    │
                    └──────────────────┬──────────────────┘
                                       │ asyncpg / TLS
                    ┌──────────────────▼──────────────────┐
                    │         PostgreSQL 16                │
                    └─────────────────────────────────────┘
```

**Regla de dependencia:** `routes → services → repositories → models`

**Principios**

- HTTP no conoce SQL; la lógica de negocio vive en servicios.
- Async end-to-end: FastAPI → `AsyncSession` → `asyncpg`.
- Inyección de dependencias vía FastAPI `Depends()`.
- Proveedores IA desacoplados en `app/providers/ai/`.

### Estructura del repositorio

```
mis-eventos-api/
├── app/
│   ├── api/v1/           # Router, routes, dependencies
│   ├── core/             # config, database, security, logging, middleware, migrations
│   ├── models/           # SQLAlchemy ORM
│   ├── schemas/          # Pydantic DTOs
│   ├── repositories/     # Acceso a datos
│   ├── services/         # Lógica de aplicación
│   ├── providers/ai/     # OpenAI / Mock
│   ├── utils/            # Reglas puras (event_rules, session_rules, password_policy)
│   ├── tests/            # unit | integration | factories | fixtures
│   └── main.py
├── alembic/              # Migraciones versionadas
├── scripts/              # start-production.sh (Render)
├── .github/workflows/    # CI/CD
├── Dockerfile            # Multi-stage: development | production
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── ARCHITECTURE.md
├── AI_USAGE.md
└── README.md
```

Diagramas C4, flujos full stack y decisiones técnicas: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Seguridad

Defensa en profundidad implementada en producción:

| Control | Implementación |
|---------|----------------|
| **Transporte** | HTTPS/TLS (Render + Vercel); contraseñas cifradas en tránsito |
| **Password hashing** | bcrypt nativo (12 rounds), salting automático, nunca plaintext |
| **JWT** | Access tokens HS256; revalidación de usuario activo en BD |
| **CORS** | Orígenes explícitos (`localhost:5173`, dominio Vercel) |
| **Validación** | Pydantic v2; errores 422 sanitizados sin exponer `input` |
| **Anti-enumeración** | Mensajes genéricos en login/registro duplicado |
| **Security headers** | `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`, `Referrer-Policy` |
| **Logging seguro** | Redacción automática de passwords, tokens y API keys |
| **Secretos** | 12-factor; variables de entorno; nunca en código ni imágenes |
| **RBAC** | Infraestructura `require_roles()` con verificación token ↔ rol en BD |

**Política de contraseña:** mínimo 8 caracteres, mayúscula, minúscula, dígito y especial (`!@#$%^&*._-`).

Detalle completo: [ARCHITECTURE.md § Seguridad](ARCHITECTURE.md#8-seguridad)

---

## JWT Authentication

```
POST /api/v1/auth/register  →  bcrypt hash  →  201 UserRead
POST /api/v1/auth/login     →  verify hash  →  200 { access_token, token_type, expires_in }
GET  /api/v1/auth/me        →  Bearer JWT   →  200 UserRead
```

| Aspecto | Valor |
|---------|-------|
| Algoritmo | HS256 |
| Variable | `SECRET_KEY` (mín. 32 caracteres) |
| Claims | `sub`, `role`, `type=access`, `iat`, `exp` |
| TTL | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min) |
| Header | `Authorization: Bearer <token>` |

El backend **no confía ciegamente en el token**: decodifica JWT y carga el usuario activo desde PostgreSQL en cada request protegido.

---

## PostgreSQL

- **Motor único** en desarrollo, CI y producción (no SQLite).
- **PostgreSQL 16** con enums nativos (`user_role`, `event_status`, `registration_status`).
- **Constraints** reales: cupos, fechas, unicidad parcial en inscripciones activas.
- **Render Managed Database** en producción; Docker Compose en local.
- GitHub Actions usa **service container** Postgres 16 para tests de integración.

Entidades: `users` → `events` → `sessions` → `event_registrations`

---

## SQLAlchemy Async

- **SQLAlchemy 2.0** con estilo moderno (`Mapped[]`, `mapped_column`).
- **`AsyncSession`** por request con commit/rollback en `get_db_session`.
- Driver **`asyncpg`** — referencia para PostgreSQL async en Python.
- Pool configurado: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`.
- Repositorios encapsulan queries; servicios orquestan transacciones (`begin_nested` en cupos).

---

## Alembic

Migraciones versionadas en `alembic/versions/`:

```bash
uv run alembic revision --autogenerate -m "descripcion"
uv run alembic upgrade head
uv run alembic history
uv run alembic current
```

**Revisiones actuales:** `users` → `events` → `sessions` → `event_registrations`

**Producción (Render):**

- `scripts/start-production.sh` ejecuta `alembic upgrade head` antes de Uvicorn.
- Lifespan aplica migraciones pendientes con advisory lock PostgreSQL (multi-worker safe).

---

## Docker

### Imagen multi-stage (`Dockerfile`)

| Stage | Uso |
|-------|-----|
| `development` | `uv sync` completo, hot reload, Alembic |
| `production` | Imagen mínima, usuario `appuser` non-root, `HEALTHCHECK`, 2 workers Uvicorn |

### docker-compose.yml

| Servicio | Descripción |
|----------|-------------|
| `postgres` | PostgreSQL 16 Alpine, volumen persistente, healthcheck |
| `backend` | API `:8000`, migraciones automáticas al arrancar |

### docker-compose.test.yml

| Servicio | Descripción |
|----------|-------------|
| `postgres-test` | DB aislada en puerto **5433** |
| `test` | Runner pytest + cobertura |

```bash
docker compose up --build                    # Dev
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

---

## CI/CD

Tres workflows desacoplados en [`.github/workflows/`](.github/workflows/):

| Workflow | Qué valida |
|----------|------------|
| [**backend-ci.yml**](.github/workflows/backend-ci.yml) | Ruff + Black → pytest + PostgreSQL 16 → cobertura ≥ 50% |
| [**docker-validation.yml**](.github/workflows/docker-validation.yml) | Build multi-stage, Compose, smoke test `/health` |
| [**security-checks.yml**](.github/workflows/security-checks.yml) | `pip-audit` (+ cron semanal) |

**Pipeline**

- Python 3.12 + **uv** con caché determinista
- `concurrency` con cancel-in-progress
- Artefactos: `htmlcov/`, `coverage.xml`
- Deploy automático: **Render** (backend) · **Vercel** (frontend) en merge a `main`

### Reproducir CI en local

```bash
uv sync --all-groups
uv run ruff check app
uv run ruff format --check app
uv run black --check app
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos_test
export SECRET_KEY=ci-test-secret-key-minimum-32-characters-long
export ENVIRONMENT=test
export AI_PROVIDER=mock
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=50
```

---

## Testing

Estrategia con **PostgreSQL real** en integración — misma semántica que producción.

```
app/tests/
├── unit/           # Schemas, reglas, providers — sin DB
├── integration/    # HTTP + PostgreSQL (AsyncClient)
├── fixtures/       # client, database, users, events…
├── factories/      # Payloads JSON reutilizables
└── utils/          # Assertions de errores
```

```bash
uv run pytest                    # Suite completa
uv run pytest -m unit            # Solo unitarios
uv run pytest -m integration     # Solo integración
uv run pytest --cov=app --cov-report=html
```

| Métrica | Valor |
|---------|-------|
| Suite completa | **> 70%** cobertura |
| Gate CI | ≥ **50%** (`--cov-fail-under=50`) |
| Aislamiento | Savepoint + rollback por test de integración |

---

## IA

Endpoint: `POST /api/v1/ai/generate-event-description` (requiere JWT)

Genera descripciones profesionales para fichas de evento a partir de título y contexto opcional.

| Proveedor | Config | Comportamiento |
|-----------|--------|----------------|
| **Mock** | `AI_PROVIDER=mock` (default) | Determinista, sin red — dev, tests, CI |
| **OpenAI** | `AI_PROVIDER=openai` + `OPENAI_API_KEY` | Async con reintentos y timeout |
| **Fallback** | Automático | Degrada a Mock si OpenAI falla |

- Rate limiting por usuario (`429` al exceder cuota)
- Sanitización de inputs en schemas
- Errores `502` sin filtrar detalles internos del proveedor
- Trazabilidad en logs: `request_id`, `user_id`, `provider`, `latency_ms`

Uso responsable de IA en el desarrollo: [AI_USAGE.md](AI_USAGE.md)

---

## OpenAPI

FastAPI genera **OpenAPI 3** automáticamente desde rutas y schemas Pydantic.

| Recurso | Local | Producción |
|---------|-------|------------|
| **Swagger UI** | http://localhost:8000/docs | https://mis-eventos-api-3625.onrender.com/docs |
| **ReDoc** | http://localhost:8000/redoc | https://mis-eventos-api-3625.onrender.com/redoc |
| **Esquema JSON** | http://localhost:8000/openapi.json | https://mis-eventos-api-3625.onrender.com/openapi.json |

**Autenticación en Swagger:** botón **Authorize** → `Bearer <access_token>` desde `POST /api/v1/auth/login`.

Tags: `Authentication`, `Events`, `Sessions`, `Registrations`, `AI`, `Health`.

---

## Observabilidad

| Capacidad | Implementación |
|-----------|----------------|
| **Logs JSON** | Structlog con `LOG_JSON=true` |
| **Request tracing** | `X-Request-ID` en request/response y logs |
| **Redacción** | Passwords, tokens y API keys → `[REDACTED]` |
| **Health liveness** | `GET /health` — sin tocar BD |
| **Health readiness** | `GET /api/v1/health` — incluye `SELECT 1` |
| **Errores estructurados** | `{ "error": { "code", "message", "details?" }, "request_id" }` |
| **Métricas request** | `duration_ms`, `status_code` en cada log de request |

Ejemplo de log:

```json
{
  "event": "request_completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "status_code": 200,
  "duration_ms": 87.3,
  "level": "info",
  "timestamp": "2026-05-24T21:00:00.000Z"
}
```

---

## Stack tecnológico

| Tecnología | Rol |
|------------|-----|
| **Python 3.12** | Runtime |
| **FastAPI** | Framework HTTP async + OpenAPI |
| **PostgreSQL 16** | Persistencia ACID |
| **SQLAlchemy 2.0 Async** | ORM tipado |
| **asyncpg** | Driver PostgreSQL async |
| **Alembic** | Migraciones versionadas |
| **Pydantic v2** | Validación + settings |
| **JWT (python-jose)** | Autenticación stateless |
| **bcrypt** | Hashing de contraseñas |
| **Structlog** | Logs estructurados JSON |
| **OpenAI SDK** | Proveedor IA (opcional) |
| **Pytest + httpx** | Tests unit + integración |
| **uv** | Gestión de dependencias |
| **Docker** | Paridad dev/prod |
| **GitHub Actions** | CI/CD |
| **Render** | Deploy backend |

---

## Setup local

### Requisitos

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- Docker y Docker Compose (recomendado)

### Opción A — Docker Compose (recomendado)

```bash
cp .env.example .env
docker compose up --build
```

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health | http://localhost:8000/health |
| Health + DB | http://localhost:8000/api/v1/health |

### Opción B — Desarrollo nativo

```bash
uv sync --all-groups
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Comandos frecuentes

```bash
uv run ruff check app
uv run ruff format app
uv run black app
uv run pytest
```

---

## Variables de entorno

Copia [.env.example](.env.example) a `.env`. Configuración vía **pydantic-settings** (`app/core/config.py`).

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DATABASE_URL` | Sí | `postgresql+asyncpg://...` |
| `SECRET_KEY` | Sí | Firma JWT (mín. 32 chars) |
| `ENVIRONMENT` | No | `development` \| `staging` \| `production` \| `test` |
| `CORS_ORIGINS` | No | Lista JSON de orígenes permitidos |
| `AI_PROVIDER` | No | `mock` (default) \| `openai` |
| `OPENAI_API_KEY` | No | Requerida si `AI_PROVIDER=openai` |
| `LOG_JSON` | No | `true` → logs JSON (producción) |

Ver [.env.example](.env.example) para la lista completa.

---

## API REST (v1)

Prefijo: `/api/v1`

### Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/register` | Registro |
| `POST` | `/auth/login` | Login → JWT |
| `GET` | `/auth/me` | Perfil autenticado |

### Eventos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/events` | Crear evento |
| `GET` | `/events` | Listar (filtros, paginación) |
| `GET` | `/events/{id}` | Detalle |
| `PUT` | `/events/{id}` | Actualizar |
| `DELETE` | `/events/{id}` | Cancelación lógica |

### Sesiones

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/events/{event_id}/sessions` | Crear sesión |
| `GET` | `/events/{event_id}/sessions` | Listar sesiones |
| `GET` | `/sessions/{id}` | Detalle |
| `PUT` | `/sessions/{id}` | Actualizar |
| `DELETE` | `/sessions/{id}` | Eliminar |

### Inscripciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/events/{event_id}/register` | Inscribirse |
| `DELETE` | `/events/{event_id}/register` | Cancelar inscripción |
| `GET` | `/events/{event_id}/attendees` | Asistentes (organizador) |
| `GET` | `/me/events` | Mis eventos inscritos |

### IA y salud

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/ai/generate-event-description` | Generar descripción IA |
| `GET` | `/api/v1/health` | Readiness + DB |
| `GET` | `/health` | Liveness (raíz) |

### Ejemplo rápido

```bash
# Registro
curl -s -X POST https://mis-eventos-api-3625.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","full_name":"Ana User","password":"Secure1@pass"}'

# Login
TOKEN=$(curl -s -X POST https://mis-eventos-api-3625.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Secure1@pass"}' | jq -r .access_token)

# Perfil
curl -s https://mis-eventos-api-3625.onrender.com/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Licencia

MIT — ver repositorio para detalles.

---

**Mis Eventos** · Backend by [Dariorojaslopez](https://github.com/Dariorojaslopez) · [Arquitectura completa →](ARCHITECTURE.md)
