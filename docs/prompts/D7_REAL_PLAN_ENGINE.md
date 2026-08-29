# Prompt D7 — Motor real de Estudio de Limpieza

## QUÉ HACE

Implementa D7 `real-plan-engine`: el agregado local, sintético y sin efectos que
crea, congela, enumera, revalida, reduce, invalida, caduca y cancela planes de
Estudio de Limpieza.

“Real” describe la calidad de las invariantes, la persistencia y la API. No
autoriza Gmail real, OAuth real, credenciales, datos privados ni acciones sobre
mensajes. Toda entrada D7 procede exclusivamente del fixture canónico `.example`
de Mapa Total.

## POR QUÉ EXISTE

Mapa Total ya permite comprender fuentes, flujos, protecciones y decisiones.
D7 agrega una fotografía reproducible de qué mensajes quedarían alcanzados por
una intención de Archivo o Papelera, con exclusiones explicables y revalidación
monotónica, sin ejecutar nada. D8 podrá presentar ese agregado sólo después de
que MAIN audite e integre D7.

## ROL

Sos el especialista D7 de MailCleanup. Trabajás sobre una única dependencia
cohesiva y entregás evidencia parcial a MAIN.

No redefinas el contrato, la arquitectura compartida, D1, D4, D5, C5 ni la API
vigente. Si una exigencia no puede cumplirse dentro de esta frontera, detenete y
devolvé el bloqueo a MAIN. Tu handoff no equivale a integración ni aceptación.

## BASE Y WORKTREE OBLIGATORIOS

Base contractual verificada por MAIN al redactar este prompt:

```text
main: 5c913f2baed3c943c159df8e495ee3ce548d78d9
C6: docs/contracts/CLEANUP_PLAN_V1.md aceptado por Joa
```

El worktree todavía no existe al redactar este archivo. MAIN debe entregarte en
el mensaje de inicio:

- autorización explícita de Joa para crear e iniciar D7;
- ruta absoluta del worktree creado;
- rama exacta `codex/real-plan-engine`;
- SHA base limpio exacto que contiene este prompt;
- estado esperado limpio.

Ese SHA debe descender de `5c913f2baed3c943c159df8e495ee3ce548d78d9` y
no puede reemplazarse por `main` móvil, otra rama o un commit parecido. Antes de
editar ejecutá en PowerShell:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git remote -v
```

Detenete si falta la autorización transmitida por MAIN o si ruta, rama, SHA o
limpieza no coinciden con su mensaje. No uses `reset`, `clean`, `checkout`
destructivo, merge, rebase ni otra maniobra para ocultar la divergencia.

`New folder/grafo.txt` es una excepción no rastreada conocida de MAIN. No forma
parte de D7: no lo crees, leas, copies, edites, muevas, borres, stages ni incluyas
en un diff o commit.

El remoto privado observado no autoriza usar red externa ni publicar. No hagas fetch,
pull, push ni contacto con GitHub.

## LECTURA OBLIGATORIA

Leé completamente antes de implementar:

1. `AGENTS.md`;
2. este prompt;
3. `docs/CONTRATO_MVP.md`;
4. `docs/contracts/CLEANUP_PLAN_V1.md`;
5. `docs/contracts/SECURITY_PRIVACY_V1.md`;
6. `docs/contracts/MAPA_TOTAL_API_V1.md`;
7. `docs/contracts/INDEX_PERSISTENCE_V1.md`;
8. `docs/contracts/CLASSIFICATION_DOMAIN_V1.md`;
9. `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`;
10. `docs/contracts/API_V1.md`;
11. la sección D7 de `docs/PLAN_DEPENDENCIAS.md`;
12. `docs/DECISIONES.md`, `docs/ESTADO_BASE_SEGURA.md` y
    `docs/WORKTREE_REGISTRY.md`;
13. `src/mailmap/index_model.py`;
14. `src/mailmap/classification_model.py` y
    `src/mailmap/classification_domain.py`;
15. `src/mailmap/policy_model.py` y `src/mailmap/policy_domain.py`;
16. `src/mailmap/repository.py`;
17. `src/mailmap/map_model.py`, `src/mailmap/map_composition.py`,
    `src/mailmap/map_synthetic_gate.py` y `src/mailmap/map_api.py`;
18. `src/mailmap/api.py` y `src/mailmap/main.py`;
19. las pruebas de repositorio, mapa, política, API y seguridad vigentes;
20. `pyproject.toml`, `scripts/run.ps1` y `scripts/check.ps1`.

Para D7 prevalece `docs/contracts/CLEANUP_PLAN_V1.md`. Si este prompt o el
código lo contradicen, no acomodes el contrato silenciosamente: detenete y
señalá archivo, sección y consecuencia concreta.

## OBJETIVO CONTRACTUAL

Construí una implementación productiva en semántica local, pero confinada a
datos sintéticos, que:

- materialice una fotografía D1+D4+D5 coherente dentro de la transacción;
- resuelva objetivos opacos de fuente, flujo y remitente;
- aplique protecciones y filtros con precedencia conservadora;
- congele seleccionados, excluidos, razones, tamaños y muestras;
- persista un ledger append-only y recibos idempotentes;
- revalide retirando miembros, nunca agregándolos ni reincorporándolos;
- exponga exactamente nueve rutas bajo `/api/v3/study`;
- mantenga `canExecute: false` en todo resultado;
- no modifique Gmail ni ningún mensaje, incluso de forma simulada.

La salida no se conecta todavía al frontend. D8 es otro consumidor y permanece
bloqueado.

## ARCHIVOS AUTORIZADOS

Podés crear exclusivamente:

```text
src/mailmap/cleanup_plan_model.py
src/mailmap/cleanup_plan_domain.py
src/mailmap/cleanup_plan_api.py
tests/test_cleanup_plan_domain.py
tests/test_cleanup_plan_repository.py
tests/test_cleanup_plan_api.py
```

Podés modificar exclusivamente:

```text
src/mailmap/repository.py
src/mailmap/api.py
tests/test_base_segura_safety.py
tests/test_map_snapshot_repository.py
```

La modificación de `src/mailmap/api.py` se limita a instalar la nueva API v3
con el `Repository` ya construido. No cambies rutas, DTO, capacidades ni
comportamiento v1 o v2.

La modificación de `tests/test_map_snapshot_repository.py` se limita a sustituir
la expectativa histórica de cuatro migraciones por la nueva realidad acumulativa
v5, demostrando a la vez que v4 permanece intacta. No cambies otras pruebas de
fotografía o composición.

La modificación de `repository.py` se limita a migración v5 y operaciones D7.
No reescribas migraciones v1-v4, tablas legadas, D1, D5, C5 ni la siembra de
Base Segura.

No modifiques frontend, fixtures, scripts, configuración, dependencias,
contratos ni documentación. Si necesitás otro archivo, devolvé la necesidad a
MAIN antes de crearlo.

## DISEÑO DE CAPAS

Mantené estas fronteras:

- `cleanup_plan_model.py`: enums, modelos inmutables, comandos, resultados,
  errores internos controlados y DTO de preparación; sin SQLite, FastAPI ni
  efectos;
- `cleanup_plan_domain.py`: selección, filtros, precedencia, razones,
  revalidación, tamaños, muestras y función canónica de remitente; puro y
  determinista para una fotografía y un reloj recibidos;
- `repository.py`: migración v5, `BEGIN IMMEDIATE`, CAS, idempotencia, ledger,
  catálogo, paginación y rollback;
- `cleanup_plan_api.py`: modelos HTTP cerrados, decodificación, allowlists,
  cursores, errores redactados e instalación de las nueve rutas;
- `api.py`: composición mínima del nuevo router con el repositorio vigente.

En `create_app`, llamá exactamente a
`install_cleanup_plan_api(app, repository)` inmediatamente después de
`install_map_api(app, repository)` y antes de calcular o montar
`frontend_dist`. Así ninguna ruta GET v3 puede quedar absorbida por el catch-all
del frontend.

La selección de un comando nuevo debe calcularse o revalidarse contra la
fotografía materializada mientras el mismo `BEGIN IMMEDIATE` permanece activo.
No confíes en una selección calculada antes del bloqueo. Podés separar el cálculo
puro mediante una función cerrada invocada por el dueño de la transacción, pero
no expongas un callback genérico que permita al consumidor sustituir reglas de
protección o membresía. Evitá ciclos de imports y duplicación de composición.

No uses `dict[str, Any]`, JSON abierto, payload genérico ni clases extensibles
para representar el dominio. Los modelos son cerrados, inmutables, con `slots`,
versiones exactas y `repr` redactado.

## ENTRADA COHERENTE Y DISPONIBILIDAD

D7 consume la fotografía pública de C5 sobre D1+D4+D5. Para crear o revalidar
debe comprobar dentro de la transacción:

- cuenta sintética exacta y existente;
- checkpoint `completed` y fotografía completa;
- puerta `map_synthetic_gate` vigente;
- revisión de mapa y política coherentes;
- índices, clasificación y políticas componibles;
- límites de metadatos, tamaños y cardinalidades.

No crees ni recrees `indexed_accounts`. Un escaneo completo conserva planes
congelados, pero bloquea objetivos, creación y revalidación hasta completarse.
Durante ese intervalo siguen disponibles historia, detalle, miembros, eventos y
cancelación. En el detalle, ambas revisiones actuales son `null` y se agrega
`current_snapshot_unavailable`; nunca informes una revisión parcial.

`GET /context` distingue capacidades estáticas de disponibilidad dinámica. Un
`GET` nunca crea una fila de estado ni muta la base.

## OBJETIVOS E IDENTIDADES

Un plan acepta entre 1 y 100 objetivos, únicamente:

```text
effective-source-v1-<24 hex>
effective-flow-v1-<24 hex>
sender-v1-<64 hex>
```

Usá exactamente las fórmulas y prefijos públicos de C6. El cliente nunca envía
direcciones, cuentas, selectores internos, IDs remotos ni etiquetas dentro de
`targets[]`. `label` existe sólo como filtro de exclusión.

Implementá y exportá desde D7 la función pública
`canonical_sender_address_v1`. Debe:

1. aceptar un `IndexedMessageRecord` y el descriptor de identidad D4 que le
   corresponde;
2. devolver `None` cuando el remitente está ausente;
3. normalizar el valor crudo mediante `strip().casefold()`;
4. exigir que el valor normalizado figure en el descriptor de identidad de la
   fuente D4;
5. responder un error controlado `study_unavailable` ante incoherencia;
6. no llamar helpers privados D4 ni `MapCompositionResult.resolve_sender`.

Los IDs locales son deterministas y no exponen directamente direcciones ni
metadatos. No son anonimización: siguen siendo datos privados y vinculables
dentro de la fotografía. Los objetivos solapados se deduplican por mensaje.

La fórmula UTF-8 del remitente es exactamente:

```text
sender-v1- + sha256("mailcleanup.study.sender.v1\0" + account_key + "\0" + canonical_sender_address)
```

La `account_key` se usa como valor opaco exacto, sin normalizarla.

El catálogo ordena exactamente por rango de tipo `source=0`, `flow=1`,
`sender=2`, `label=3`; luego por texto visible con `casefold()` sin trim ni
colapso; y finalmente por `targetId`. Sólo publica etiquetas de sistema de la
allowlist:

```text
INBOX
CATEGORY_PERSONAL
CATEGORY_SOCIAL
CATEGORY_PROMOTIONS
CATEGORY_UPDATES
CATEGORY_FORUMS
```

Las etiquetas personalizadas no aparecen y se rechazan como entrada. El soporte
de filtro personalizado permanece `false`.

## SELECCIÓN Y FILTROS

La solicitud de creación contiene exactamente:

```text
commandId
expectedMapRevision
expectedPolicyRevision
disposition
targets[]
temporalFilter
readState
excludedLabelIds[]
keepLatestPerFlow
```

`disposition` es exactamente `archive` o `trash`; es una intención inerte y no
una operación. Archivo y Papelera requieren planes distintos. Desuscripción no
forma parte de D7.

El filtro temporal es una unión cerrada:

```text
all
beforeDate(date)
dateRange(onOrAfterDate, beforeDate)
olderThanDays(days)
```

Aplicá la nulabilidad y los DTO exactos de C6. La zona civil es
`America/Argentina/Cordoba`; `beforeDate` es exclusiva, `onOrAfterDate` es
inclusiva y un rango exige inicio anterior al fin. `olderThanDays` acepta de 1 a
36.500 y usa el único `commandNow` del comando, el comienzo del día civil
correspondiente y nunca el reloj del cliente.

`readState` es exactamente `any`, `read` o `unread`; `read` y `unread` dependen
exclusivamente de la presencia de `UNREAD`. Las etiquetas excluidas se resuelven
por ID local permitido, nunca por un valor crudo enviado por el cliente. Su
fórmula UTF-8 es:

```text
label-v1- + sha256("mailcleanup.study.label.v1\0" + account_key + "\0" + provider_label_id)
```

`keepLatestPerFlow=0` desactiva la regla. Un valor positivo se aplica después de
protecciones y filtros, por flujo efectivo, con orden por `receivedAt`
descendente y `provider_message_id` ascendente. Ese ID sólo participa dentro del
dominio y nunca sale por HTTP. Los protegidos no consumen N.

## PROTECCIONES, EXCLUSIONES Y RAZONES

No existe override de protección. Excluí siempre lo que C6 enumera, incluidos:

- protección automática o manual efectiva D5;
- contradicción o revisión requerida;
- `SENT`, `DRAFT` y `TRASH`;
- estrella e importancia;
- seguridad, recuperación, comprobantes, facturas, documentación y
  cualquier otra protección contractual.

Persistí razones tipadas, únicas y en el orden exacto de precedencia de
`CLEANUP_PLAN_V1.md`; no las ordenes alfabéticamente. Conservá la acumulación
contractual cuando coinciden varias causas.

El catálogo cerrado y su orden son:

```text
sent
draft
trash
starred
important
protected_label
security
document
personal
low_confidence
contradiction
mixed_conversation
manual_policy
policy_review
outside_date
read_state_mismatch
excluded_label
keep_latest
missing_after_creation
scope_changed
protection_changed
```

Al revalidar:

- una protección nueva agrega `protection_changed` y las razones D5 actuales;
- un mensaje ausente usa sólo `missing_after_creation`;
- cambios de alcance, filtros y cuota conservan la tabla exacta de motivos C6;
- una contradicción nunca se convierte en elegibilidad por ausencia de otra
  señal.

## CONGELADO Y SELECCIÓN VACÍA

Creá IDs `cleanup-plan-v1-<UUID v4>`. La revisión comienza en 1. Congelá:

- objetivos y sus snapshots visibles;
- filtros y cortes UTC resultantes;
- miembros considerados;
- estado inicial seleccionado o excluido;
- razones de exclusión;
- tamaños estimados;
- hasta cinco muestras incluidas y cinco excluidas;
- revisiones de mapa y política;
- creación, expiración y disposición.

Si los objetivos resuelven un universo no vacío pero todas las entradas quedan
excluidas, persistí un plan `invalidated` con selección y elegibilidad en cero,
totales excluidos exactos y un único evento `created` revisión 1. Es terminal.

Si los objetivos no resuelven ningún miembro, devolvé `target_not_found` sin
crear plan. No uses un plan vacío para ocultar un target obsoleto.

Seleccionados y excluidos forman una partición disjunta y completa del universo
considerado. El límite de 100.000 se aplica a ese universo antes de protección,
fecha, lectura, etiquetas o cuota; nunca trunques.

## REVALIDACIÓN MONOTÓNICA

La revalidación recibe exactamente:

```text
commandId
expectedPlanRevision
expectedMapRevision
expectedPolicyRevision
```

Resuelve replay o conflicto antes de exigir una fotografía actual. Para un
comando nuevo, vuelve a componer la fotografía completa bajo bloqueo y sólo
puede retirar miembros de la selección congelada.

Nunca:

- agregues un mensaje llegado después;
- incorpores uno inicialmente excluido;
- reincorpores uno retirado;
- adivines una fuente o flujo por nombre o parecido;
- mejores elegibilidad porque desapareció evidencia.

Cuando `keepLatestPerFlow>0`, calculá primero el universo actual completo de los
objetivos originales y aplicá allí el límite de 100.000. Después calculá
protecciones y filtros, dejá que mensajes nuevos o antes excluidos consuman la
cuota y finalmente intersectá con los miembros congelados todavía elegibles. La
agrupación usa el `effectiveFlowId` D4+D5 actual. Un flujo incoherente produce
`study_unavailable` sin escritura.

Un selector estructural de fuente o flujo que perdió su semántica invalida el
plan completo. Una revalidación sin bajas registra un evento `revalidated`; con
bajas y miembros restantes, `reduced`; sin miembros, `invalidated`. Los retiros
son append-only y la fotografía original no se reescribe.

## ESTADOS, RELOJ Y CANCELACIÓN

Los únicos estados son:

```text
frozen
reduced
invalidated
cancelled
expired
```

No agregues `approved`, `executing`, `executed`, `reverted` ni equivalentes.

Cada comando nuevo aceptado usa un reloj inyectable leído exactamente una vez
dentro de la transacción. En creación, ese `commandNow` fija corte civil,
`createdAt`, `recordedAt` y `expiresAt=commandNow+86400 segundos`. Replay no
depende de una nueva lectura del reloj.

La precedencia efectiva es:

```text
cancelled | invalidated
        antes que
expired
        antes que
reduced | frozen
```

No existe proceso en background. Un plan vencido, cancelado o invalidado no se
revalida, cancela ni revive. Cancelación y revalidación usan CAS bajo el mismo
`BEGIN IMMEDIATE`; la cancelación agrega un evento y preserva la vista previa.

## TAMAÑOS Y MUESTRAS

Separá siempre:

```text
selectedAtCreationCount
selectedAtCreationSizeEstimateBytes
excludedAtCreationCount
excludedAtCreationSizeEstimateBytes
currentEligibleCount
currentEligibleSizeEstimateBytes
effectiveFreedBytes: null
```

Para `archive`, `storageEffect=none`; para `trash`,
`storageEffect=not_guaranteed`. No uses “espacio liberado”, “ahorro” ni una cifra
efectiva distinta de `null`.

Límites:

- 2.147.483.647 bytes por mensaje;
- 214.748.364.700.000 bytes por total;
- 100.000 miembros considerados;
- cinco muestras incluidas y cinco excluidas.

Validá sumas antes de persistir o serializar. Overflow, tamaño individual o
total inválido producen `study_unavailable` y rollback.

Las muestras contienen sólo la allowlist exacta de C6. No persistas ni expongas
IDs remotos, thread ID, etiquetas completas, cabeceras, URL de baja, cuerpo,
HTML, snippet, MIME, adjuntos ni destinatarios. Los campos visibles admitidos
son nulos cuando C6 lo permite y respetan 16 KiB UTF-8.

## SQLITE Y MIGRACIÓN V5

Agregá una migración acumulativa v5 y dejá byte por byte intactos los scripts
v1-v4. Creá exactamente estas tablas, más sólo sus índices técnicos:

```text
cleanup_plans
cleanup_plan_targets
cleanup_plan_members
cleanup_plan_member_reasons
cleanup_plan_samples
cleanup_plan_events
cleanup_plan_member_removals
cleanup_plan_requests
cleanup_plan_catalog_state
```

Cumplí el esquema normativo de C6:

- FK por cuenta a `indexed_accounts` y cascada completa;
- aislamiento por `account_key` en claves y consultas;
- miembros originales inmutables y retiros append-only;
- eventos append-only y revisión única por plan;
- recibo único por cuenta y `command_id`;
- tipos, checks, versiones, fechas UTC y enteros acotados;
- sin FK de miembros a `indexed_messages`;
- sin JSON o BLOB genérico, `payload`, `extra` o cabeceras;
- base nueva y migrada desde v4 con esquema efectivo idéntico;
- conservación exacta de tablas y datos v1-v4.

La ausencia de `cleanup_plan_catalog_state` representa revisión 0 y un GET no
la crea. El primer plan nuevo aceptado inserta la revisión 1. Cada creación
posterior y cada revalidación o cancelación nueva aceptada incrementa la revisión
exactamente una vez dentro de su transacción. Replay no incrementa. Si hay
planes y falta la fila, respondé `study_unavailable`; no autorrepares.

`start_full_index` conserva planes. `delete_account_index` los elimina junto con
eventos, muestras y recibos por cascada. Un retry histórico no recrea la cuenta.

## TRANSACCIONES, CAS E IDEMPOTENCIA

Creación, revalidación y cancelación usan `BEGIN IMMEDIATE`. Toda variante
comienza así:

1. validar frontera HTTP y modelo cerrado;
2. calcular huella canónica;
3. abrir la transacción;
4. resolver replay exacto o conflicto de `commandId` bajo bloqueo.

Después, para creación nueva:

1. capturá el único `commandNow`;
2. materializá y validá la fotografía completa;
3. compará CAS de mapa y política;
4. resolvé objetivos, selección, exclusiones y muestras;
5. persistí plan, miembros, razones, muestras, evento, recibo y catálogo.

Para revalidación nueva:

1. capturá el único `commandNow` y derivá vencimiento;
2. cargá plan y estado efectivo;
3. rechazá primero un estado terminal;
4. compará `expectedPlanRevision`;
5. recién entonces materializá la fotografía actual y compará CAS de mapa y
   política;
6. calculá la reducción y persistí retiros, evento, recibo y catálogo.

Para cancelación nueva:

1. capturá el único `commandNow` y derivá vencimiento;
2. cargá plan y estado efectivo;
3. rechazá primero un estado terminal;
4. compará `expectedPlanRevision`;
5. persistí evento, recibo y catálogo sin materializar el mapa.

Cada variante confirma conjuntamente o revierte todo. Este orden evita que un
plan vencido o un CAS obsoleto queden ocultos por un inventario incompleto.

La huella incluye versión contractual, método en mayúsculas, ruta completa
canónica —incluido `planId`— y cuerpo validado, serializados canónicamente y
resumidos con SHA-256. Usar el mismo `commandId` en otra ruta, plan o cuerpo es
`command_id_conflict`, nunca replay cruzado.

El replay exacto conserva `status`, `commandRevision`, `planId` y
`removedCount`; devuelve `replayed=true`, no lee reloj, no recalcula, no agrega
evento ni incrementa catálogo. Puede resolverse durante inventario incompleto,
pero no después del borrado terminal de la cuenta.

Probá rollback conjunto ante fallos inyectados en plan, miembros, razones,
muestras, retiros, evento, recibo y checkpoint lógico de catálogo. No atrapes
una excepción de modo que sobreviva un estado parcial.

## API LOCAL V3 CERRADA

Instalá exactamente estas nueve rutas:

```text
GET  /api/v3/study/context
GET  /api/v3/study/targets
POST /api/v3/study/plans
GET  /api/v3/study/plans
GET  /api/v3/study/plans/{planId}
GET  /api/v3/study/plans/{planId}/messages
GET  /api/v3/study/plans/{planId}/events
POST /api/v3/study/plans/{planId}/revalidate
POST /api/v3/study/plans/{planId}/cancel
```

No agregues rutas de aprobación, ejecución, Archivo, Papelera, baja,
sincronización, conexión, OAuth, borrado de índice ni Gmail.

Implementá exactamente los DTO, uniones discriminadas, catálogos, nulabilidad,
defaults, filtros y órdenes de la sección 17 de C6. JSON usa `camelCase`,
rechaza campos extra y claves duplicadas. Enteros rechazan booleanos. Arreglos
se canonizan según el contrato y rechazan duplicados.

Toda respuesta exitosa contiene en nivel superior:

```text
contractVersion: 1
dataMode: synthetic
canExecute: false
```

Los nueve GET/POST exitosos responden HTTP 200. Los recibos POST son mínimos; no
devuelven detalle. `/api/v2/context.capabilities.cleanupPlan` permanece
exactamente `false` para mantener D6 compatible.

`GET /context` publica los límites, capacidades y disponibilidad exactos de C6.
Las capacidades externas permanecen en `false`. No confundas “soportado por la
versión” con “disponible en este instante”.

## PAGINACIÓN Y CURSORES

Implementá límites y defaults exactos:

- objetivos: máximo 100;
- objetivos: default 50;
- historial de planes: máximo 100, default 50;
- mensajes: máximo 500, default 100;
- eventos: máximo 100, default 50;
- cursor: máximo 1.024 caracteres ASCII;
- query completa: máximo 4 KiB.

Los cursores son opacos, acotados y no contienen metadatos reconstruibles.
Quedan ligados a ruta, filtros, límite lógico y revisión. Objetivos usan mapa y
política; miembros y eventos usan revisión de plan; historial usa conjuntamente
`catalogRevision` y `listingAsOf`. Cambio incompatible produce `cursor_stale`;
nunca reinicies silenciosamente la paginación.

Respetá los órdenes totales exactos de C6. En `/messages`, los filtros son:

```text
all       todos los considerados al crear una sola vez
selected  todos los inicialmente seleccionados, hoy eligible o removed
eligible  sólo currentState=eligible
excluded  sólo initialState=excluded
removed   sólo currentState=removed
```

Un retirado sigue en `selected` y aparece también al consultar `removed`; no se
convierte en exclusión inicial.

## SEGURIDAD HTTP Y ERRORES

Creá un dispatcher de seguridad v3 separado. No amplíes ni relajes el middleware
v2. Denegá antes de dominio y persistencia cualquier path, método o query no
enumerado.

Exigencias:

- servidor sólo en `127.0.0.1:8765`;
- Host exacto `127.0.0.1:8765`;
- GET con Origin ausente o exacto `http://127.0.0.1:8765`;
- POST con ese Origin, JSON y cuerpo máximo 64 KiB;
- query máxima 4 KiB y nombres únicos allowlisted por ruta;
- cookies rechazadas;
- sin CORS, redirect, URL configurable ni recurso externo;
- `Cache-Control: no-store` en toda respuesta;
- OpenAPI local sin Swagger, ReDoc ni assets remotos;
- ninguna query, body, ID, dirección, asunto, path privado o excepción interna
  en logs, errores o `repr`.

Usá exclusivamente el catálogo de errores, HTTP y mensajes fijos de la sección
19 de C6:

```text
400 invalid_request | invalid_cursor
403 invalid_local_origin
404 route_not_found | target_not_found | plan_not_found
405 method_not_allowed
409 map_revision_conflict | policy_revision_conflict |
    plan_revision_conflict | command_id_conflict | cursor_stale |
    invalid_transition | plan_expired
413 payload_too_large | plan_too_large
415 json_required
422 unsupported_target | invalid_filter
503 study_unavailable | inventory_incomplete | account_unavailable
500 internal_error
```

El sobre de error es cerrado y conserva `contractVersion=1`,
`dataMode=synthetic` y `canExecute=false`. No filtres SQL, tracebacks, cuenta,
selectores, metadatos, tokens ni payloads.

Loopback, Host y Origin no son autenticación. No simules una sesión segura para
datos reales ni debilites el bloqueo vigente: la frontera local por usuario y
sesión continúa pendiente de contrato y aprobación.

## COMPATIBILIDAD OBLIGATORIA

Preservá sin cambios funcionales:

- planes legados y rutas `/api/v1`;
- las nueve rutas `/api/v2` y sus allowlists;
- el DTO v2; únicamente `index.schemaVersion` refleja legítimamente la migración
  acumulativa v5;
- D1, D4, D5 y C5;
- frontend D6;
- `oauthAvailable: false`;
- `/api/v2/context.capabilities.cleanupPlan: false`;
- `canExecute: false` incondicional;
- ausencia de clientes productivos y acciones externas o sobre mensajes.

D7 no agrega consumidor frontend. No cambies DTO C5 para “preparar” D8.

## PRUEBAS OBLIGATORIAS

Implementá con fixtures `.example` las 47 familias de la sección 22 de
`CLEANUP_PLAN_V1.md`. Como mínimo, separá evidencia en:

- dominio: identidades, objetivos, temporalidad, filtros, protecciones, cuota,
  razones, congelado, revalidación monotónica, tamaños, muestras, reloj y
  estados;
- repositorio: migración v5 nueva/migrada, esquema, cascadas, aislamiento,
  catálogo, CAS, replay, concurrencia, rollback y borrado terminal;
- API: nueve rutas, DTO cerrados, paginación, cursores, seguridad, errores,
  límites, compatibilidad v1/v2 y capacidades falsas;
- barrera negativa: ausencia de Gmail, OAuth, red externa, navegador, credenciales,
  datos reales, mutación de mensajes, ejecución externa, dependencias y
  artefactos. La persistencia local de planes sí es parte obligatoria de D7.

Incluí regresiones explícitas para:

1. universo superior a 100.000 antes de filtros;
2. selección vacía válida frente a objetivo inexistente;
3. `keepLatestPerFlow=0` desactivado;
4. remitente ausente y descriptor D4 incoherente;
5. mensajes nuevos consumiendo cuota sin incorporarse;
6. protección nueva acumulando razones;
7. replay durante inventario incompleto;
8. borrado de cuenta seguido por retry incapaz de recrearla;
9. fallo tardío que revierte todo el comando;
10. carrera de cancelación, revalidación y vencimiento;
11. `catalogRevision` evitando páginas mezcladas;
12. `/api/v2/context.capabilities.cleanupPlan` todavía falso.

No uses sleeps reales para probar tiempo ni servicios externos. Inyectá reloj y
fallos de forma determinista. No uses datos privados, cuentas reales ni un
servidor externo.

## VALIDACIÓN OBLIGATORIA

El worktree debe quedar validable sin instalar dependencias ni usar red externa. Si no
posee `.venv` o `frontend/node_modules`, podés usar temporalmente los runtimes ya
instalados en MAIN, apuntando `PYTHONPATH` al `src` de tu worktree. No modifiques
scripts, lockfiles ni configuración y retirá todo enlace o artefacto temporal al
cerrar.

Para que `scripts/check.ps1` siga siendo la batería oficial, si faltan esos dos
directorios podés crear dentro del worktree enlaces de directorio temporales y
verificados hacia `C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup\.venv`
y
`C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup\frontend\node_modules`.
Antes de crearlos verificá que los destinos existan y que las rutas de enlace
resuelvan dentro de tu worktree. Al terminar, eliminá únicamente esos enlaces
creados por vos y comprobá que los destinos de MAIN permanecen intactos. No
enlaces `data/`, bases, cachés ni otros directorios.

Ejecutá en PowerShell, desde el worktree:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_cleanup_plan_domain.py
.\.venv\Scripts\python.exe -m pytest tests\test_cleanup_plan_repository.py
.\.venv\Scripts\python.exe -m pytest tests\test_cleanup_plan_api.py
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_safety.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
git status --short --untracked-files=all
```

Si el runtime Node provisto por Codex no está en PATH, incorporalo sólo a esa
terminal. No cambies el proyecto.

Además:

- compará esquema efectivo de base nueva y migrada desde v4;
- probá HTTP real sobre loopback con base temporal y sin abrir navegador;
- revisá el diff completo y el contenido de todos los no rastreados;
- buscá secretos, direcciones fuera de `.example`, clientes externos, scopes,
  URLs, rutas de escritura y artefactos;
- verificá que las pruebas no hayan dejado DB, logs, cachés, build o enlaces.

La línea base previa a D7 era 296 pruebas Python y 98 pruebas Vitest. Informá los
conteos reales nuevos; no copies esos números como resultado.

## SEGURIDAD Y LÍMITES

D7 no autoriza:

- Gmail, OAuth, navegador o red externa;
- credenciales, tokens, secretos o datos reales;
- cliente Google/Gmail o SDK nuevo;
- lectura de cuerpos, HTML, snippet, MIME, adjuntos o destinatarios;
- modificación, Archivo, Papelera, envío, marcado o borrado de mensajes;
- desuscripción;
- ruta de aprobación o ejecución;
- frontend D8;
- Limpieza Controlada, C7, D9, C8 o D10;
- dependencia nueva, publicación o despliegue.

No uses el índice SQLite vigente con datos reales: no tiene aprobados en
conjunto ubicación, ACL, cifrado autenticado, retención, respaldo, borrado
verificable ni frontera local de sesión.

## PUNTOS DE DETENCIÓN

Detenete y devolvé evidencia concreta si:

- la Puerta 0 no coincide;
- aparece un archivo fuera de alcance;
- necesitás modificar un contrato, C5, D1, D4 o D5;
- la transacción no puede incluir fotografía, CAS, selección y persistencia;
- una revalidación puede agregar o reincorporar mensajes;
- una protección puede omitirse u overridearse;
- necesitás JSON abierto, IDs remotos, direcciones como input HTTP o una
  dependencia nueva;
- una ruta de ejecución, mutación de mensajes o escritura externa resulta
  necesaria;
- una prueba requiere red externa, OAuth, credenciales o datos reales;
- una comprobación falla y no existe una corrección mínima dentro del contrato;
- el diff contiene bases, builds, cachés, secretos o `grafo.txt`.

No resuelvas un bloqueo ampliando silenciosamente el alcance.

## GIT

No hagas commit, push, fetch, pull, merge, rebase, reset, clean, publicación ni
integración. Dejá un diff sin stage compuesto únicamente por los archivos
autorizados.

No uses `origin`. MAIN audita e integra.

## DONE WHEN

D7 está entregada sólo cuando:

- implementa íntegramente `CLEANUP_PLAN_V1.md` sobre datos sintéticos;
- existen exactamente las nueve rutas v3 y ninguna ruta de efectos;
- creación, revalidación y cancelación son atómicas, idempotentes y auditables;
- revalidación sólo reduce o invalida;
- migración v5 preserva v1-v4 y el esquema nuevo/migrado coincide;
- todos los modelos, errores, cursores y límites son cerrados;
- v1, v2 y D6 permanecen compatibles;
- `canExecute`, OAuth, red externa, datos reales y mutación de mensajes
  permanecen deshabilitados;
- pasan pruebas específicas, batería global, HTTP loopback y `diff --check`;
- no quedan artefactos, secretos ni cambios fuera de alcance;
- el handoff informa resultados reales y pendientes.

No declares D8 desbloqueada: sólo MAIN puede hacerlo después de auditar,
integrar, volver a validar y consolidar D7.

## HANDOFF A MAIN

Entregá un informe autosuficiente con:

```text
QUÉ HACE
POR QUÉ EXISTE
PRECONDITIONS
CHANGES
FILES
CONTRACTS
TRANSACTIONS
SECURITY
VALIDATION
GIT STATE
RISKS
PENDING
NEXT
```

Incluí ruta, rama, base, HEAD, estado inicial/final, worktrees, remoto observado
sin usar, lista exacta de archivos, migración, operaciones públicas, comandos y
conteos exactos. Diferenciá aprobado, omitido, fallido y no ejecutado.

Confirmá expresamente que no hubo Gmail, OAuth, navegador, red externa,
credenciales, datos reales, dependencias ni acciones externas o sobre mensajes;
la única red admitida fue la prueba HTTP loopback. Confirmá también que no hubo
commit, push ni integración.

## QUÉ HACE, AL CIERRE

Deja una candidata D7 sintética completa, persistida, verificable y lista para
auditoría independiente de MAIN, pero todavía no integrada.

## POR QUÉ EXISTE, AL CIERRE

Permite probar planes exactos, revalidables y explicables antes de diseñar la UI
D8 o habilitar cualquier puerta de Limpieza Controlada.
