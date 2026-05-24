# Arquitectura — Mis Eventos Backend

Documento de referencia para ingeniería, revisión técnica y evolución del sistema. Describe **por qué** el backend está construido así, no solo **qué** contiene cada carpeta.

---

## 1. Visión arquitectónica

Mis Eventos es un **monolito modular async** orientado a API REST. La arquitectura prioriza:

1. **Claridad de fronteras** — HTTP, aplicación, persistencia e integraciones externas están separadas.
2. **Testabilidad** — servicios y reglas puras se prueban sin levantar la red; integración usa PostgreSQL real.
3. **Evolución incremental** — versionado `/api/v1`, migraciones Alembic y contratos Pydantic permiten cambiar sin romper clientes.
4. **Operabilidad** — logs JSON, `request_id`, health checks y pipeline CI/CD como ciudadanos de primera clase.

### Clean Architecture (implementación pragmática)

No se adoptó un DDD ceremonioso completo. Se aplicó una **Clean Architecture ligera** adecuada al tamaño del dominio y al plazo de la prueba técnica:

```
         ┌─────────────────────────────────────────┐
         │           Driving adapters              │
         │   FastAPI routes, middleware, OpenAPI   │
         └──────────────────┬──────────────────────┘
                            │ DTOs (schemas)
         ┌──────────────────▼──────────────────────┐
         │         Application layer               │
         │   services/ — reglas y orquestación     │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │         Persistence adapters            │
         │   repositories/ + models/ (SQLAlchemy)  │
         └──────────────────┬──────────────────────┘
                            │
         ┌──────────────────▼──────────────────────┐
         │         Infrastructure                │
         │   PostgreSQL, JWT, Structlog, OpenAI    │
         └─────────────────────────────────────────┘
```

**Regla de dependencia:** `routes` → `services` → `repositories` → `models`. Ningún repositorio importa FastAPI. Los `providers` (IA) son adaptadores de salida invocados solo desde servicios.

### Escalabilidad en el diseño actual

- **Vertical:** workers Uvicorn en imagen `production`; pool de conexiones SQLAlchemy (`pool_size=10`, `max_overflow=20`).
- **Horizontal (preparado):** API stateless (JWT), health checks para orquestadores, logs correlacionables por `request_id`.
- **Microservicios (no hoy):** el monolito modular permite extraer `providers/ai` o el módulo de eventos a un servicio sin reescribir el dominio, si el tráfico o el equipo lo exigen.

---

## 2. Decisiones técnicas

Cada decisión incluye el **trade-off** asumido conscientemente.

### FastAPI vs Django

| | FastAPI | Django (DRF) |
|---|---------|----------------|
| **Ventaja elegida** | Async nativo, OpenAPI automático, validación Pydantic en la misma capa que los tipos | Admin, ORM maduro, ecosistema de paquetes enorme |
| **Coste asumido** | Menos “baterías incluidas”; convenciones de equipo hay que definirlas | Stack mayormente síncrono; async en Django es viable pero menos idiomático en 2026 para APIs greenfield |

**Decisión:** se eligió **FastAPI** priorizando rendimiento en I/O concurrente (DB + futuras llamadas a IA), contrato OpenAPI como fuente de verdad para frontend y DX de tipado. Se sacrificó el ecosistema administrativo de Django y la curva de un framework “batteries-included” a cambio de control explícito de capas.

### Async vs sync

| Async (elegido) | Sync |
|-----------------|------|
| Un proceso atiende muchas conexiones I/O-bound sin un hilo por request | Modelo mental más simple |
| Coherencia con `asyncpg` y `AsyncSession` | Mezclar sync ORM + async FastAPI genera `run_in_executor` y deuda |

**Decisión:** **async end-to-end** en el path HTTP → DB. Alembic usa motor async con `run_sync` solo donde el API de migraciones lo exige. El coste es mayor disciplina en tests (`pytest-asyncio`) y depuración de race conditions en código concurrente (p. ej. rate limiter con `asyncio.Lock`).

### PostgreSQL vs SQLite

| PostgreSQL | SQLite |
|----------|--------|
| Enums nativos (`user_role`), constraints reales, concurrencia write | Cero fricción en CI local |
| Mismo motor en dev, test, CI y prod | Semántica distinta (tipos, locks) → falsos positivos en tests |

**Decisión:** **PostgreSQL exclusivo**. SQLite se descartó incluso para CI: GitHub Actions levanta un **service container** Postgres 16. El coste es exigir Docker o una instancia local para la suite completa; la ganancia es confianza en constraints, índices y comportamiento transaccional real.

### SQLAlchemy 2.0 Async

**Por qué:** un solo modelo ORM tipado con `Mapped[]`, compatible con migraciones Alembic y con el estilo 2.0 (sin query API legacy).

**Trade-off:** más verbosidad que un ORM activo tipo Django; a cambio, control fino de sesiones, savepoints en tests y queries explícitas en repositorios.

### Repository Pattern

Los repositorios encapsulan **cómo** se lee/escribe la BD; no **si** una operación de negocio es válida.

```python
# Correcto: repository
await event_repository.get_by_id(event_id)

# Incorrecto: repository con regla de negocio
# if event.status == FINISHED: raise ...  ← esto va en EventService
```

**Trade-off:** más archivos y boilerplate que “Fat Models” o queries en rutas. **Beneficio:** tests de servicio con repositorios mockeables y queries reutilizables sin duplicar SQL en cada endpoint.

### Service Layer

`EventService`, `SessionService`, `RegistrationService` concentran:

- Transiciones de estado (`draft` → `published`)
- Validación de cupos y solapamientos temporales
- Excepciones de dominio (`ConflictError`, `ForbiddenError`, …)

**Trade-off:** riesgo de “God Service” si no se divide por agregado — mitigado manteniendo un servicio por bounded context (evento, sesión, inscripción, IA).

### Docker Compose

**Por qué:** paridad de entorno, onboarding en un comando, Postgres con healthcheck antes de arrancar la API.

**Trade-off:** no sustituye Kubernetes en producción; es la capa de **desarrollo y validación CI**. La imagen `production` del Dockerfile sí prepara despliegue en runtime containerizado (usuario no-root, healthcheck).

### Structlog

**Por qué:** logs **estructurados** (JSON) con contexto (`request_id`, `user_id`, `provider`) sin parsear strings.

**Trade-off:** menos legible en consola local sin `LOG_JSON=false`; en producción el intercambio es trivial frente a agregadores (ELK, Loki, Datadog).

### GitHub Actions

Tres workflows desacoplados (calidad, Docker, seguridad) en lugar de un job monolítico:

- Fallos localizables (lint vs test vs audit)
- `concurrency` + cancelación de runs redundantes
- Matrices preparadas para ampliar Python sin reescribir YAML

**Trade-off:** más archivos de pipeline; ganancia en mantenibilidad y tiempos de feedback paralelizables.

---

## 3. Arquitectura backend por capas

### Routes (`app/api/v1/routes/`)

Responsabilidad: traducir HTTP a llamadas de servicio y mapear excepciones a status codes (vía handlers globales).

- Sin SQL directo
- Sin ramas de negocio complejas
- Documentación OpenAPI (`summary`, `responses`, tags)

**Ejemplo de flujo:**

```
POST /api/v1/events
  → EventCreate (Pydantic)
  → EventService.create(current_user, data)
  → EventRead
```

### Dependencies (`app/api/v1/dependencies/`)

Factories FastAPI para inyectar:

| Dependencia | Rol |
|-------------|-----|
| `DbSession` | `AsyncSession` por request con commit/rollback |
| `CurrentUser` | JWT → `UserRead` desde BD |
| `require_roles(...)` | RBAC con verificación token/rol en BD |
| `EventServiceDep`, `AIServiceDep`, … | Servicios con sesión o singleton cacheado (IA) |

### Services (`app/services/`)

Corazón del dominio aplicado:

| Servicio | Responsabilidades principales |
|----------|------------------------------|
| `UserService` | Registro, autenticación, perfil |
| `EventService` | CRUD eventos, publicación, cupos |
| `SessionService` | Agenda, solapamientos, capacidad por sesión |
| `RegistrationService` | Inscripciones, reglas de elegibilidad |
| `AIService` | Orquestación IA, rate limit, fallback |

### Repositories (`app/repositories/`)

Acceso a datos con SQLAlchemy 2.0. Heredan patrones de `base.py` cuando aplica. Retornan modelos ORM o `None`; no DTOs Pydantic.

### Providers (`app/providers/ai/`)

Adaptadores de integración externa:

```
AIProvider (Protocol/ABC)
├── MockAIProvider      — sin red, determinista
└── OpenAIProvider      — cliente async, reintentos
```

`create_ai_provider()` selecciona implementación según `AI_PROVIDER` y disponibilidad de `OPENAI_API_KEY`.

### Schemas (`app/schemas/`)

Contratos de entrada/salida Pydantic v2. Separados de modelos ORM para:

- No filtrar campos internos (`hashed_password`)
- Validar reglas de API (longitud, formatos) independientes de columnas DB

### Models (`app/models/`)

Estado persistido: `User`, `Event`, `Session`, `EventRegistration`. Enums PostgreSQL nativos donde aportan integridad (`UserRole`, `EventStatus`).

### Core (`app/core/`)

| Módulo | Función |
|--------|---------|
| `config.py` | `Settings` pydantic-settings, validación `DATABASE_URL` |
| `database.py` | Engine async, session factory, `get_db_session` |
| `security.py` | bcrypt, JWT encode/decode |
| `exceptions.py` | Jerarquía `AppException` + handlers |
| `logging.py` | Configuración Structlog |
| `middleware.py` | `RequestIdMiddleware` |

### Utils (`app/utils/`)

Funciones puras sin I/O: `event_rules`, `session_rules`, `text_sanitize`. Fáciles de testear con `@pytest.mark.unit`.

---

## 4. Seguridad

### Autenticación JWT

- **Algoritmo:** HS256 con `SECRET_KEY` (mín. 32 caracteres)
- **Claims:** `sub` (user UUID), `role`, `type=access`, `exp`, `iat`
- **Flujo:** login verifica bcrypt → emite token → rutas protegidas decodifican y cargan usuario activo desde BD

**Limitación consciente:** JWT stateless no permite revocación inmediata sin blacklist o refresh tokens rotativos (evolución documentada en trade-offs).

### Autorización (RBAC readiness)

Roles: `admin`, `organizer`, `attendee`.

`require_roles()`:

1. Decodifica JWT
2. Carga usuario activo
3. Compara `payload["role"]` con `user.role` en BD (detecta tokens desincronizados)
4. Verifica pertenencia al conjunto permitido

Hoy muchos endpoints de eventos usan `CurrentUser` (cualquier autenticado); la infraestructura RBAC está lista para endurecer permisos sin refactor de auth.

### Validación y superficie de ataque

- Pydantic en todos los inputs
- Contraseñas con política de complejidad
- Errores de IA sin exponer stack ni respuestas crudas del proveedor (`AIGenerationError`)
- CORS restrictivo por lista en producción

### Configuración y secretos

- 12-factor: configuración solo por entorno
- `.env` en `.gitignore`; `.env.example` sin secretos reales
- CI usa claves de prueba dedicadas, nunca producción

---

## 5. Observabilidad

### Logs JSON (Structlog)

Con `LOG_JSON=true`:

```json
{
  "event": "request_completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/events",
  "status_code": 201,
  "duration_ms": 42.5,
  "timestamp": "2026-05-24T12:00:00.000Z"
}
```

Procesadores: context vars, nivel, logger name, timestamp ISO UTC, excepciones formateadas.

### Request tracing

`RequestIdMiddleware`:

- Acepta `X-Request-ID` entrante o genera UUID
- Lo enlaza a Structlog context vars
- Lo devuelve en la respuesta
- Los handlers de error incluyen `request_id` en el payload JSON

### Health checks

| Endpoint | Propósito |
|----------|-----------|
| `GET /health` | Liveness — proceso vivo, sin tocar DB |
| `GET /api/v1/health` | Readiness — incluye `SELECT 1` a PostgreSQL |

Docker `HEALTHCHECK` en stage `production` usa `/health` para orquestadores.

---

## 6. Estrategia de testing

### Pirámide aplicada

```
        ┌─────────────┐
        │  E2E flows  │  pocos, alto valor (auth → evento → sesión → registro)
        ├─────────────┤
        │ Integration │  HTTP + PostgreSQL real, markers @integration
        ├─────────────┤
        │    Unit     │  schemas, rules, providers, servicios aislados
        └─────────────┘
```

### Unit tests (`@pytest.mark.unit`)

- Sin base de datos
- Rápidos (< 2s total)
- Cubren validadores Pydantic, reglas de dominio puras, factory de proveedores IA, rate limiter

### Integration tests (`@pytest.mark.integration`)

- `AsyncClient` (httpx ASGI) contra app real
- PostgreSQL vía `TEST_DATABASE_URL`
- Fixture `db_engine`: `drop_all` + `create_all` al inicio del módulo de sesión
- Fixture `async_db_session`: **savepoint + rollback** por test — aislamiento sin limpiar datos globalmente

### Por qué no SQLite en tests

Los constraints PostgreSQL (`CheckConstraint`, enums nativos, tipos UUID) y el comportamiento de transacciones deben validarse en el mismo motor de producción. SQLite habría ocultado bugs de esquema y de concurrencia.

### Cobertura

- **Objetivo del proyecto:** > 70% en suite completa
- **Gate CI:** ≥ 50% (`--cov-fail-under=50`) como red de seguridad mínima
- **Omitidos:** `app/tests/**`, `__init__.py` vacíos
- **Reportes:** terminal, HTML (`htmlcov/`), XML (`coverage.xml` para Sonar/Codecov)

### Factories y fixtures

- `factories/`: payloads JSON válidos reutilizables
- `fixtures/`: usuarios autenticados, headers, override de `get_db_session` para inyectar sesión de test

---

## 7. Arquitectura de IA

### Objetivo

Generar descripciones de eventos **sin acoplar** el dominio a OpenAI. El módulo de eventos no importa `openai`; solo `AIService` conoce proveedores.

### Abstracción

```python
class AIProvider(ABC):
    async def generate_event_description(
        self, context: EventDescriptionContext
    ) -> str: ...
```

`EventDescriptionContext` es un dataclass de negocio (título, ubicación, tipo, audiencia), no un dict de API cruda.

### Selección de proveedor (`factory.py`)

```
AI_PROVIDER=mock     → MockAIProvider
AI_PROVIDER=openai   → OpenAIProvider si hay API key
                      → MockAIProvider si falta key (degradación en arranque)
```

### Fallback en runtime (`AIService`)

```
1. Rate limit por user_id
2. Intentar proveedor primario
3. Si AIProviderError y primario ≠ Mock → fallback MockAIProvider
4. Si Mock falla → AIGenerationError (502 al cliente)
5. Logs: ai_request_started / ai_generation_failed / ai_provider_fallback / ai_request_completed
```

**Trade-off:** el fallback a mock mejora disponibilidad pero puede devolver contenido genérico sin avisar explícitamente al usuario final — aceptable en MVP; en producción se podría incluir `provider_used` en la respuesta (ya inferible en logs).

### Rate limiting

`AIRateLimiter` en memoria por proceso (`asyncio.Lock`). Suficiente para monolito single-instance; para horizontal scaling futuro: Redis con ventana deslizante.

### Desacoplamiento OpenAI

`OpenAIProvider` encapsula:

- Cliente async
- Timeout y reintentos con backoff
- Mapeo de errores a `AIProviderError` (sin filtrar claves ni prompts al HTTP layer)

Cambiar a Anthropic, Azure OpenAI o un modelo self-hosted implica nuevo adapter + línea en factory, sin tocar rutas ni `EventService`.

---

## 8. Escalabilidad futura

### Versionado de API

- Prefijo `/api/v1` en `Settings.api_v1_prefix`
- Nuevos breaking changes → `/api/v2` con router paralelo; v1 se mantiene hasta deprecación documentada

### Escalado horizontal

| Componente | Estado actual | Evolución |
|------------|---------------|-----------|
| API | Stateless (JWT) | Réplicas detrás de load balancer |
| Sesiones DB | Pool por instancia | PgBouncer si conexiones escalan |
| Rate limit IA | En memoria | Redis / API Gateway |
| Caché | No implementado | Redis para listados de eventos públicos, CDN para assets |

### Microservicios (readiness, no obligación)

Límites naturales de extracción:

1. **Servicio IA** — ya aislado en `providers/`
2. **Notificaciones** — futuros emails/webhooks sin contaminar `RegistrationService`
3. **Búsqueda** — índices full-text o Elasticsearch si filtros superan SQL

El monolito modular evita premature microservices; los límites de carpeta ya dibujan cortes.

### Async como base

Nuevas integraciones (webhooks, colas, otros HTTP clients) deben ser `async` para no bloquear el event loop. Trabajo CPU-bound pesado → `asyncio.to_thread` o worker Celery separado.

---

## 9. Modelo de datos (resumen)

```
users ─────────────┐
                   │ organizer_id
                   ▼
                events ──────── sessions
                   │
                   │ event_id
                   ▼
         event_registrations ─── user_id → users
```

| Entidad | Notas de diseño |
|---------|-----------------|
| `users` | UUID PK, email único, enum `user_role` nativo |
| `events` | Estados, capacidad máxima, cupos disponibles, soft cancel |
| `sessions` | Ventana temporal dentro del evento, capacidad, solapamiento |
| `event_registrations` | Unicidad inscripción activa, liberación de cupo al cancelar |

---

## 10. Flujos representativos

### Registro e inscripción

```
Attendee → POST /auth/register
        → POST /auth/login → JWT
        → POST /events/{id}/register
        → RegistrationService valida:
              evento publicado, cupos, no auto-inscripción organizador, no duplicado
        → 201 + decremento available_slots
```

### Publicación de evento

```
Organizer → POST /events (draft)
         → PUT /events/{id} (transición a published si reglas OK)
         → EventService valida fechas, capacidad, transiciones permitidas (event_rules)
```

### Generación IA

```
Organizer → POST /ai/generate-event-description + Bearer
         → AIService → OpenAIProvider
         → (error red) → fallback MockAIProvider
         → 200 + generated_description
```

---

## 11. Trade-offs reales (resumen ejecutivo)

| Decisión | Ganancia | Coste asumido |
|----------|----------|---------------|
| FastAPI sobre Django | Async + OpenAPI + tipado | Menos ecosistema integrado out-of-the-box |
| Async sobre sync | Throughput I/O | Complejidad en tests y debugging |
| PostgreSQL único | Integridad y paridad prod | Requiere DB real en dev/CI |
| Repository + Service | Testabilidad y claridad | Más capas que un CRUD rápido |
| JWT stateless | Escalado horizontal simple | Revocación y rotación más elaboradas |
| HS256 | Simplicidad en monolito | En multi-servicio, preferir RS256/JWKS |
| Commit por request en `get_db_session` | Implementación directa | Transacciones multi-agregado más delicadas |
| Fallback IA a mock | Alta disponibilidad percibida | Calidad de texto inconsistente si OpenAI cae |
| Rate limit en memoria | Cero infra extra | Incorrecto con múltiples réplicas sin store compartido |
| Monolito modular | Velocidad de entrega y refactor local | Límite de escala de equipo/proceso por despliegue |

---

## 12. Convenciones y estándares (2026)

- SQLAlchemy 2.0: `Mapped[]`, `mapped_column`, consultas 2.0 style
- Pydantic v2: `model_config`, `field_validator`
- Python 3.12+ con `StrEnum`
- Gestión de deps: **uv** + `uv.lock` reproducible
- Calidad: Ruff (lint + isort) + Black; pre-commit opcional en equipo
- Configuración: 12-factor, sin secretos en imagen

---

## Referencias internas

- Setup y comandos: [README.md](README.md)
- Workflows CI: `../.github/workflows/`
- Configuración tipada: `app/core/config.py`
- Contrato de errores: `app/core/exceptions.py`
