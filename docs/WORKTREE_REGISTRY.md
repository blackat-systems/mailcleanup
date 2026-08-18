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
| Base consolidada | El commit que contiene este registro |
| Estado | Base Git limpia y técnicamente verificada; revisión visual y aceptación de producto pendientes |

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
| Estado | `EN DESARROLLO` |
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
| Integración en `main` | Pendiente de handoff y auditoría independiente de MAIN |

Codex creó inicialmente el checkout en `detached HEAD`. MAIN comprobó que estaba
limpio, lo adjuntó a la rama indicada y volvió a verificar ruta, rama, base y
estado antes de habilitar al especialista. La tarea recibió el prompt completo
con el SHA exacto y la prohibición de conectar Gmail.

## Reglas de actualización

Al crear, entregar, integrar o descartar un worktree se registran ruta, rama,
base, prompt, alcance, estado Git y verificaciones. Ninguna entrega especialista
se considera integrada hasta que MAIN inspecciona el diff y repite la batería
relevante.

La secuencia obligatoria es: base limpia, contrato, prompt, creación, entrega,
auditoría, integración, batería global y recién después habilitación de un
consumidor.
