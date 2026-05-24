# Mis Eventos — Backend API

[![Backend CI](https://github.com/OWNER/REPO/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/backend-ci.yml)
[![Docker Validation](https://github.com/OWNER/REPO/actions/workflows/docker-validation.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/docker-validation.yml)
[![Security Checks](https://github.com/OWNER/REPO/actions/workflows/security-checks.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/security-checks.yml)
[![Coverage](https://img.shields.io/badge/coverage-%3E70%25-brightgreen)](https://github.com/OWNER/REPO/actions/workflows/backend-ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com/)

> **Nota:** sustituye `OWNER/REPO` en los badges por tu organización y repositorio de GitHub.

API backend para **Mis Eventos**, plataforma de gestión de eventos corporativos. Diseñada con Clean Architecture ligera, stack async de punta a punta y calidad de software orientada a equipos senior.

**Documentación:** [ARCHITECTURE.md](ARCHITECTURE.md) · [AI_USAGE.md](AI_USAGE.md) (uso responsable de IA en el desarrollo)

---

## Tabla de contenidos

1. [Introducción](#introducción)
2. [Stack tecnológico](#stack-tecnológico)
3. [Arquitectura](#arquitectura)
4. [Setup local](#setup-local)
5. [Variables de entorno](#variables-de-entorno)
6. [Migraciones](#migraciones)
7. [Testing](#testing)
8. [Swagger / OpenAPI](#swagger--openapi)
9. [CI/CD](#cicd)
10. [AI Feature](#ai-feature)
11. [Docker](#docker)
12. [Seguridad](#seguridad)
13. [API REST (v1)](#api-rest-v1)
14. [Licencia](#licencia)

---

## Introducción

**Mis Eventos** es una plataforma para planificar, publicar y operar eventos presenciales o híbridos. El backend expone una API REST versionada que cubre el ciclo de vida completo del dominio:

| Dominio | Capacidades |
|---------|-------------|
| **Usuarios y auth** | Registro, login JWT, perfiles, roles (`admin`, `organizer`, `attendee`) |
| **Eventos** | CRUD, estados (`draft` → `published` → `finished` / `cancelled`), capacidad y cupos |
| **Sesiones** | Agenda por evento, validación de solapamientos (ponente / sala), ventana temporal |
| **Inscripciones** | Registro de asistentes, control de cupos, cancelación y vista “mis eventos” |
| **IA** | Generación asistida de descripciones de evento con proveedor configurable y fallback |

El objetivo de la plataforma es ofrecer una base **mantenible y auditable** para organizadores y asistentes, no un CRUD genérico: reglas de negocio explícitas, trazabilidad por `request_id` y contratos HTTP predecibles.

---

## Stack tecnológico

| Tecnología | Rol | Por qué está aquí |
|------------|-----|-------------------|
| **Python 3.12** | Runtime | Tipado maduro, rendimiento y ecosistema actual |
| **FastAPI** | Framework HTTP | Async nativo, validación Pydantic y OpenAPI automático |
| **PostgreSQL 16** | Persistencia | ACID, enums nativos, JSON futuro, producción real |
| **SQLAlchemy 2.0 (async)** | ORM | `AsyncSession`, `Mapped[]` tipado, un solo modelo de datos |
| **asyncpg** | Driver | Driver async de referencia para PostgreSQL en Python |
| **Alembic** | Migraciones | Evolución de esquema versionada y reproducible |
| **Pydantic v2** | Contratos / settings | Validación en frontera HTTP y configuración tipada |
| **JWT (python-jose)** | Autenticación | Tokens stateless con claims de rol |
| **Structlog** | Observabilidad | Logs estructurados JSON listos para agregadores |
| **Pytest + pytest-asyncio** | Calidad | Tests unitarios e integración contra PostgreSQL real |
| **uv** | Dependencias | Lockfile determinista, installs rápidos en CI y local |
| **Docker Compose** | Entorno | Paridad dev/prod, Postgres + API en un comando |
| **GitHub Actions** | CI/CD | Lint, tests, cobertura, seguridad y validación Docker |

---

## Arquitectura

El backend aplica **Clean Architecture ligera**: dependencias apuntan hacia el dominio; HTTP no conoce SQL; la lógica de negocio vive en servicios.

```
┌──────────────────────────────────────────────────────────────┐
│  Routes (FastAPI)          app/api/v1/routes/                │
│  — Validación entrada, auth, códigos HTTP                    │
├──────────────────────────────────────────────────────────────┤
│  Services                  app/services/                     │
│  — Reglas de negocio, orquestación, excepciones de dominio   │
├──────────────────────────────────────────────────────────────┤
│  Repositories              app/repositories/                 │
│  — Queries y persistencia (sin reglas de negocio)            │
├──────────────────────────────────────────────────────────────┤
│  Models (ORM)              app/models/                       │
├──────────────────────────────────────────────────────────────┤
│  Infrastructure            app/core/ + app/providers/          │
│  — Config, DB, JWT, logging, integraciones externas (IA)     │
└──────────────────────────────────────────────────────────────┘
```

**Principios clave**

- **Separación de responsabilidades:** `routes` delegan; `services` deciden; `repositories` persisten.
- **Async end-to-end:** FastAPI → SQLAlchemy `AsyncSession` → `asyncpg` sin bloquear el event loop.
- **Inyección de dependencias:** FastAPI `Depends()` para sesión DB, usuario actual y servicios.
- **Proveedores desacoplados:** la capa `app/providers/ai/` aísla OpenAI del dominio.

### Estructura del repositorio (monorepo)

```
mis-eventos/                    # Raíz del repositorio Git
├── .github/
│   ├── actions/setup-backend/  # Composite: uv + caché
│   └── workflows/              # CI/CD (backend-ci, docker, security)
├── backend/                    # ← Este proyecto
│   ├── app/
│   │   ├── api/v1/             # Router, routes, dependencies
│   │   ├── core/               # config, database, security, logging, middleware
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic DTOs
│   │   ├── repositories/       # Acceso a datos
│   │   ├── services/           # Lógica de aplicación
│   │   ├── providers/ai/       # Abstracción proveedores IA
│   │   ├── utils/              # Reglas puras (event_rules, session_rules)
│   │   ├── tests/              # unit | integration | factories | fixtures
│   │   └── main.py
│   ├── alembic/
│   ├── Dockerfile              # Multi-stage: development | production
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── README.md
│   └── ARCHITECTURE.md
└── frontend/                   # Cliente (SPA) — evolución prevista del monorepo
    └── …
```

---

## Setup local

### Requisitos

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- Docker y Docker Compose (recomendado)

### Opción A — Docker Compose (recomendado)

Levanta PostgreSQL y la API con migraciones automáticas:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/api/v1/docs |
| ReDoc | http://localhost:8000/api/v1/redoc |
| Health (ligero) | http://localhost:8000/health |
| Health + DB | http://localhost:8000/api/v1/health |

### Opción B — Desarrollo nativo con uv

```bash
cd backend

# 1. Dependencias (runtime + dev: pytest, ruff, black, pip-audit)
uv sync --all-groups

# 2. Variables de entorno
cp .env.example .env
# Si Postgres corre en localhost (no en Docker), ajusta DATABASE_URL:
# postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos

# 3. Base de datos (crear DB si no existe)
# CREATE DATABASE mis_eventos;

# 4. Migraciones
uv run alembic upgrade head

# 5. Servidor con hot reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Comandos de desarrollo frecuentes

```bash
uv sync --all-groups              # Sincronizar entorno
uv run ruff check app             # Lint
uv run ruff format app            # Formato (ruff)
uv run black app                  # Formato (black)
uv add <paquete>                  # Nueva dependencia runtime
uv add --group dev <paquete>      # Dependencia de desarrollo
```

---

## Variables de entorno

Copia [.env.example](.env.example) a `.env`. La configuración se carga vía **pydantic-settings** (`app/core/config.py`).

| Variable | Requerida | Descripción | Ejemplo |
|----------|-----------|-------------|---------|
| `DATABASE_URL` | Sí | URL async SQLAlchemy. Debe usar driver `postgresql+asyncpg://` | `postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos` |
| `TEST_DATABASE_URL` | Tests | Base dedicada para pytest de integración (no usar la DB de dev) | `postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos_test` |
| `SECRET_KEY` | Sí | Clave de firma JWT (HS256), mínimo 32 caracteres. En documentación de despliegue a menudo se llama **JWT secret**; en este proyecto la variable efectiva es `SECRET_KEY` | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | No | API key de OpenAI. Obligatoria solo si `AI_PROVIDER=openai` | `sk-…` |
| `AI_PROVIDER` | No | Proveedor IA: `mock` (default, sin red) u `openai` | `mock` |
| `ENVIRONMENT` | No | Entorno de ejecución: `development`, `staging`, `production`, `test` | `development` |

**Variables adicionales relevantes**

| Variable | Descripción |
|----------|-------------|
| `JWT_ALGORITHM` | Algoritmo JWT (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL del access token |
| `LOG_JSON` | `true` → logs JSON (producción / observabilidad) |
| `CORS_ORIGINS` | Lista JSON de orígenes permitidos |
| `AI_OPENAI_MODEL` | Modelo OpenAI (default `gpt-4o-mini`) |
| `AI_RATE_LIMIT_REQUESTS` | Límite de solicitudes IA por usuario/ventana |

> **CI/CD:** en GitHub Actions se usan `TEST_DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT=test` y `AI_PROVIDER=mock`. Opcionalmente puedes definir un secret `JWT_SECRET_KEY` en GitHub y mapearlo a `SECRET_KEY` en el workflow de despliegue.

---

## Migraciones

Las migraciones viven en `alembic/versions/` y se aplican contra PostgreSQL.

```bash
# Crear nueva revisión (autogenerate tras cambiar modelos)
uv run alembic revision --autogenerate -m "descripcion_corta"

# Revisar el script generado, luego aplicar
uv run alembic upgrade head

# Ver historial / estado
uv run alembic history
uv run alembic current
```

**Revisiones actuales:** `users` → `events` → `sessions` → `event_registrations`.

En Docker, `docker compose up` ejecuta `alembic upgrade head` antes de arrancar Uvicorn.

---

## Testing

La estrategia prioriza **PostgreSQL real** en integración (misma semántica que producción). SQLite no se usa por diseño.

### Estructura

```
app/tests/
├── unit/           # Reglas, schemas, providers — sin DB
├── integration/    # API + PostgreSQL
├── fixtures/       # client, database, users, events…
├── factories/      # payloads de prueba
└── utils/          # assertions reutilizables
```

### Preparar base de datos de test

```sql
CREATE DATABASE mis_eventos_test;
```

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos_test
export SECRET_KEY=ci-test-secret-key-minimum-32-characters-long
export ENVIRONMENT=test
export AI_PROVIDER=mock
```

### Ejecutar tests

```bash
# Suite completa (unit + integration)
uv run pytest

# Solo unitarios — no requieren PostgreSQL
uv run pytest -m unit

# Solo integración
uv run pytest -m integration

# Cobertura con reportes HTML y XML
uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
```

Abre `htmlcov/index.html` para el reporte detallado.

### Cobertura

| Ámbito | Cobertura |
|--------|-----------|
| Suite completa (con PostgreSQL) | **> 70%** en código de aplicación (`app/`, excl. tests) |
| Gate en CI | ≥ **50%** (`--cov-fail-under=50`) |
| Tests unitarios aislados | ~60% (sin ejercitar capa HTTP/DB de integración) |

La integración aporta la mayor parte de la cobertura en `services/`, `repositories/` y rutas HTTP.

### Tests con Docker

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

Levanta `postgres-test` en el puerto **5433** y ejecuta pytest dentro del contenedor de test.

### Aislamiento en integración

Cada test de integración obtiene una sesión con **rollback automático** (`join_transaction_mode="create_savepoint"`), evitando contaminación entre casos sin truncar tablas manualmente.

---

## Swagger / OpenAPI

FastAPI genera el esquema OpenAPI 3 automáticamente a partir de rutas y modelos Pydantic.

| Recurso | Ruta |
|---------|------|
| **Swagger UI** (explorar y probar) | `/api/v1/docs` |
| **ReDoc** (lectura) | `/api/v1/redoc` |
| **Esquema JSON** | `/api/v1/openapi.json` |

**Autenticación en Swagger:** botón **Authorize** → `Bearer <access_token>` obtenido de `POST /api/v1/auth/login`.

Los tags agrupan el dominio: `Authentication`, `Events`, `Sessions`, `Registrations`, `AI`, `Health`.

---

## CI/CD

Los workflows viven en `.github/workflows/` (raíz del monorepo). Se disparan en `push` y `pull_request` cuando cambia `backend/**`.

| Workflow | Qué valida |
|----------|------------|
| **backend-ci.yml** | Ruff + Black → pytest con PostgreSQL 16 (service container) → cobertura ≥ 50% |
| **docker-validation.yml** | Build multi-stage (`development`, `production`), Compose, healthcheck `/health` |
| **security-checks.yml** | `pip-audit` sobre lockfile exportado (+ cron semanal) |

**Características del pipeline**

- Python 3.12 + **uv** con caché de dependencias
- `concurrency` con cancelación de runs obsoletos en la misma rama
- `fail-fast` en matrices (preparado para ampliar versiones de Python)
- Timeouts por job
- Artefactos: `htmlcov/`, `coverage.xml`

### Reproducir CI en local

```bash
cd backend
uv sync --all-groups
uv run ruff check app
uv run ruff format --check app
uv run black --check app
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mis_eventos_test
export SECRET_KEY=ci-test-secret-key-minimum-32-characters-long
export ENVIRONMENT=test
export AI_PROVIDER=mock
uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=50
uv export --no-hashes --frozen --no-emit-project -o requirements-audit.txt
uv run pip-audit -r requirements-audit.txt --strict --desc
```

---

## AI Feature

Endpoint: `POST /api/v1/ai/generate-event-description` (requiere JWT).

Genera una **descripción profesional** para la ficha de un evento a partir del título y contexto opcional (ubicación, tipo, audiencia).

### Proveedores

| Proveedor | Configuración | Comportamiento |
|-----------|---------------|----------------|
| **Mock** | `AI_PROVIDER=mock` (default) | Respuesta determinista sin llamadas de red. Ideal para dev, tests y CI |
| **OpenAI** | `AI_PROVIDER=openai` + `OPENAI_API_KEY` | Chat Completions async con reintentos y timeout configurables |
| **Fallback** | Automático | Si OpenAI falla, el servicio degrada a `MockAIProvider` y registra el evento en logs |

### Capacidades transversales

- **Rate limiting** por usuario (`AIRateLimiter`) — respuesta `429` al exceder cuota
- **Sanitización** de entrada en schemas Pydantic
- **Trazabilidad:** logs Structlog con `request_id`, `user_id`, `provider`, `latency_ms`
- **Errores controlados:** `502` sin filtrar detalles internos del proveedor

```
Client → AIService → AIProvider (OpenAI | Mock)
                  ↘ fallback MockAIProvider (si falla OpenAI)
```

---

## Docker

### Imagen multi-stage (`Dockerfile`)

| Stage | Uso |
|-------|-----|
| `development` | `uv sync` completo, hot reload, Alembic incluido |
| `production` | Imagen mínima, usuario `appuser` no-root, `HEALTHCHECK` en `/health`, 2 workers Uvicorn |

### docker-compose.yml

| Servicio | Descripción |
|----------|-------------|
| `postgres` | PostgreSQL 16 Alpine, volumen persistente, healthcheck `pg_isready` |
| `backend` | API en puerto 8000, depende de Postgres healthy, ejecuta migraciones al arrancar |

### docker-compose.test.yml

| Servicio | Descripción |
|----------|-------------|
| `postgres-test` | DB aislada en puerto **5433** |
| `test` | Runner pytest + cobertura, sale con código de test |

---

## Seguridad

| Control | Implementación |
|---------|----------------|
| **JWT** | Access tokens HS256; claims `sub`, `role`, `type`, `exp`, `iat` |
| **Password hashing** | bcrypt vía Passlib; política de complejidad en `UserCreate` |
| **Request ID** | Middleware `RequestIdMiddleware` → header `X-Request-ID` en respuesta y logs |
| **Validación de entrada** | Pydantic v2 en todos los bodies y query params |
| **RBAC preparado** | `require_roles(UserRole.ORGANIZER, …)` con verificación token ↔ rol en BD |
| **Errores uniformes** | `{ "error": { "code", "message" }, "request_id" }` sin stack traces al cliente |
| **CORS** | Orígenes configurables por entorno |
| **Secrets** | Solo vía variables de entorno; nunca en código ni en imágenes |

**Política de contraseña:** mínimo 8 caracteres, mayúscula, minúscula, dígito y carácter especial.

---

## API REST (v1)

Prefijo base: `/api/v1`

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
| `POST` | `/events/{event_id}/sessions` | Crear sesión en evento |
| `GET` | `/events/{event_id}/sessions` | Listar sesiones del evento |
| `GET` | `/sessions/{id}` | Detalle sesión |
| `PUT` | `/sessions/{id}` | Actualizar |
| `DELETE` | `/sessions/{id}` | Eliminar (lógico) |

### Inscripciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/events/{event_id}/register` | Inscribirse |
| `DELETE` | `/events/{event_id}/register` | Cancelar inscripción |
| `GET` | `/events/{event_id}/attendees` | Asistentes (organizador) |
| `GET` | `/me/events` | Eventos del usuario inscrito |

### IA y salud

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/ai/generate-event-description` | Generar descripción con IA |
| `GET` | `/health` | Health + conectividad DB |
| `GET` | `/health` (raíz) | Health ligero sin DB |

### Ejemplo rápido

```bash
# Registro
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"org@example.com","full_name":"Ana Org","password":"Secure1@pass"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"org@example.com","password":"Secure1@pass"}' | jq -r .access_token)

# Perfil
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Licencia

MIT — ver repositorio para detalles.
