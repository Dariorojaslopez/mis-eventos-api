# Uso de IA en el desarrollo — Mis Eventos

Este documento describe **de forma honesta** cómo se utilizó inteligencia artificial durante la construcción del backend de Mis Eventos. La prueba técnica evalúa criterio de ingeniería, uso responsable de IA y capacidad crítica — no la velocidad de copiar y pegar.

**Lectura recomendada junto a:** [README.md](README.md) · [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Introducción

El desarrollo de Mis Eventos se realizó con **asistencia de IA** (principalmente Cursor y modelos conversacionales), siempre bajo un principio explícito:

> La IA acelera la producción de borradores; **no sustituye** el juicio de ingeniería, la revisión de código ni la responsabilidad sobre arquitectura, seguridad y calidad.

En la práctica, el flujo habitual fue:

1. **Definir** la decisión arquitectónica o el contrato (capa, endpoint, regla de negocio).
2. **Solicitar** a la IA un borrador (scaffolding, test, workflow, documentación).
3. **Revisar** línea a línea: tipos, async, transacciones, acoplamientos, edge cases.
4. **Ejecutar** tests, linter y CI localmente antes de dar por bueno un cambio.
5. **Corregir o descartar** lo que no encajara con PostgreSQL async, Clean Architecture ligera o los requisitos de la prueba.

Ningún módulo crítico (inscripciones con cupos, JWT, proveedores IA, migraciones) se integró sin revisión manual. Los errores que aparecen en las secciones 4 y 5 son prueba de que **la IA no es oráculo**: detecta patrones comunes, pero no garantiza corrección en concurrencia, configuración ni integración real con PostgreSQL.

---

## 2. Herramientas de IA utilizadas

| Herramienta | Uso principal | Rol en el proyecto |
|-------------|---------------|-------------------|
| **Cursor** | IDE con agente integrado, edición contextual, búsqueda en repo | Scaffold de módulos, refactors mecánicos, generación de tests y YAML de CI, revisión asistida de diffs |
| **ChatGPT** (u otros LLM conversacionales) | Consultas puntuales, alternativas de diseño, redacción inicial de docs | Segunda opinión sobre trade-offs (p. ej. JWT vs sesiones), borradores de `ARCHITECTURE.md` / `README.md` |
| **Autocompletado / inline suggestions** | Completar imports, tipos `Mapped[]`, payloads de test repetitivos | Reducir fricción en código boilerplate ya validado por el equipo |
| **Generación de boilerplate** | Estructura inicial de repositorios, rutas FastAPI, factories pytest | Punto de partida; siempre ajustado a convenciones del repo |
| **Apoyo en documentación** | README, ARCHITECTURE, este `AI_USAGE.md` | Acelerar redacción; el contenido técnico y los trade-offs se revisaron contra el código real |
| **Tests repetitivos** | Casos de integración simétricos (409, 401, validaciones Pydantic) | Acelerar cobertura; aserciones y datos de prueba validados manualmente |

**Qué no se delegó a la IA**

- Decisiones de stack (FastAPI async + PostgreSQL exclusivo).
- Modelo de transacciones en inscripciones (`SELECT FOR UPDATE`, `begin_nested`).
- Contrato de errores HTTP y observabilidad (`request_id`, Structlog).
- Criterio de rechazo de SQLite, ORM legacy y acoplamiento directo a OpenAI en rutas.

---

## 3. Sugerencias de IA aceptadas

Cada ejemplo incluye qué se pidió, por qué se aceptó y cómo se validó.

### 3.1 Modelos SQLAlchemy 2.0 async (`Mapped`, enums nativos)

**Qué propuso la IA:** esqueleto de modelos con `DeclarativeBase`, `Mapped[uuid.UUID]`, `mapped_column`, relaciones `relationship()` y `CheckConstraint` para cupos (`available_slots`, `max_capacity`).

**Por qué fue útil:** alineación inmediata con SQLAlchemy 2.0 tipado y con PostgreSQL (UUID, enums `user_role`, `event_status`).

**Validación manual:**

- Revisión de que **todos** los campos datetime usen `DateTime(timezone=True)`.
- Comprobación de que los enums usen `native_enum=True` donde corresponde.
- Ejecución de migraciones Alembic y tests de integración contra PostgreSQL real.

**Resultado en código:** `app/models/event.py`, `app/models/user.py`, revisiones en `alembic/versions/`.

---

### 3.2 Fixtures de testing con aislamiento por savepoint

**Qué propuso la IA:** fixture `async_db_session` con conexión dedicada, transacción externa y `join_transaction_mode="create_savepoint"` para rollback por test.

**Por qué fue útil:** evita truncar tablas entre tests y permite inyectar la misma sesión en `AsyncClient` vía `dependency_overrides`.

**Validación manual:**

- Verificar que tests de integración **no** dejan datos residuales al ejecutar la suite completa.
- Confirmar compatibilidad con el `commit` del `get_db_session` de producción (override en tests).
- Ejecutar `pytest -m integration` con `TEST_DATABASE_URL` apuntando a `mis_eventos_test`.

**Resultado en código:** `app/tests/fixtures/database.py`, `app/tests/fixtures/client.py`.

---

### 3.3 Scaffolding de endpoints delgados (routes → services)

**Qué propuso la IA:** rutas FastAPI que solo reciben DTOs Pydantic, dependencias y delegan en `EventService`, `SessionService`, etc.

**Por qué fue útil:** refuerza Clean Architecture ligera y mantiene OpenAPI alineado con schemas.

**Validación manual:**

- Inspección de que **no** haya queries SQL ni reglas de negocio en `app/api/v1/routes/`.
- Revisión de códigos HTTP y handlers globales en `app/core/exceptions.py`.

**Ejemplo real:**

```python
# app/api/v1/routes/events.py — la ruta no decide reglas de negocio
async def create_event(
    data: EventCreate,
    service: EventServiceDep,
    current_user: CurrentUser,
) -> EventRead:
    return await service.create_event(data, current_user)
```

---

### 3.4 Validaciones Pydantic v2 (fechas, contraseñas, IA)

**Qué propuso la IA:** `@model_validator` para `end_date > start_date`, política de contraseña en `UserCreate`, límites en schemas de IA.

**Por qué fue útil:** validación en la frontera HTTP antes de tocar la BD; mensajes de error consistentes con 422.

**Validación manual:**

- Tests unitarios en `app/tests/unit/` para casos límite.
- Tests de integración que esperan 422 con payload inválido.

---

### 3.5 Abstracción de proveedor IA (factory + fallback)

**Qué propuso la IA:** interfaz `AIProvider`, implementaciones `MockAIProvider` y `OpenAIProvider`, `create_ai_provider()` según `AI_PROVIDER`.

**Por qué fue útil:** desacopla OpenAI del dominio; CI y tests usan `mock` sin red.

**Validación manual:**

- Confirmar que **ninguna** ruta importe `openai` directamente.
- Tests de fallback en `app/tests/unit/ai/test_ai_service.py`.
- `AI_PROVIDER=mock` en GitHub Actions.

**Resultado:** `app/providers/ai/`, `app/services/ai_service.py`, `app/api/v1/dependencies/ai.py`.

---

### 3.6 GitHub Actions y action composite `setup-backend`

**Qué propuso la IA:** workflows separados (`backend-ci`, `docker-validation`, `security-checks`), caché de `uv`, service container PostgreSQL 16, matrices con `fail-fast` y `concurrency`.

**Por qué fue útil:** estructura enterprise sin un YAML monolítico; reutilización del setup en varios jobs.

**Validación manual:**

- Ajuste de paths para monorepo (`backend/`).
- Corrección de `pip-audit` (ver sección 4 y 5).
- Ejecución local de ruff, black y pytest con las mismas variables que CI.

**Resultado:** `.github/workflows/*.yml`, `.github/actions/setup-backend/action.yml`.

---

## 4. Sugerencias de IA rechazadas o corregidas

Esta sección es la más relevante para demostrar **criterio senior**: la IA suele proponer lo estadísticamente común, no lo correcto para *este* sistema.

### 4.1 Lógica de negocio dentro de las routes

| | |
|---|---|
| **Propuesta IA** | Validar cupos, estados del evento y permisos directamente en el endpoint con `if`/`raise HTTPException`. |
| **Por qué es incorrecto** | Acopla HTTP al dominio; duplica reglas entre endpoints; dificulta tests unitarios y evolución del API. |
| **Corrección aplicada** | Reglas en `RegistrationService`, `EventService`, `SessionService`; rutas solo delegan. |
| **Criterio** | Single Responsibility + testabilidad del dominio sin levantar ASGI. |

---

### 4.2 Inscripción sin bloqueo de fila (race en `available_slots`)

| | |
|---|---|
| **Propuesta IA** | Leer evento, comprobar `available_slots > 0`, decrementar y guardar en dos pasos sin bloqueo. |
| **Por qué es incorrecto** | Dos requests concurrentes pueden pasar la validación y sobrescribir cupos (lost update). |
| **Corrección aplicada** | `get_by_id_for_update()` con `.with_for_update()` y `async with self._db.begin_nested():` en `RegistrationService.register_for_event`. |
| **Criterio** | Integridad bajo concurrencia en PostgreSQL; pessimistic locking acorde a contadores de cupos. |

```python
# app/repositories/event_repository.py
stmt = select(Event).where(Event.id == event_id).with_for_update()
```

---

### 4.3 Estilo ORM SQLAlchemy 1.x / queries síncronas

| | |
|---|---|
| **Propuesta IA** | `session.query(Event).filter(...)`, `Session = sessionmaker()`, mezcla de `def` síncronos en servicios. |
| **Por qué es incorrecto** | Incompatible con stack async elegido; deprecaciones 2.0; riesgo de bloquear el event loop. |
| **Corrección aplicada** | `select()` + `await session.execute()`, `AsyncSession`, servicios `async def`. |
| **Criterio** | Coherencia async end-to-end (FastAPI + asyncpg + SQLAlchemy 2.0). |

---

### 4.4 SQLite para tests o desarrollo

| | |
|---|---|
| **Propuesta IA** | `DATABASE_URL=sqlite+aiosqlite:///:memory:` para “simplificar” CI y tests locales. |
| **Por qué es incorrecto** | Enums, `CheckConstraint`, UUID y semántica de transacciones difieren; falsos positivos y bugs solo visibles en prod. |
| **Corrección aplicada** | `TEST_DATABASE_URL` con PostgreSQL; service container en GitHub Actions; `docker-compose.test.yml`. |
| **Criterio** | Paridad de motor entre test, CI y producción. |

---

### 4.5 Llamada directa a OpenAI desde la ruta

| | |
|---|---|
| **Propuesta IA** | Endpoint que instancia `OpenAI()` y llama al SDK dentro de `generate_event_description`. |
| **Por qué es incorrecto** | Acopla HTTP a proveedor externo; imposible testear sin red; sin rate limit ni fallback uniforme. |
| **Corrección aplicada** | `AIService` + `AIProvider` + factory; inyección vía `AIServiceDep`; fallback a `MockAIProvider`. |
| **Criterio** | Ports & adapters; observabilidad centralizada; CI sin secretos de OpenAI. |

---

### 4.6 `ENVIRONMENT=test` en CI sin actualizar `Settings`

| | |
|---|---|
| **Propuesta IA** | Workflow con `ENVIRONMENT=test` mientras `Settings.environment` solo permitía `development \| staging \| production`. |
| **Por qué es incorrecto** | Pydantic rechaza el arranque (`ValidationError`) al importar `app.main`; la pipeline falla antes del primer test. |
| **Corrección aplicada** | Añadir `"test"` al `Literal` en `app/core/config.py`. |
| **Criterio** | Contrato de configuración explícito; alinear tipos con variables reales de CI. |

---

### 4.7 `pip-audit --strict` sobre entorno editable

| | |
|---|---|
| **Propuesta IA** | Ejecutar `uv run pip-audit --strict --desc` sobre el venv con el paquete local `mis-eventos-backend` instalado en editable. |
| **Por qué es incorrecto** | Falla con *“Dependency not found on PyPI”* o errores por paquete editable; el job de seguridad da falso negativo. |
| **Corrección aplicada** | Exportar lockfile sin el proyecto (`uv export --no-emit-project`) y auditar `pip-audit -r requirements-audit.txt --strict`. |
| **Criterio** | Auditar dependencias **publicadas**, no el código fuente local. |

---

### 4.8 Commits automáticos por request sin considerar tests anidados

| | |
|---|---|
| **Propuesta IA** | Reutilizar `get_db_session` de producción en tests sin override ni savepoints. |
| **Por qué es incorrecto** | El `commit` al final del request interfiere con el rollback del fixture; tests flaky o estado compartido. |
| **Corrección aplicada** | Override de `get_db_session` en `async_client` + transacción con savepoint en fixture de BD. |
| **Criterio** | Aislamiento determinista de tests de integración. |

---

## 5. Bugs y problemas que la IA no detectó

Problemas reales descubiertos con **ejecución**, **revisión de CI** o **debugging manual** — no con la sugerencia del modelo.

### 5.1 Desajuste `ENVIRONMENT=test` / Pydantic (bloqueo de CI)

| | |
|---|---|
| **Síntoma** | `ValidationError` al importar settings con `ENVIRONMENT=test`. |
| **Detección** | Reproducción local del entorno de CI antes del push; `python -c "from app.core.config import get_settings"`. |
| **Causa** | Documentación y workflows asumían valor `test`; el tipo en código no lo incluía. |
| **Solución** | Extender `Literal` en `Settings.environment`. |
| **Lección** | La IA generó YAML y config en momentos distintos sin verificar consistencia global. |

---

### 5.2 Conflictos de sesión async en tests de integración

| | |
|---|---|
| **Síntoma** | Errores intermitentes o estado visible entre tests al usar la misma BD. |
| **Detección** | Ejecutar suite completa `pytest` (no tests aislados); revisar fixtures. |
| **Causa** | Interacción entre commit de `get_db_session`, override de dependencias y transacciones SQLAlchemy async. |
| **Solución** | `join_transaction_mode="create_savepoint"` + rollback explícito en fixture; override de sesión en cliente HTTP. |
| **Lección** | La IA sugirió fixtures “típicos” de tutoriales sync; el modo async 2.0 requiere lectura de documentación oficial. |

---

### 5.3 Serialización y comparación de fechas (timezone-aware)

| | |
|---|---|
| **Síntoma** | Tests de eventos/sesiones fallan o comparaciones de ventana temporal inconsistentes. |
| **Detección** | Tests de integración con payloads ISO 8601 y reglas `is_within_event_window`. |
| **Causa** | Mezcla de `datetime` naive vs aware entre JSON, Pydantic y columnas `timestamptz`. |
| **Solución** | Uso consistente de `datetime.now(UTC)` en servicios y validadores; `DateTime(timezone=True)` en modelos. |
| **Lección** | La IA no valida semántica temporal end-to-end; hace falta prueba con datos reales. |

---

### 5.4 Reglas de solapamiento de sesiones (ponente / sala)

| | |
|---|---|
| **Síntoma** | Casos borde de solapamiento no cubiertos en primera iteración. |
| **Detección** | Diseño de casos de prueba en `test_sessions.py` (conflictos 409) y revisión de `session_rules.py`. |
| **Causa** | Lógica de intervalos fácil de simplificar incorrectamente (comparaciones estrictas vs inclusivas). |
| **Solución** | Funciones puras `times_overlap`, `is_within_event_window` con tests unitarios dedicados. |
| **Lección** | Dominio de agenda requiere tabla de casos manual; la IA no sustituye análisis de casos borde. |

---

### 5.5 Cobertura “engañosa” solo con tests unitarios

| | |
|---|---|
| **Síntoma** | Cobertura aparente aceptable en `-m unit` pero capas `services/` y rutas poco ejercitadas. |
| **Detección** | Reporte `pytest --cov` separando unit vs integration; revisión de `htmlcov/`. |
| **Causa** | Mucho código en servicios solo se ejecuta con PostgreSQL y flujo HTTP completo. |
| **Solución** | Suite de integración obligatoria en CI con service container; gate `--cov-fail-under=50` y objetivo >70% en suite completa. |
| **Lección** | Métricas sin integración real sobrevaloran el trabajo hecho. |

---

### 5.6 Pipeline de lint desalineado con el repo

| | |
|---|---|
| **Síntoma** | `ruff check` / `black --check` fallan en CI pese a “código funcional”. |
| **Detección** | Ejecutar localmente los mismos comandos que `backend-ci.yml` antes de merge. |
| **Causa** | Código generado/asistido sin pasar linter; reglas estrictas en tests (`E501`, `E402` por `pytestmark`). |
| **Solución** | `ruff format`, `black`, ajuste de `per-file-ignores` donde el patrón es intencional (tests). |
| **Lección** | “Funciona en mi máquina” ≠ listo para CI; la IA no ejecuta el pipeline por defecto. |

---

### 5.7 JWT: coherencia rol en token vs rol en BD

| | |
|---|---|
| **Síntoma** | Riesgo de escalada si el rol en JWT no coincide con el usuario actualizado en BD. |
| **Detección** | Revisión de seguridad de `require_roles()` en `app/api/v1/dependencies/auth.py`. |
| **Causa** | Patrones JWT típicos confían solo en claims del token. |
| **Solución** | Verificación `user.role.value != token_role` → `UnauthorizedError` antes de autorizar. |
| **Lección** | Seguridad requiere threat modeling manual; la IA implementa el happy path. |

---

## 6. Reflexión técnica

### Ventajas reales de la IA en este proyecto

- **Velocidad en scaffolding:** repositorios, rutas, factories y YAML de CI llegan en minutos, no en horas.
- **Recordatorio de patrones modernos:** SQLAlchemy 2.0, Pydantic v2, Structlog, workflows con caché de `uv`.
- **Documentación:** primer borrador de README y ARCHITECTURE útil si se contrasta con el código.
- **Tests repetitivos:** variaciones de 401/409/422 más rápidas de generar, liberando tiempo para casos de concurrencia y reglas de negocio.

### Limitaciones observadas (2026)

- **No ejecuta** el sistema ni entiende el estado de tu CI sin que se lo indiques explícitamente.
- **Sesgo al promedio:** SQLite, ORM legacy, lógica en controllers, OpenAI en rutas — patrones frecuentes en training, no decisiones de este proyecto.
- **Concurrencia y transacciones:** raramente propone `SELECT FOR UPDATE` o savepoints correctos sin pedirlo con precisión.
- **Consistencia global:** variables de entorno, tipos Pydantic y workflows pueden desalinearse entre archivos generados en sesiones distintas.
- **Seguridad:** no reemplaza revisión de amenazas (JWT, rate limits, filtrado de errores externos).

### Por qué sigue siendo imprescindible el criterio humano

La arquitectura (capas, async, PostgreSQL único, proveedores IA) se decidió **antes** de delegar implementación. La IA optimiza teclas; el ingeniero optimiza **riesgos**:

- Integridad de datos bajo carga.
- Contratos de API estables.
- Observabilidad y operación en producción.
- Deuda técnica consciente documentada en [ARCHITECTURE.md](ARCHITECTURE.md).

Depender de la IA sin revisión es equivalente a aceptar deuda de un PR no revisado — a escala.

### Riesgo de dependencia excesiva

Señales de alerta que este proyecto evitó deliberadamente:

- Merge de código que “compila mentalmente” pero no pasa `pytest` + PostgreSQL.
- Documentación que describe features inexistentes.
- Tests que mockean todo y nunca tocan la BD real.
- Ignorar fallos de CI porque “la IA dijo que estaba bien”.

---

## 7. Conclusión

La IA **aceleró** el desarrollo de Mis Eventos: scaffolding, tests, pipelines, documentación y refactors mecánicos. No diseñó la arquitectura ni garantizó la calidad final.

**Responsabilidad humana explícita en:**

| Área | Decisión humana |
|------|-----------------|
| Arquitectura | Clean Architecture ligera, async end-to-end, sin SQLite |
| Negocio | Cupos, inscripciones, estados de evento, solapamiento de sesiones |
| Seguridad | JWT, bcrypt, RBAC, rate limit IA, errores sin filtrar proveedores |
| Calidad | PostgreSQL en tests/CI, cobertura, ruff/black, `pip-audit` correcto |
| Operación | Docker multi-stage, health checks, logs JSON con `request_id` |

Un futuro líder técnico no se distingue por usar IA, sino por **saber cuándo no confiar en ella**. Este repositorio pretende demostrar ese criterio: código revisado, trade-offs documentados y honestidad sobre lo que la automatización no resolvió.

---

*Documento alineado con el estado del backend a mayo de 2026. Si el stack o los workflows evolucionan, actualizar este archivo con el mismo rigor crítico.*
