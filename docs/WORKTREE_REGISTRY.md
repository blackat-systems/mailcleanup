# Registro de worktrees

Este archivo es la fuente durable de coordinación. No reemplaza
`git worktree list`; ambos deben coincidir.

## MAIN

| Campo | Estado |
|---|---|
| Rol | Dueño integral, contratos, auditoría e integración |
| Ruta | `C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup` |
| Rama | `main` |
| HEAD heredado al iniciar | `fecdef43745a7b145641394651b364378cf6257a` |
| Base previa al desarrollo adelantado | `3209f044d12107511aaf9f973b1cc6baf89e9405` |
| Candidato funcional heredado | `0a90b71403bb176c6fd2457213bcb8b347428a92` |
| Proceso autorizado | Base Segura por portado selectivo, sólo con datos sintéticos |
| Gmail real | Prohibido |
| Remoto actual | `origin` privado: `https://github.com/blackat-systems/mailcleanup.git` |
| Política de publicación | Sólo MAIN publica `main` con autorización explícita y verificación del destino; ninguna rama especialista se publica por defecto |
| Primera publicación | `main` → `origin/main` verificada desde `6310c7654084e322b9d280cd43b359809e55d354` |
| Base consolidada | El commit que contiene este registro consolida D7; la fuente especialista conserva base `e92a77a34f25e468be3056a4c65bef8d59fa4506` |
| Estado | Base Segura, Mapa Total, C6 y D7 aceptadas con alcance sintético; D1-D7 y C5 consolidadas; D8 bloqueada |

MAIN implementó C5 directamente porque conserva composición, contratos y API
transversales. No se creó un worktree C5. El candidato agrega
`MAPA_TOTAL_API_V1.md`, fotografía SQLite, composición D4+D5, fixture `.example`,
puerta sintética y `/api/v2`; queda consolidado por el commit que contiene este
registro. C5 no habilitó D6 por sí solo ni habilita capacidades reales.

## Estado al consolidar Base Segura

- Existe un solo worktree: la ruta de MAIN indicada arriba.
- No existe un worktree especialista.
- La ruta histórica `C:\Users\Joaquin\Desktop\chatgptprojects\limpiar_mails`
  no estaba disponible durante la auditoría.
- El historial de esa referencia sí está presente en el repositorio actual.
- No hay remoto Git configurado.
- La consolidación local queda fijada por el commit que contiene este registro.
- No se creó ni habilitó ningún worktree especialista durante esa intervención.

## Dependencias futuras

Las propuestas, dependencias, contratos pendientes y condiciones de apertura se
mantienen en `docs/PLAN_DEPENDENCIAS.md`. Este registro enumera únicamente
worktrees que existen realmente.

## D1 — `real-index-persistence`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, infraestructura sintética preparatoria |
| Estado | `INTEGRADA` y consolidada; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\ab1f\mailcleanup` |
| Rama | `codex/real-index-persistence` |
| Base | `c3dc210e69e31eb252443d08558e78f756c719d2` |
| HEAD al crear | `c3dc210e69e31eb252443d08558e78f756c719d2` |
| Tarea | `01a014bf-5182-7902-a38a-ee62028bdc02` — `D1 · Persistencia del índice` |
| Prompt | `docs/prompts/D1_REAL_INDEX_PERSISTENCE.md` |
| Contrato | `docs/contracts/INDEX_PERSISTENCE_V1.md` |
| Alcance | Modelo cerrado del índice, migración SQLite, checkpoint atómico, consultas y borrado con datos sintéticos |
| Archivos permitidos | `src/mailmap/index_model.py`, `src/mailmap/repository.py`, `tests/test_index_persistence.py` |
| Gmail, OAuth y datos reales | Prohibidos |
| Commit del especialista | No autorizado |
| Integración en `main` | Auditada e integrada en el commit que contiene este registro, sobre base `7720ad4c57c984c7ba6fc2e6bc9c5e02119756a2` |

Codex creó inicialmente el checkout en `detached HEAD`. MAIN comprobó que estaba
limpio, lo adjuntó a la rama indicada y volvió a verificar rama, HEAD y estado
antes de habilitar al especialista para editar.

MAIN auditó los tres archivos autorizados, repitió la batería completa y detectó
un defecto de severidad media: una migración fallida podía dejar DDL parcial.
La integración agrega una transacción explícita para cada migración y una prueba
de regresión. D1 continúa siendo local, sintética y no apta para datos reales.

## D2 — `secure-gmail-session`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, preparación sintética de sesión |
| Estado | `INTEGRADA` en el árbol de trabajo de MAIN; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\6d71\mailcleanup` |
| Rama | `codex/secure-gmail-session` |
| Base | `889d5f55acf1262aea722ace3d48a9064d06803f` |
| HEAD al crear | `889d5f55acf1262aea722ace3d48a9064d06803f` |
| Tarea | `01a014f4-c5a0-7d31-be0a-fd7dbe92e38c` — `D2 · Sesión segura Gmail` |
| Prompt | `docs/prompts/D2_SECURE_GMAIL_SESSION.md` |
| Contrato | `docs/contracts/GMAIL_SESSION_V1.md` |
| Alcance | Sesión de sólo metadatos, puertos OAuth, identidad, DPAPI, renovación, desconexión y revocación, todo con dobles sintéticos |
| Archivos permitidos | `src/mailmap/session_model.py`, `src/mailmap/oauth_session.py`, `src/mailmap/windows_secret_store.py`, `tests/test_gmail_session.py`, `tests/test_base_segura_safety.py`, `pyproject.toml` |
| OAuth real, Gmail, credenciales y datos reales | Prohibidos durante desarrollo y pruebas |
| Commit del especialista | No autorizado |
| Integración en `main` | Auditada e integrada sobre `1c7843876efd2add2b2a6f50baf8e4fa2a5a6a64` por el commit que contiene este registro |

Codex creó inicialmente D2 en `detached HEAD`. MAIN verificó que estaba limpio,
lo adjuntó a `codex/secure-gmail-session`, confirmó nuevamente ruta, rama, base y
estado y recién entonces indicó al especialista que comenzara.

MAIN auditó los cinco archivos autorizados y corrigió tres defectos dentro del
contrato: límite máximo de cinco minutos para la autorización, rechazo de
credenciales ya vencidas y conservación del refresh token previo cuando una
renovación válida no entrega uno nuevo. La batería global pasó. D2 continúa sin
adaptadores productivos, rutas API, OAuth real, Gmail, credenciales ni datos
reales; D2 por sí sola no habilitó D3.

## D3 — `gmail-readonly-inventory`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, inventario sintético de sólo metadatos |
| Estado | `INTEGRADA`; consolidada por el commit que contiene este registro; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\f1b0\mailcleanup` |
| Rama | `codex/gmail-readonly-inventory` |
| Base | `f510db0799c94d944f28d3dd71db8a9bd79ae648` |
| HEAD al crear | `f510db0799c94d944f28d3dd71db8a9bd79ae648` |
| Tarea | `01a01570-d229-7fb1-a39e-dd55aa1761bb` — `D3 · Inventario Gmail de sólo lectura` |
| Prompt | `docs/prompts/D3_GMAIL_READONLY_INVENTORY.md` |
| Contratos | `SECURITY_PRIVACY_V1.md`, `GMAIL_READONLY_INVENTORY_V1.md`, `GMAIL_SESSION_V1.md` e `INDEX_PERSISTENCE_V1.md` |
| Alcance | Orquestación de inventario completo y parcial, paginación, metadatos exactos, reanudación, cancelación y errores, todo con dobles sintéticos |
| Archivos permitidos | `src/mailmap/gmail_inventory_model.py`, `src/mailmap/gmail_inventory.py`, `tests/test_gmail_readonly_inventory.py`, `tests/test_base_segura_safety.py` |
| OAuth, Gmail, red, credenciales y datos reales | Prohibidos durante desarrollo y pruebas |
| Adaptador productivo, API y frontend | Prohibidos |
| Commit del especialista | No autorizado |
| Integración en `main` | Auditoría, integración semántica y consolidación completadas |

Codex creó inicialmente el checkout en `detached HEAD`. MAIN comprobó que estaba
limpio, lo adjuntó a la rama indicada y volvió a verificar ruta, rama, base y
estado antes de habilitar al especialista. La tarea recibió el prompt completo
con el SHA exacto y la prohibición de conectar Gmail.

MAIN auditó los cuatro archivos entregados, detectó que las bajas parciales y
el checkpoint no compartían transacción y que un escaneo completo no retiraba
registros obsoletos. Por instrucción de Joa amplió D1 con `apply_index_page` y
`start_full_index`, agregó regresiones de rollback y reemplazo completo, adaptó
D3 y repitió la batería global. La integración continúa exclusivamente
sintética y no habilita Gmail, OAuth, credenciales, datos reales ni D4.

## D4 — `real-classification-domain`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, clasificación explicable sobre registros normalizados sintéticos |
| Estado | `INTEGRADA` y consolidada por el commit que contiene este registro; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\460d\mailcleanup` |
| Rama | `codex/real-classification-domain` |
| Base | `ba1efb4eeb2c80c0c973ee2c7c6dce12089576f2` |
| HEAD al crear | `ba1efb4eeb2c80c0c973ee2c7c6dce12089576f2` |
| Tarea | `01a0448e-800e-7420-8b07-978a87f2149a` — `D4 · Clasificación explicable real` |
| Prompt | `docs/prompts/D4_REAL_CLASSIFICATION_DOMAIN.md` |
| Contrato | `docs/contracts/CLASSIFICATION_DOMAIN_V1.md` |
| Alcance | Identidad conservadora de fuente, flujos separados, rubro, intención, suscripción, confianza y evidencia sin hints de fixtures |
| Archivos permitidos | `src/mailmap/classification_model.py`, `src/mailmap/classification_domain.py`, `tests/test_real_classification_domain.py`, ampliación acotada de `tests/test_base_segura_safety.py` |
| Gmail, OAuth, red, credenciales y datos reales | Prohibidos |
| Persistencia, API, UI, protección, planes, D5 y D6 | Prohibidos |
| Commit del especialista | No autorizado |
| Integración en `main` | Auditoría e integración semántica completadas sobre `d1671bfef0b7217de170f3c9da7aae0dbdadf14d`; consolidada por el commit que contiene este registro |

Codex creó el checkout en `detached HEAD` sobre la base exacta. MAIN comprobó
que estaba limpio, lo adjuntó a `codex/real-classification-domain` y volvió a
verificar rama, base y limpieza antes de habilitar la implementación. El prompt
fue entregado al crear la tarea con los archivos autorizados, validaciones y
stop points completos.

MAIN leyó el contrato y los cuatro archivos completos, reprodujo defectos que
las pruebas originales no cubrían y corrigió dentro del alcance: impedimento de
fusionar dominios distintos sólo por nombre, validación local de mecanismos de
baja, agrupación de señales de confianza por familias independientes y límite
de confianza baja para identidades aisladas. La batería global pasó con 162
pruebas Python, Ruff, mypy, ESLint, 4 pruebas Vitest y build Vite. Los IDs
inferidos siguen pudiendo cambiar si cambia la membresía de una fuente. D5 ya
resuelve esa variación mediante bindings conservadores y revisión explícita. D4
no habilita Gmail real, OAuth, red, credenciales, datos reales ni D6.

## D5 — `local-policy-memory`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, memoria local sintética de decisiones y protecciones |
| Estado | `INTEGRADA` y consolidada por el commit que contiene este registro; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\9623\mailcleanup` |
| Rama | `codex/local-policy-memory` |
| Base | `663d8a99e94da9c40b5787bfb5f7a6b1e5f595b8` |
| HEAD al crear | `663d8a99e94da9c40b5787bfb5f7a6b1e5f595b8` |
| Tarea | `01a04539-09b7-7780-bf93-1ca8172c63a2` — `D5 - LOCAL_POLICY_MEMORY` |
| Prompt | `docs/prompts/D5_LOCAL_POLICY_MEMORY.md` |
| Contrato | `docs/contracts/LOCAL_POLICY_MEMORY_V1.md` |
| Alcance | Preparación tipada, replay, historial append-only, undo, reconciliación conservadora, protección acumulativa y migración SQLite v3 |
| Archivos permitidos | `src/mailmap/policy_model.py`, `src/mailmap/policy_domain.py`, `src/mailmap/repository.py`, `tests/test_local_policy_memory.py`, ampliación acotada de `tests/test_base_segura_safety.py` |
| Gmail, OAuth, red, credenciales y datos reales | Prohibidos |
| API, servicio, frontend, UI, acciones y D6 | Prohibidos |
| Commit del especialista | No autorizado |
| Integración en `main` | Auditoría independiente e integración semántica completadas sobre `c479522cac3f3260111901b103dc16743585c16f`; consolidada por el commit que contiene este registro |

Codex creó inicialmente el checkout en `detached HEAD` sobre la base exacta.
MAIN comprobó que estaba limpio, creó la rama `codex/local-policy-memory` sin
mover el commit y volvió a verificar ruta, rama, HEAD y estado. La tarea recibió
el SHA exacto, el prompt durable completo y una aclaración para repetir la Puerta
0 después de adjuntar la rama.

D5 no crea ni recrea `indexed_accounts`. MAIN verificó que el borrado de cuenta
es terminal y que preparados, retries y undos anteriores no resucitan memoria
borrada. También verificó migración v3 acumulativa, replay bajo
`BEGIN IMMEDIATE`, historial append-only, aislamiento por cuenta y protección
acumulativa.

La auditoría detectó un defecto contractual: una partición podía mejorar la
confianza automática de un fragmento respecto del flujo D4 original. MAIN lo
corrigió para conservar `automatic_flow.confianza` y agregó una regresión. En
MAIN pasaron 56 pruebas D5, 12 de seguridad, 128 de regresión D1/D4/D5 y 225
pruebas Python globales, además de Ruff, mypy, ESLint, 4 pruebas Vitest y build
Vite mediante `scripts/check.ps1`. La integración permanece exclusivamente
sintética y no habilita Gmail, OAuth, credenciales, datos reales ni D6.

El remoto privado fue agregado por MAIN después de la Puerta 0 de D5. Esa
aparición posterior es una variación de infraestructura conocida: no habilita al
especialista a hacer fetch, push, commit, publicación ni a cambiar su alcance.

## D6 — `mapa-total-ui`

| Campo | Estado real |
|---|---|
| Proceso | Mapa Total, interfaz sintética sobre la API local `/api/v2` |
| Estado | `INTEGRADA`, aceptada por Joa y consolidada por el commit que contiene este registro; fuente conservada |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\bbbc\mailcleanup` |
| Rama | `codex/mapa-total-ui` |
| Base | `75764c9fbc66b2ba36bf1c3ccc5e8141e91f3130` |
| HEAD al crear | `75764c9fbc66b2ba36bf1c3ccc5e8141e91f3130` |
| Tarea | `01a0463f-19c6-76a3-a07d-2793191b868d` — `D6 · Interfaz de Mapa Total` |
| Prompt | `docs/prompts/D6_MAPA_TOTAL_UI.md` |
| Contratos | `MAPA_TOTAL_API_V1.md`, `SECURITY_PRIVACY_V1.md` y compatibilidad backend `API_V1.md` |
| Alcance | Migrar la superficie frontend activa a las nueve rutas `/api/v2`, mostrar mapa y evidencia, registrar las siete decisiones D5 y undo, con estados completos y responsive |
| Archivos permitidos | `frontend/src/**` y `frontend/index.html` |
| Backend, contratos, scripts, configuración y dependencias | Prohibidos |
| Gmail, OAuth, red externa, credenciales y datos reales | Prohibidos |
| Estudio de Limpieza, controles de sincronización y acciones | Prohibidos |
| Commit y publicación del especialista | No autorizados |
| Integración en `main` | Integración semántica completada sobre `1745acd0dd2a9e3aa176ba61934181364d60d907`; consolidada por el commit que contiene este registro |

Codex creó inicialmente el checkout en `detached HEAD` sobre la base exacta.
MAIN verificó que estaba limpio, lo adjuntó a `codex/mapa-total-ui`, volvió a
comprobar ruta, rama, HEAD y estado, y recién entonces envió el prompt durable
con el SHA exacto. El especialista no recibió autorización para usar el remoto.

El 28 de agosto de 2026 MAIN auditó los 29 archivos entregados y corrigió siete
defectos comprobados: redirecciones HTTP externas, conteo Unicode, atribución de
protección efectiva, identificación de objetivos de undo, validación de códigos
de error, foco/inercia del menú y una contradicción del fixture de protección.
Después de integrar pasaron 296 pruebas Python, Ruff, mypy estricto sobre 24
archivos, ESLint, 98 pruebas Vitest y el build Vite. MAIN recorrió Panorama,
Fuentes, vistas, detalle, Correcciones y Estado en escritorio y 390 px sin
desborde horizontal ni errores de consola. La entrega sigue siendo sintética y
no habilita Gmail, OAuth, credenciales, red externa, datos reales, D7 ni acciones.

Joa pidió después reducir la densidad visual. MAIN mantuvo las rutas y contratos,
redujo la navegación primaria y convirtió filtros, evidencia y diagnósticos
secundarios en paneles progresivos accesibles. La batería global y el recorrido
HTTP local volvieron a pasar. Joa aceptó explícitamente D6 y autorizó a MAIN a
consolidarla y publicarla el 28 de agosto de 2026. Esa aceptación no habilita
por sí sola Gmail real, OAuth, credenciales, datos privados ni acciones. Joa
autorizó después preparar C6 de Estudio de Limpieza, pero no se creó ni registró
un worktree D7. Joa aceptó C6 el 29 de agosto de 2026 y autorizó su commit; esa
decisión tampoco crea ni registra D7. Joa autorizó posteriormente redactar y
auditar el prompt `docs/prompts/D7_REAL_PLAN_ENGINE.md`; el archivo no representa
por sí mismo un worktree real. Joa autorizó después consolidarlo, crear e iniciar
D7; la instancia real queda registrada a continuación.

## D7 — `real-plan-engine`

| Campo | Estado real |
|---|---|
| Proceso | Estudio de Limpieza, motor sintético de planes sin efectos |
| Estado | `INTEGRADA`; MAIN la aprobó con correcciones y Joa autorizó consolidarla y publicarla |
| Ruta | `C:\Users\Joaquin\.codex\worktrees\4d09\mailcleanup` |
| Rama | `codex/real-plan-engine` |
| Base y HEAD al despachar | `e92a77a34f25e468be3056a4c65bef8d59fa4506` |
| Tarea | `01a04b9f-8d9d-7181-8935-c156b669c05a` — `D7 · Motor de Estudio de Limpieza` |
| Prompt | `docs/prompts/D7_REAL_PLAN_ENGINE.md` |
| Contratos | `CLEANUP_PLAN_V1.md`, `SECURITY_PRIVACY_V1.md`, `MAPA_TOTAL_API_V1.md`, `INDEX_PERSISTENCE_V1.md`, `CLASSIFICATION_DOMAIN_V1.md`, `LOCAL_POLICY_MEMORY_V1.md` y compatibilidad `API_V1.md` |
| Alcance | Modelos y dominio de planes, migración SQLite v5, transacciones/CAS/replay, nueve rutas cerradas `/api/v3/study` y pruebas sintéticas |
| Archivos nuevos permitidos | `cleanup_plan_model.py`, `cleanup_plan_domain.py`, `cleanup_plan_api.py` y tres pruebas específicas D7 |
| Archivos modificables | `repository.py`, `api.py`, `test_base_segura_safety.py` y `test_map_snapshot_repository.py`, sólo según el prompt |
| Frontend, contratos, scripts, configuración y dependencias | Prohibidos |
| Gmail, OAuth, navegador, red externa, credenciales y datos reales | Prohibidos |
| D8, acciones sobre mensajes, ejecución y Limpieza Controlada | Prohibidos |
| Commit y publicación del especialista | No autorizados |
| Auditoría MAIN | Invariantes persistidas, coherencia de muestras, paginación SQL acotada e integridad N+1 corregidas; batería global verde |
| Integración en `main` | Consolidada y publicada por el commit que contiene este registro |

Codex creó el checkout inicialmente en `detached HEAD` sobre la base exacta.
MAIN verificó que estaba limpio, creó allí la rama
`codex/real-plan-engine`, volvió a comprobar ruta, rama, HEAD y limpieza y recién
entonces envió el prompt. El especialista confirmó la pausa inicial y recibió
después la autorización de comienzo. El remoto se observó pero no está
autorizado para esta dependencia. La fuente especialista conserva exactamente
los diez archivos autorizados sin commit y permanece como evidencia.

## Reglas de actualización

Al crear, entregar, integrar o descartar un worktree se registran ruta, rama,
base, prompt, alcance, estado Git y verificaciones. Ninguna entrega especialista
se considera integrada hasta que MAIN inspecciona el diff y repite la batería
relevante.

La secuencia obligatoria es: base limpia, contrato, prompt, creación, entrega,
auditoría, integración, batería global y recién después habilitación de un
consumidor.
