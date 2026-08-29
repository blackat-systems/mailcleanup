# Contrato de planes de Estudio de Limpieza v1

Estado: C6 aceptado explícitamente por Joa el 29 de agosto de 2026 después de la
auditoría de MAIN. Queda consolidado por el commit que contiene este estado. Su
aceptación no crea ni autoriza el worktree D7.

Autoridad: `CONTRATO_MVP.md`, `SECURITY_PRIVACY_V1.md`, los contratos D1, D4,
D5 y C5 consolidados, y la autorización de Joa para preparar C6. Ante una
contradicción de seguridad prevalece `SECURITY_PRIVACY_V1.md`.

Este contrato no autoriza Gmail real, OAuth, credenciales, datos privados, red
externa, adaptadores productivos, modificación de mensajes, desuscripción,
Limpieza Controlada, publicación ni despliegue.

## 1. Significado de “planificación real”

En C6, “real” describe la semántica del plan: alcance exacto, miembros
congelados, persistencia transaccional, revalidación, caducidad, cancelación e
historial durable. No significa que el plan use una cuenta o mensajes reales.

La implementación D7 de este contrato debe continuar exclusivamente sobre la
cuenta y el fixture sintéticos de Mapa Total. Antes de usar metadatos privados
siguen pendientes ubicación por usuario, ACL, cifrado autenticado, retención,
respaldo y borrado verificable del índice y de los planes.

## 2. Objetivo y frontera

C6 define un agregado local incapaz de producir efectos externos:

```text
fotografía coherente D1 + checkpoint completado
                    ↓
       clasificación D4 + políticas D5
                    ↓
     selección cerrada y filtros explícitos
                    ↓
  miembros y exclusiones congelados en SQLite
                    ↓
 vista previa, revalidación, cancelación e historial
                    ↓
            canExecute: false
```

Debe permitir:

- seleccionar por remitente, fuente efectiva o flujo efectivo;
- elegir Archivo o Papelera como una intención inerte y única;
- filtrar por fecha civil, antigüedad y estado de lectura actual;
- excluir etiquetas de sistema disponibles elegidas por Joa;
- aplicar todas las protecciones automáticas y locales;
- conservar los últimos N candidatos de cada flujo efectivo;
- enumerar exactamente incluidos, excluidos y motivos;
- conservar una vista previa inmutable y muestras seguras;
- distinguir volumen estimado de espacio efectivamente liberado;
- revalidar sin incorporar mensajes nuevos;
- cancelar y consultar historia sin efectos.

No incluye aprobación para ejecutar, mutación Gmail, baja, reglas futuras,
monitoreo, desprotección, categorías o búsquedas libres, filtros de cuerpo,
palabras o adjuntos, eliminación definitiva ni vaciado de Papelera.

## 3. Frontera con los planes de Base Segura

Las rutas `/api/v1/plans/preview`, `/api/v1/plans/{plan_id}/revalidate` y la
tabla `plans` pertenecen a la demostración sintética original. Se conservan por
compatibilidad y no se reinterpretan como C6.

C6 no reutiliza ese agregado porque:

- consume el modelo legado en lugar del índice D1 y la composición D4+D5;
- guarda selección y fotografía en JSON abierto;
- no aísla por cuenta;
- permite sobrescribir una vista previa por `UPSERT`;
- no tiene caducidad, cancelación, CAS ni ledger append-only;
- acepta una lista combinable con `unsubscribe`;
- publica IDs del fixture y no IDs locales opacos;
- no persiste exclusiones, muestras ni revalidaciones completas.

La migración C6 debe conservar intacta esa tabla y sus pruebas. D8 no consume
la API v1.

## 4. Entrada coherente y condiciones para crear

La creación usa una sola `MapInputSnapshot` y su `MapCompositionResult`:

```text
account_key interna
account_exists
indexed_account_keys
fixture_version
records
checkpoint
active_policies
policy_history
policy_revision
input_revision
map_revision
```

Se exige conjuntamente:

1. cuenta sintética exacta y puerta C5 válida;
2. una sola cuenta indexada;
3. checkpoint presente y `state=completed`;
4. mapa no parcial;
5. versión D1, D4, D5 y composición conocidas;
6. `expectedMapRevision` y `expectedPolicyRevision` actuales;
7. objetivos existentes y resolubles en esa fotografía;
8. cero datos fuera de la allowlist METADATA.

Un inventario `not_started`, `running`, `paused`, `requires_full_resync` o
`failed` bloquea catálogo de objetivos, creación y revalidación. La ausencia
temporal de un ID durante un escaneo incompleto nunca se interpreta como
eliminación del mensaje ni reduce un plan. El historial, detalle, miembros y
eventos ya congelados continúan legibles desde C6; la cancelación tampoco
materializa el mapa y permanece sujeta sólo al estado y CAS del plan.

## 5. Objetivos de selección

La solicitud pública contiene entre 1 y 100 objetivos únicos de esta unión
cerrada. Cada objetivo tiene exactamente `kind` y `targetId`:

```text
source: targetId = sourceId efectivo
flow: targetId = flowId efectivo
sender: targetId = senderId local opaco
```

Fuentes y flujos usan los IDs efectivos de C5. Los remitentes reciben un ID
local determinista con formato `sender-v1-<64 hex>`. C6 debe exponer como única
fuente pública interna la función pura `canonical_sender_address_v1`. Recibe el
registro D1 y la clasificación D4 de la misma fotografía, y resuelve así:

1. `None` produce `None` y no crea objetivo de remitente;
2. otro valor se transforma únicamente con `strip()` y `casefold()`;
3. el resultado debe aparecer en `identity_descriptor.sender_addresses` de la
   fuente D4 que contiene ese mensaje;
4. si no aparece, la fotografía es incoherente y la operación completa responde
   `study_unavailable` sin escribir ni omitir silenciosamente el mensaje.

D4 sigue siendo la autoridad que valida la sintaxis completa; D7 no llama su
helper privado, no duplica una expresión regular y tampoco usa
`MapCompositionResult.resolve_sender`, que exige que D1 ya contenga el valor
canónico. Catálogo, pertenencia y fórmula de ID C6 consumen siempre el resultado
de `canonical_sender_address_v1`. La fórmula UTF-8 es:

```text
sender-v1- + sha256("mailcleanup.study.sender.v1\0" + account_key + "\0" + canonical_sender_address)
```

La `account_key` se usa como valor opaco exacto, sin normalizarla. Ese ID no es
una anonimización y sólo se resuelve dentro de la fotografía esperada. Una
dirección ausente no produce un objetivo `sender`; un valor presente que no
coincide con la salida pública de D4 bloquea la fotografía en vez de degradarse
a una ausencia.

La API C6 expone un catálogo paginado de objetivos. El navegador nunca envía
`account_key`, `provider_message_id`, selectores D5, direcciones de remitente ni
descriptores internos para crear un plan.

La unión de objetivos forma el universo inicial. Los solapamientos se eliminan
por identidad compuesta `(account_key, provider_message_id)`. La resolución se
hace en el servidor; un objetivo desconocido o de otra revisión se rechaza sin
persistir.

## 6. Filtro temporal

La solicitud contiene exactamente una variante cerrada:

```text
all
beforeDate(date)
dateRange(onOrAfterDate, beforeDate)
olderThanDays(days)
```

Reglas:

- la zona civil es siempre `America/Argentina/Cordoba` en v1;
- `beforeDate` es exclusiva: inicio de esa fecha civil convertido a UTC;
- `onOrAfterDate` es inclusiva: inicio de esa fecha civil convertido a UTC;
- un rango exige `onOrAfterDate < beforeDate`;
- `olderThanDays` acepta entre 1 y 36.500 días;
- la antigüedad se resuelve con el reloj del servidor y días civiles completos:
  `resolvedBeforeUtc` es el inicio en Córdoba de
  `localDate(serverNow) - days`, convertido a UTC, y la comparación es exclusiva;
- el corte resultante se persiste como instantes UTC y no vuelve a desplazarse;
- fechas inexistentes, ambiguas o fuera de rango se rechazan.

Por ejemplo, “antes del 01/06/2026” significa estrictamente
`received_at < 2026-06-01T00:00:00` en Córdoba, después convertido a UTC.

## 7. Lectura, etiquetas y últimos N

`readState` es `any`, `read` o `unread`. En v1:

- `unread` significa que el registro contiene la etiqueta exacta `UNREAD`;
- `read` significa que no la contiene;
- no se presenta este valor como tasa de apertura ni evidencia de atención.

Las exclusiones elegidas por etiqueta usan IDs opacos `label-v1-<64 hex>` del
catálogo C6. El identificador de proveedor se toma exactamente como fue validado
y serializado por D1 —es opaco y sensible a mayúsculas— y la fórmula UTF-8 es:

```text
label-v1- + sha256("mailcleanup.study.label.v1\0" + account_key + "\0" + provider_label_id)
```

El servidor resuelve ese identificador dentro de la fotografía y nunca acepta
el valor de proveedor directamente desde el cliente. La `account_key` tampoco
sale por HTTP.

D1/D3 no conservan nombres de etiquetas personalizadas. C6 v1 no los inventa ni
expone su ID remoto como nombre. El catálogo ofrece sólo estas etiquetas de
sistema cuando aparecen en la fotografía, con texto local fijo:

| ID interno | Nombre visible |
|---|---|
| `INBOX` | Recibidos |
| `CATEGORY_PERSONAL` | Principal |
| `CATEGORY_SOCIAL` | Social |
| `CATEGORY_PROMOTIONS` | Promociones |
| `CATEGORY_UPDATES` | Actualizaciones |
| `CATEGORY_FORUMS` | Foros |

`UNREAD` se controla con `readState`; las demás etiquetas de protección o
exclusión dura no se ofrecen como filtros redundantes. Las etiquetas
personalizadas quedan fuera de C6 v1 hasta que MAIN y Joa autoricen un contrato
de metadatos de etiquetas, su persistencia y su privacidad.

`keepLatestPerFlow` acepta entre 0 y 10.000. Cero desactiva la regla; un valor
positivo se aplica por flujo efectivo, no por fuente ni por el conjunto global.
Primero se aplican protecciones y filtros; después se conservan los N candidatos
ordinarios más recientes de cada flujo.
Los mensajes ya protegidos no consumen esa cuota. El orden es:

```text
received_at DESC, provider_message_id ASC
```

Esta regla preserva separadamente, por ejemplo, comprobantes y promociones de
una misma fuente.

## 8. Exclusiones y precedencia

La elegibilidad se calcula por mensaje en este orden:

1. pertenencia a un objetivo seleccionado;
2. exclusiones obligatorias y protecciones;
3. filtro temporal;
4. estado de lectura;
5. etiquetas excluidas por Joa;
6. `keepLatestPerFlow`;
7. inclusión final.

Siempre quedan fuera:

- `SENT`, `DRAFT` y `TRASH`;
- `STARRED` e `IMPORTANT`;
- `hard_excluded`, `protected` o `review_required` de D5;
- seguridad y recuperación de cuenta;
- documentos, comprobantes y facturas;
- comunicación personal;
- confianza baja o contradictoria;
- conversación con protección mixta;
- protección manual por mensaje, remitente, etiqueta, fuente o flujo;
- bindings `NEEDS_REVIEW`, `AMBIGUOUS` o `CONFLICT` que alcancen al miembro.

`ORPHANED` sin objetivo actual permanece en la historia D5 y no inventa
miembros afectados. C6 v1 no ofrece “incluir de todos modos” ni una forma de
rebajar protección.

Cada exclusión conserva uno o más códigos cerrados, únicos y ordenados. El
catálogo y su orden contractual v1 son exactamente:

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
```

y estos motivos propios de C6:

```text
outside_date
read_state_mismatch
excluded_label
keep_latest
missing_after_creation
scope_changed
protection_changed
```

La persistencia, la API y las comparaciones usan siempre ese orden, no orden
lexicográfico ni el orden accidental en que se detectaron las condiciones. La
tabla condición → motivos es cerrada:

- toda protección o exclusión D5 agrega todos los valores actuales de
  `protection_reasons`, incluidos `sent`, `draft`, `trash`, `starred`,
  `important`, `protected_label`, `security`, `document`, `personal`,
  `low_confidence`, `contradiction`, `mixed_conversation`, `manual_policy` y
  `policy_review` que correspondan;
- fallar el corte temporal agrega `outside_date`;
- fallar `readState` agrega `read_state_mismatch`;
- contener una etiqueta elegida por Joa agrega `excluded_label`;
- quedar fuera de la cuota N agrega `keep_latest`;
- desaparecer después de la creación agrega únicamente
  `missing_after_creation`, porque ya no hay una fotografía actual sobre la que
  evaluar otros motivos;
- dejar de pertenecer a todos los objetivos originales todavía resolubles
  agrega `scope_changed`;
- una protección D5 que no estaba presente al crear agrega
  `protection_changed` y además todos sus motivos D5 actuales.

Las condiciones evaluables se acumulan, se deduplican y recién entonces se
ordenan por el catálogo anterior. Si un objetivo `source` o `flow` deja de tener
la misma semántica, el plan completo se invalida y cada miembro todavía elegible
se retira con `scope_changed`; no se inventa una pertenencia sustituta. Los
miembros retirados anteriormente conservan sus motivos históricos.

## 9. Congelado e identidad

Al crear, el plan conserva dos conjuntos distintos:

- universo considerado: todos los mensajes actuales alcanzados por objetivos;
- selección congelada: sólo los mensajes elegibles después de exclusiones.

Cada miembro se identifica internamente por
`(account_key, provider_message_id)`. HTTP expone únicamente el ID local
`message-v1-<64 hex>` ya definido por C5.

La fotografía original es inmutable. Guarda como mínimo:

- versión contractual;
- criterios canónicos y cortes UTC resueltos;
- objetivos opacos y huellas de sus selectores;
- `input_revision`, `mapRevision` y `policyRevision` de creación;
- miembros incluidos y excluidos;
- razones, fecha, estado de lectura y tamaño de cada miembro;
- totales y muestras;
- checkpoint y versiones necesarias para detectar un escaneo incompatible.

Ninguna revalidación vuelve a ejecutar los objetivos para agregar miembros. Un
mensaje llegado después, uno inicialmente excluido o uno que luego pasa a
cumplir el filtro nunca entra en ese plan. Para ampliar alcance se crea otro.

Si el universo considerado contiene al menos un mensaje pero todas las reglas
lo excluyen al crear, C6 persiste igualmente un plan explicable con estado
`invalidated`, selección congelada vacía, `selectedAtCreationCount=0`,
`selectedAtCreationSizeEstimateBytes=0`, `currentEligibleCount=0` y
`currentEligibleSizeEstimateBytes=0`. `excludedAtCreationCount` y
`excludedAtCreationSizeEstimateBytes` conservan el total exacto del universo no
vacío, junto con todas sus exclusiones. Registra un único evento `created` de
revisión 1 con `state=invalidated`, `removedCount=0` y `remainingCount=0`. El
recibo conserva `status=created`. Ese plan es terminal y no admite revalidación
ni cancelación. Si los objetivos no pueden resolver ningún miembro en la
fotografía declarada, se responde `target_not_found` sin crear plan; no se usa
un plan vacío para ocultar un objetivo obsoleto.

## 10. Modelos y estados cerrados

Los modelos de dominio C6 son inmutables, con `slots`, versiones exactas,
representaciones redactadas y sin diccionarios arbitrarios.

Estados públicos:

| Estado | Significado |
|---|---|
| `frozen` | selección original vigente y no reducida |
| `reduced` | uno o más miembros congelados fueron retirados |
| `invalidated` | el plan ya no puede reutilizarse |
| `cancelled` | Joa lo canceló; terminal |
| `expired` | venció por hora del servidor; terminal |

No existen `approved`, `executing`, `executed`, `reverted` ni equivalentes en
C6. La aprobación de ejecución pertenece a C7 y Limpieza Controlada.

Cada plan usa un ID `cleanup-plan-v1-<UUID v4>` y una revisión monotónica que
comienza en 1. Cada comando nuevo aceptado agrega exactamente un evento y avanza
una revisión. Repetir el mismo comando no avanza el ledger.

## 11. Creación, CAS e idempotencia

La solicitud de creación contiene:

```text
commandId: UUID v4
expectedMapRevision
expectedPolicyRevision
disposition: archive | trash
targets[]
temporalFilter
readState
excludedLabelIds[]
keepLatestPerFlow
```

El cliente no declara la hora del evento. Una vez resuelto que no es replay, el
servidor lee su reloj inyectable exactamente una vez dentro de la transacción y
llama `commandNow` a ese valor. En creación, el mismo `commandNow` determina el
corte civil de `olderThanDays`, `createdAt`, `recordedAt` y
`expiresAt=commandNow+86400 segundos`. En revalidación y cancelación determina
la prueba de expiración y `recordedAt`. Un replay exacto se resuelve sin depender
de una nueva lectura del reloj. La huella de
idempotencia cubre versión contractual, método en mayúsculas, ruta canónica
completa —incluido `planId`— y cuerpo validado. Ese conjunto se serializa
canónicamente y se resume con SHA-256.

Orden obligatorio:

1. validar Host, Origin, método, JSON, tamaño y modelo cerrado;
2. calcular la huella canónica;
3. abrir `BEGIN IMMEDIATE`;
4. resolver replay exacto o conflicto de `commandId` antes de exigir una
   fotografía nueva;
5. para un comando nuevo, materializar dentro de esa transacción una fotografía
   coherente y comprobar cuenta, puerta sintética, checkpoint e
   `input_revision`;
6. comparar revisiones, resolver objetivos y calcular selección, exclusiones y
   muestras;
7. insertar plan, objetivos, miembros, razones, muestras, evento y recibo en la
   misma transacción;
8. devolver el recibo de comando persistido con `canExecute: false`.

Un replay exacto puede resolverse aunque el inventario actual esté temporalmente
incompleto, porque no recalcula ni escribe. Sólo existe mientras cuenta, recibo y
plan sobrevivan; `delete_account_index` los elimina por cascada y el retry nunca
recrea la cuenta. Reutilizar `commandId` con otra huella —versión, método, ruta
incluido `planId`, o cuerpo— produce `command_id_conflict`. Una operación C6
nunca crea ni recrea `indexed_accounts`.

## 12. Revalidación monotónica

La revalidación recibe:

```text
commandId
expectedPlanRevision
expectedMapRevision
expectedPolicyRevision
```

Debe usar la fotografía actual completa y repetir CAS bajo `BEGIN IMMEDIATE`.
Sólo considera miembros incluidos al crear y todavía elegibles. Verifica:

- existencia del mensaje;
- pertenencia a la misma cuenta;
- vigencia de la semántica del objetivo original;
- cortes temporales UTC originales;
- estado de lectura original solicitado;
- etiquetas excluidas;
- todas las protecciones, contradicciones y revisiones D5 actuales.

Una fuente o flujo cuyo selector ya no puede resolverse con la misma semántica
invalida el plan completo; no se adivina un reemplazo por nombre o parecido. Un
mensaje desaparecido, recién protegido o que dejó de cumplir los criterios se
retira con motivo cerrado.

Si `keepLatestPerFlow` es mayor que cero, la revalidación resuelve primero el
universo actual completo alcanzado por la unión de objetivos originales. Cuenta
y limita ese universo antes de aplicar protección, fecha, lectura, etiquetas o
cuota. Si supera 100.000 produce `plan_too_large` y revierte la transacción
completa: no agrega evento ni retiro.

Recién después deriva los candidatos ordinarios que existen ahora y cumplen
protecciones y filtros originales, y recalcula sobre ellos la cuota. Incluye
mensajes posteriores a la creación y miembros inicialmente excluidos sólo para
consumir la cuota; nunca los agrega al plan. Los protegidos no consumen N. El
resultado se intersecta con los miembros congelados aún elegibles, de modo que
la regla sólo puede retirar miembros y nunca agregar ni reincorporar uno. Si
todos los objetivos
originales conservan su semántica, la cuota se agrupa por el `effectiveFlowId`
actual calculado por D4+D5 para cada candidato, incluso para un plan elegido por
remitente. Si un candidato no puede obtener un flujo efectivo coherente, la
operación responde `study_unavailable` sin escribir. Un objetivo `source` o
`flow` incompatible invalida antes de calcular la cuota, según la sección 8.

La reducción es monotónica:

- nunca incorpora un ID nuevo;
- nunca reincorpora un miembro retirado;
- `currentEligibleIds` siempre es subconjunto de la selección congelada;
- `reduced` no vuelve a `frozen`;
- si no queda ningún miembro, pasa a `invalidated`.

La fotografía original no se reescribe. Se agregan evento y retiros de miembros
append-only. Una revalidación aceptada sin cambios también registra la revisión
observada. El replay exacto se resuelve antes de exigir una fotografía actual.
Para un comando nuevo, un inventario incompleto responde error controlado y deja
el plan exactamente como estaba.

## 13. Cancelación y caducidad

La cancelación recibe `commandId` y `expectedPlanRevision`. El servidor asigna
`recordedAt`. Agrega un evento append-only, no borra la vista previa y compite
mediante CAS con una revalidación. Es idempotente por comando y terminal.

C6 v1 fija una validez de 24 horas exactas desde `createdAt`, calculada con un
reloj de servidor inyectable y persistida en UTC. Joa ni el navegador pueden
elegir, renovar o extender `expiresAt`.

`expired` se deriva cuando `serverNow >= expiresAt`; no necesita un proceso en
segundo plano. La precedencia terminal es:

```text
cancelled | invalidated
        antes que
expired
        antes que
reduced | frozen
```

Un plan vencido, cancelado o invalidado no se revalida ni se revive. Se crea un
plan nuevo.

Dentro de `BEGIN IMMEDIATE`, el orden para revalidar o cancelar es:

1. resolver replay exacto o conflicto de `commandId`;
2. capturar el único `commandNow` y derivar vencimiento;
3. aceptar un comando nuevo sólo si el estado efectivo es `frozen` o `reduced`;
4. comparar `expectedPlanRevision`;
5. persistir la única transición admitida.

Un comando nuevo sobre `expired`, `cancelled` o `invalidated` produce
`plan_expired` o `invalid_transition` sin evento. Cancelar después del
vencimiento nunca reemplaza `expired`; reintentar exactamente un comando antes
aceptado conserva su replay aunque el reloj o el estado hayan avanzado.

## 14. Disposición y tamaños

Cada plan contiene exactamente una intención inerte:

```text
archive
trash
```

No acepta una lista. Archivo y Papelera requieren planes separados.
Desuscripción no forma parte del agregado.

La respuesta separa:

```text
selectedAtCreationCount
selectedAtCreationSizeEstimateBytes
excludedAtCreationCount
excludedAtCreationSizeEstimateBytes
currentEligibleCount
currentEligibleSizeEstimateBytes
effectiveFreedBytes: null
```

Para `archive`, `storageEffect` es `none`. Para `trash`, es
`not_guaranteed`: mover a Papelera no demuestra liberación inmediata ni
definitiva. Ningún campo se denomina “espacio recuperado” o “ahorro”.

En creación, seleccionados y excluidos son conjuntos disjuntos cuya unión es el
universo considerado; sus conteos y tamaños deben cumplir esa suma exacta.
`currentEligibleCount` y `currentEligibleSizeEstimateBytes` comienzan iguales a
los valores seleccionados. Después suman esas mismas estimaciones congeladas
sólo para los miembros que todavía son elegibles; una revalidación no reescribe
tamaños históricos ni permite que ningún total vigente aumente.

C6 limita cada `sizeEstimateBytes` a `2.147.483.647` y todo total público o
persistido a `214.748.364.700.000` bytes. Este último valor es el máximo teórico
de 100.000 miembros y permanece por debajo del entero seguro máximo de
JavaScript y del entero con signo de SQLite. Toda suma se valida antes de
persistir o serializar. Un registro D1 que supere el límite individual, un
overflow o un total fuera del límite vuelve incoherente la fotografía y responde
`study_unavailable` sin escrituras ni truncamiento.

## 15. Muestras y enumeración exacta

El detalle conserva como máximo cinco muestras incluidas y cinco excluidas,
ordenadas por `receivedAt` descendente e ID local ascendente. Una muestra puede
contener únicamente:

```text
messageId local
receivedAt
senderName: string | null
senderAddress: string | null
subject: string | null
sizeEstimateBytes
sourceId
flowId
readState
exclusionReasons[]
```

Estos valores quedan congelados para que la vista previa sea reproducible. Son
metadatos privados aunque se almacenen localmente; su uso real continúa
bloqueado hasta proteger el reposo. No se duplican etiquetas completas,
cabeceras, URL de baja, cuerpo, HTML, snippet, MIME, adjuntos, destinatarios ni
IDs remotos.

La enumeración completa de miembros usa una ruta paginada; no intenta devolver
decenas de miles de IDs dentro del detalle. Cada elemento muestra ID local,
estado inicial, estado vigente, fecha, tamaño y códigos de motivo. El cursor es
opaco y no contiene metadatos reconstruibles.

## 16. Persistencia normalizada

D7 debe agregar la migración acumulativa v5 sin modificar las migraciones v1-v4
ni la tabla `plans` de Base Segura. Crea exactamente estas tablas C6, además de
los índices técnicos necesarios para cumplir consultas, unicidad y aislamiento:

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

Requisitos:

- FK desde cada plan a `indexed_accounts` con borrado en cascada;
- aislamiento por `account_key` en todas las claves;
- eventos append-only y revisión única por plan;
- recibo único por `(account_key, command_id)`;
- como máximo una fila `cleanup_plan_catalog_state` por cuenta con actividad C6,
  con revisión monotónica positiva de la colección de planes;
- cada recibo guarda huella, plan, tipo de resultado, revisión del evento y
  `removedCount` cuando corresponda, sin JSON genérico;
- miembros iniciales inmutables y retiros append-only;
- objetivos y razones tipados, normalizados y con restricciones SQL;
- fechas UTC, enteros no negativos y versiones exactas;
- ninguna FK de miembro a `indexed_messages`, para conservar la fotografía
  durante un nuevo escaneo;
- ningún `payload_json`, `snapshot_json`, BLOB, `extra` o encabezado genérico;
- base nueva y base migrada con el mismo esquema efectivo;
- rollback conjunto ante cualquier fallo de plan, evento, miembro o recibo.

La ausencia de fila representa `catalogRevision=0` y un `GET` nunca la crea. El
primer plan nuevo aceptado inserta revisión 1 dentro de su transacción. Cada
creación posterior, revalidación o cancelación nueva aceptada la incrementa
exactamente una vez en la misma transacción que su evento y recibo; un replay no
la incrementa. Una cuenta creada por D1 después de v5 tampoco necesita cambios
ni triggers C6 hasta ese primer plan. Si existen planes pero falta su fila, la
base es incoherente y la operación responde `study_unavailable`; no la repara
silenciosamente. La fila depende por FK de `indexed_accounts` y se elimina en la
misma cascada.

`start_full_index` conserva los planes; creación y revalidación quedan
bloqueadas mientras el nuevo escaneo no esté completo. Después, C6 compara la
fotografía nueva de forma conservadora. `delete_account_index` elimina por
cascada planes, eventos, muestras y recibos. Un retry anterior no recrea la
cuenta.

## 17. API local de Estudio v1

C6 usa un prefijo nuevo y no amplía silenciosamente las allowlists de v1 o v2:

```text
http://127.0.0.1:8765/api/v3/study
```

Rutas exactas:

| Método | Ruta | Resultado |
|---|---|---|
| `GET` | `/context` | contrato soportado y disponibilidad actual |
| `GET` | `/targets` | catálogo paginado de fuente, flujo, remitente y etiqueta |
| `POST` | `/plans` | crea y congela una vista previa |
| `GET` | `/plans` | historial paginado de resúmenes |
| `GET` | `/plans/{planId}` | detalle inmutable y estado vigente |
| `GET` | `/plans/{planId}/messages` | miembros y exclusiones paginados |
| `GET` | `/plans/{planId}/events` | transiciones append-only paginadas |
| `POST` | `/plans/{planId}/revalidate` | reduce o invalida sin efectos |
| `POST` | `/plans/{planId}/cancel` | cancela sin efectos |

### 17.1. Convenciones públicas

- JSON usa `camelCase` y rechaza campos extra;
- fechas y horas son RFC 3339 UTC terminadas en `Z`;
- fechas civiles usan `YYYY-MM-DD`;
- IDs, cursores y revisiones se tratan como opacos;
- colecciones son únicas y tienen orden contractual;
- números enteros rechazan booleanos y valores negativos;
- un cursor inválido no se interpreta como primera página;
- `mapRevision` cumple `map-v1-<64 hex>`, `policyRevision` es un entero no
  negativo y las revisiones de plan o comando son enteros positivos;
- IDs de fuente y flujo cumplen `effective-source-v1-<24 hex>` y
  `effective-flow-v1-<24 hex>`; remitentes, etiquetas y mensajes usan sus
  prefijos v1 más 64 hex;
- un cursor contiene como máximo 1.024 caracteres ASCII y la query completa no
  supera 4 KiB;
- cada parámetro de query permitido aparece como máximo una vez; duplicados,
  incluso con el mismo valor, producen `invalid_request`;
- todo texto visible procedente de METADATA contiene como máximo 16 KiB en
  UTF-8, el límite D3; una fotografía que lo contradice produce
  `study_unavailable` y nunca se trunca o persiste silenciosamente.

`GET /context` responde exactamente con este modelo:

```text
contractVersion: 1
dataMode: synthetic
timeZone: America/Argentina/Cordoba
planValiditySeconds: 86400
limits:
  maxTargets: 100
  maxExcludedLabels: 100
  maxConsideredMessages: 100000
  maxKeepLatestPerFlow: 10000
  maxMessageSizeEstimateBytes: 2147483647
  maxAggregateSizeEstimateBytes: 214748364700000
  maxTargetPageSize: 100
  maxPlanPageSize: 100
  maxMessagePageSize: 500
  maxEventPageSize: 100
  maxCursorChars: 1024
  maxQueryStringBytes: 4096
  maxVisibleMetadataBytes: 16384
  maxRequestBodyBytes: 65536
  maxIncludedSamples: 5
  maxExcludedSamples: 5
capabilities:
  studyRead: true
  targetRead: true
  planCreate: true
  planRevalidate: true
  planCancel: true
  systemLabelFilter: true
  customLabelFilter: false
  gmailConnection: false
  oauth: false
  externalNetwork: false
  realData: false
  messageMutation: false
  unsubscribe: false
  execute: false
availability:
  accountAvailable: bool
  inventoryState: not_started | running | paused | completed | requires_full_resync | failed | null
  completeSnapshotAvailable: bool
  currentMapRevision: map-v1-<64 hex> | null
  currentPolicyRevision: non-negative integer | null
  targetReadAvailable: bool
  planCreateAvailable: bool
  planRevalidateAvailable: bool
  blockerCodes[]
canExecute: false
```

`capabilities` describe qué implementa la versión, no prometen que cada comando
pueda aceptarse en ese instante. `availability` se calcula de forma cerrada: las
tres disponibilidades son `true` únicamente con cuenta, checkpoint `completed`
y fotografía C5 coherente; de lo contrario son `false`.
`completeSnapshotAvailable` comparte esa condición. Si la cuenta no existe,
`inventoryState`, ambas revisiones actuales son `null` y `blockerCodes` contiene
`account_unavailable`. Con cuenta pero inventario no completado, conserva su
estado, deja revisiones en `null` y usa `inventory_incomplete`. Con checkpoint
completo pero composición incoherente, usa `study_unavailable` y revisiones
`null`. Los códigos son únicos y siguen ese orden exacto. Las lecturas de planes
persistidos no dependen de esas tres banderas.

### 17.2. Catálogo de objetivos

`GET /targets` admite únicamente `kind`, `cursor` y `limit`. `kind` es opcional:
puede ser `source`, `flow`, `sender` o `label`, y su ausencia incluye los cuatro
tipos. `limit` es opcional, vale entre 1 y 100 y por defecto es 50. `cursor` se
omite sólo en la primera página.

La respuesta exacta contiene los tres campos comunes, `mapRevision`,
`policyRevision`, `kind` con el filtro efectivo o `null`, `items[]` y
`nextCursor: string | null`.

Los elementos son una unión cerrada:

```text
source:
  kind, targetId, displayName, messageCount

flow:
  kind, targetId, sourceId, displayName, messageCount

sender:
  kind, targetId, displayAddress, messageCount

label:
  kind, targetId, displayName, messageCount
```

Los textos visibles son metadatos locales y sus representaciones internas se
redactan. El orden ascendente exacto usa primero el rango `source=0`, `flow=1`,
`sender=2`, `label=3`; después el texto visible transformado con `casefold()` sin
quitar ni colapsar espacios; por último `targetId`. El catálogo no publica
selectores, `account_key`, IDs remotos ni huellas internas.

Los elementos `label` existen únicamente para `excludedLabelIds`. Un elemento
con `kind=label` nunca es un objetivo seleccionable dentro de `targets[]`.

### 17.3. Solicitud y selección pública

El cuerpo de `POST /plans` usa exactamente los campos de la sección 11. Cada
objetivo tiene `kind` y `targetId`, y `kind` se limita a `source`, `flow` o
`sender`; cada etiqueta excluida se identifica exclusivamente por su `targetId`
de catálogo dentro de `excludedLabelIds`. `temporalFilter` es una unión
discriminada y cerrada:

```text
all:
  kind: all

beforeDate:
  kind: beforeDate
  date: YYYY-MM-DD

dateRange:
  kind: dateRange
  onOrAfterDate: YYYY-MM-DD
  beforeDate: YYYY-MM-DD

olderThanDays:
  kind: olderThanDays
  days: integer 1..36500
```

Ninguna variante acepta los campos de otra. `targets[]` se canonicaliza por
`kind`, `targetId`; `excludedLabelIds[]`, por ID. Ambas colecciones rechazan
duplicados antes de calcular la huella.

La selección persistida y devuelta contiene:

```text
disposition
targets[]
targetSnapshots[]
temporalFilterRequested
resolvedOnOrAfterUtc | null
resolvedBeforeUtc | null
timeZone
readState
excludedLabelIds[]
excludedLabelSnapshots[]
keepLatestPerFlow
```

`targetSnapshots` es una unión cerrada, en el mismo orden canónico:

```text
source: kind, targetId, displayName
flow: kind, targetId, displayName
sender: kind, targetId, displayAddress
```

No publica la huella del selector. `excludedLabelSnapshots` contiene exactamente
`labelId` y `displayName`, ordenados por `labelId`. Estos snapshots no se
actualizan si cambia el mapa.

### 17.4. Resumen, detalle y eventos

Un resumen de plan contiene:

```text
planId
planRevision
state
createdAt
expiresAt
lastRevalidatedAt | null
disposition
selectedAtCreationCount
selectedAtCreationSizeEstimateBytes
excludedAtCreationCount
excludedAtCreationSizeEstimateBytes
currentEligibleCount
currentEligibleSizeEstimateBytes
storageEffect
effectiveFreedBytes: null
canExecute: false
```

`GET /plans` admite únicamente `state`, `cursor` y `limit`. `state` es opcional:
puede ser `frozen`, `reduced`, `invalidated`, `cancelled` o `expired`; su
ausencia incluye todos. `limit` es opcional, vale entre 1 y 100 y por defecto es
50. `cursor` se omite sólo en la primera página. Ordena por `createdAt`
descendente y `planId` ascendente.

La respuesta exacta contiene los tres campos comunes, `listingAsOf` fijado por
el servidor, `catalogRevision` entero no negativo, `state` con el filtro
efectivo o `null`, `items[]` y `nextCursor: string | null`.

El detalle agrega al resumen:

```text
selection
createdFromMapRevision
createdFromPolicyRevision
currentMapRevision: map-v1-<64 hex> | null
currentPolicyRevision: non-negative integer | null
includedSamples[]
excludedSamples[]
eventCount
recentEvents[]
warnings[]
```

Con fotografía actual completa, ambas revisiones actuales se informan juntas.
Durante inventario incompleto o una composición incoherente quedan ambas en
`null`; el detalle congelado continúa disponible y agrega
`current_snapshot_unavailable`. Nunca publica una revisión de mapa parcial ni
mezcla una revisión de política aislada con un mapa ausente.

`recentEvents` contiene como máximo diez elementos, en revisión descendente.
Cada evento público contiene exactamente:

```text
revision
type: created | revalidated | reduced | invalidated | cancelled
recordedAt
state
observedMapRevision: map-v1-<64 hex> | null
observedPolicyRevision: non-negative integer | null
removedCount
remainingCount
```

`created`, `revalidated`, `reduced` e `invalidated` conservan ambas revisiones
observadas; `cancelled` usa `null` porque no materializa el mapa. Los conteos son
enteros no negativos posteriores al evento. La creación usa `removedCount=0`;
una revalidación sin bajas usa `type=revalidated`; con bajas y miembros restantes
usa `reduced`; sin miembros usa `invalidated`. La expiración se explica mediante
`expiresAt` y no inventa un evento de background.

`GET /plans/{planId}/events` admite sólo `cursor` y `limit`. `limit` es opcional,
vale entre 1 y 100 y por defecto es 50; `cursor` se omite sólo en la primera
página. Ordena por revisión ascendente. La respuesta exacta contiene los tres
campos comunes, `planId`, `planRevision`, `items[]` y
`nextCursor: string | null`. El detalle no crece sin límite por revalidaciones
repetidas.

`warnings` usa exclusivamente `current_snapshot_unavailable`,
`map_changed_since_creation`, `policy_changed_since_creation` y
`selection_reduced`, en ese orden cuando más de uno aplica. Si falta fotografía
actual, no se emiten los dos códigos de cambio porque no existe comparación
coherente; `selection_reduced` sí puede conservarse desde el ledger. La
presentación traduce esos códigos; la API no persiste ni devuelve texto remoto o
libre.

### 17.5. Miembros paginados

`GET /plans/{planId}/messages` admite únicamente `state`, `cursor` y `limit`.
`state` es opcional, puede ser `all`, `selected`, `eligible`, `excluded` o
`removed` y por defecto es `all`. `limit` es opcional, vale entre 1 y 500 y por
defecto es 100; `cursor` se omite sólo en la primera página. Ordena por
`receivedAt` descendente y `messageId` ascendente.

Los predicados de cada filtro son exactos:

| Filtro | Predicado |
|---|---|
| `all` | todos los miembros considerados al crear, exactamente una vez |
| `selected` | `initialState=selected`, incluidos los hoy `eligible` o `removed` |
| `eligible` | `currentState=eligible` |
| `excluded` | `initialState=excluded`; su estado actual permanece `excluded` |
| `removed` | `currentState=removed` |

`all` es la unión disjunta por `messageId` de los inicialmente seleccionados y
excluidos. Un miembro retirado sigue perteneciendo a `selected` y además aparece
en `removed` cuando se consulta ese filtro; nunca se lo reclasifica como
excluido inicial.

La respuesta exacta contiene los tres campos comunes, `planId`,
`planRevision`, el `state` efectivo, `items[]` y
`nextCursor: string | null`.

Cada elemento contiene:

```text
messageId
initialState: selected | excluded
currentState: eligible | excluded | removed
receivedAt
sizeEstimateBytes
reasonCodes[]
```

No contiene `provider_message_id`, thread ID, remitente, asunto ni cabeceras.
Esos metadatos aparecen sólo en las muestras acotadas del detalle.

### 17.6. Cursores

Todo cursor queda ligado a ruta, filtros canónicos, límite lógico y fotografía
que originó la página. El catálogo se liga a `mapRevision` y `policyRevision`;
miembros y eventos, a `planRevision`; el historial general, a
`catalogRevision` y a un instante `listingAsOf` fijados juntos en la primera
página. El filtro de estado, la expiración y todos los campos del resumen
—conteos, tamaños, `lastRevalidatedAt`, estado persistido y disposición— se leen
contra esa misma revisión e instante en todas sus páginas. Todo comando nuevo C6
cambia `catalogRevision`; por eso una continuación posterior responde
`cursor_stale` en vez de mezclar resúmenes anteriores y nuevos. Reutilizar un
cursor en otra ruta o con otro filtro también se rechaza.

Si cambia la revisión necesaria para continuar sin mezclar fotografías, la API
responde `cursor_stale`; nunca reinicia silenciosamente desde la primera página.
El cursor es opaco, acotado y no contiene texto visible, IDs remotos, cuenta ni
metadatos reconstruibles.

### 17.7. Respuestas de comando

Los tres `POST` devuelven una unión discriminada y cerrada:

```text
create:
  status: created
  replayed: bool
  commandRevision
  planId

revalidate:
  status: revalidated
  replayed: bool
  commandRevision
  removedCount
  planId

cancel:
  status: cancelled
  replayed: bool
  commandRevision
  planId
```

Ninguna variante acepta campos extra. Un replay devuelve el mismo `status`,
`commandRevision`, `planId` y `removedCount` originales, con `replayed: true`;
no vuelve a calcular una selección aunque el agregado haya avanzado. El cliente
siempre relee `GET /plans/{planId}` después de cualquier éxito o replay para
obtener el detalle vigente y no mezcla el resultado histórico del comando con
el estado actual.

`commandRevision` es el entero positivo igual a la revisión del evento y del
plan creada por el comando original. Los `GET` y los tres `POST`, tanto nuevos
como replay, responden HTTP 200 cuando tienen éxito; no existen respuestas 201,
202 o 204 en C6 v1.

No existen rutas para aprobar, ejecutar, archivar, enviar a Papelera,
desuscribir, conectar, sincronizar, borrar índice ni modificar Gmail.

Toda respuesta exitosa, incluidos los tres sobres anteriores, declara en su
nivel superior:

```text
contractVersion: 1
dataMode: synthetic
canExecute: false
```

`/api/v2/context.capabilities.cleanupPlan` permanece `false`: describe la
superficie cerrada de Mapa Total y el frontend D6 vigente bloquea cualquier otro
valor. `/api/v3/study/context` es la fuente autoritativa de capacidades C6. D8
deberá componer ambos contextos en una misma integración; D7 no puede dejar D6
inutilizable entre integraciones.

## 18. Seguridad HTTP

Las rutas C6 reutilizan la política de seguridad local de C5, no su dispatcher
literal. D7 implementa una frontera v3 separada con allowlists exactas de path,
método y parámetros de consulta; no amplía ni relaja el middleware `/api/v2`,
que continúa rechazando queries. La frontera v3 prueba:

- servidor únicamente en `127.0.0.1:8765`;
- `Host` exacto `127.0.0.1:8765`;
- `GET` con Origin ausente o exacto `http://127.0.0.1:8765`;
- todo `POST` exige ese Origin, JSON y cuerpo máximo de 64 KiB;
- la query completa no supera 4 KiB y cada ruta admite sólo sus nombres de
  parámetro enumerados;
- cookies rechazadas y `credentials: "omit"` en el frontend;
- sin CORS, redirecciones, URL configurables ni recursos externos;
- `Cache-Control: no-store` en toda respuesta;
- JSON con claves duplicadas rechazadas;
- DTO cerrados con campos, enums, longitudes y cardinalidades acotados;
- logs y errores sin cuerpos, queries, IDs, direcciones, asuntos o paths;
- OpenAPI local sin Swagger, ReDoc ni assets remotos.

Un método o path no enumerado se rechaza antes de dominio y persistencia.

## 19. Errores públicos cerrados

Formato:

```json
{
  "contractVersion": 1,
  "dataMode": "synthetic",
  "canExecute": false,
  "error": {
    "code": "plan_revision_conflict",
    "message": "El plan cambió. Actualizá la vista antes de reintentar."
  }
}
```

El sobre de error es cerrado y contiene exactamente esos cuatro campos de nivel
superior. El catálogo v1 de códigos es exactamente:

| HTTP | Código |
|---|---|
| 400 | `invalid_request`, `invalid_cursor` |
| 403 | `invalid_local_origin` |
| 404 | `route_not_found`, `target_not_found`, `plan_not_found` |
| 405 | `method_not_allowed` |
| 409 | `map_revision_conflict`, `policy_revision_conflict`, `plan_revision_conflict`, `command_id_conflict`, `cursor_stale`, `invalid_transition`, `plan_expired` |
| 413 | `payload_too_large`, `plan_too_large` |
| 415 | `json_required` |
| 422 | `unsupported_target`, `invalid_filter` |
| 503 | `study_unavailable`, `inventory_incomplete`, `account_unavailable` |
| 500 | `internal_error` |

Cada mensaje es fijo por código. No concatena excepciones, SQL, cuenta, token,
dirección, asunto, selector, revisión interna ni payload remoto.

## 20. Límites operativos

- 100 objetivos de selección por plan;
- 100 etiquetas excluidas;
- 100.000 miembros considerados como máximo, incluidos más excluidos;
- 10.000 como máximo en `keepLatestPerFlow`;
- 2.147.483.647 bytes estimados como máximo por mensaje y
  214.748.364.700.000 por total;
- 500 miembros por página HTTP;
- 100 objetivos por página de catálogo y 100 eventos o planes por página;
- 1.024 caracteres ASCII por cursor y 4 KiB por query;
- cinco muestras incluidas y cinco excluidas;
- 64 KiB por cuerpo JSON;
- una sola cuenta por operación;
- 24 horas de vigencia.

Superar 100.000 mensajes en el universo alcanzado por los objetivos produce
`plan_too_large` antes de persistir incluidos, excluidos o razones y exige acotar
objetivos; no se trunca silenciosamente. Los límites forman parte de la versión
contractual.

## 21. Privacidad y olvido

C6 persiste intención de Joa, membresía, exclusiones y un conjunto mínimo de
muestras. Esos datos son privados y no se vuelven anónimos por usar hashes o
IDs opacos.

Durante D7:

- todos los registros, direcciones y dominios son sintéticos `.example`;
- la base vive en ubicación de prueba o bajo `data/`, ignorada por Git;
- no se solicitan credenciales ni se abre OAuth;
- no existe red, cliente Gmail, navegador ni SDK externo;
- no se registran metadatos en consola o excepciones;
- no se agregan dependencias.

Antes de datos reales deben protegerse conjuntamente índice D1, selectores D5,
planes C6 y muestras con la política aprobada de ubicación, ACL, cifrado
autenticado, retención, respaldo y borrado. La autorización actual no satisface
esa puerta.

Loopback, `Host`, `Origin`, ausencia de CORS y `credentials: "omit"` reducen
accesos web accidentales, pero no autentican otro proceso local ni separan por sí
solos usuarios del mismo equipo. Antes de exponer datos reales, MAIN y Joa deben
aprobar además un modelo de amenaza local y una frontera por usuario y sesión
que cubra al menos: identidad del proceso/usuario, capacidad aleatoria no
persistida en URLs o logs, renovación y revocación, permisos del archivo local y
comportamiento ante procesos hostiles. D7 sintética no implementa ni simula esa
decisión; la ausencia de esa frontera bloquea Gmail y datos reales.

## 22. Pruebas obligatorias de D7

La futura entrega especialista debe demostrar con datos sintéticos:

1. modelos cerrados, inmutables, versionados y redactados;
2. migración v5 equivalente en base nueva y migrada desde v4;
   ausencia de estado de catálogo como revisión 0, primer comando que inserta 1,
   GET sin escritura y cuenta D1 posterior a v5 sin trigger C6;
3. conservación exacta de `messages`, `plans`, D1, D5 y recibos C5;
4. cuenta inexistente, mapa parcial y checkpoint incompleto sin escritura;
   contexto con disponibilidad cerrada y lectura de historia congelada durante
   un escaneo, con revisiones actuales nulas y advertencia explícita;
5. selección por fuente, flujo y sender ID opaco;
   función pública canónica de remitente con mayúsculas y espacios equivalentes,
   ausencia aceptada e incoherencia presente rechazada;
6. solapamientos deduplicados y aislamiento entre cuentas;
7. fecha exclusiva, rango y fórmula exacta de antigüedad civil convertidos a
   UTC;
8. estado `read`/`unread` basado sólo en `UNREAD`;
9. etiqueta excluida mediante ID local y no valor crudo del cliente;
10. `keepLatestPerFlow` después de filtros y sin consumir protegidos;
11. exclusión de cada protección D5, `SENT`, `DRAFT`, `TRASH`, estrella e
    importancia;
12. múltiples razones únicas, ordenadas y persistidas;
    tabla exacta de acumulación para protección nueva, cambio de alcance y
    filtros concurrentes;
13. selección y exclusiones congeladas con miembros futuros ausentes;
    creación con selección vacía por protección o filtros persistida como
    `invalidated`, sin confundirla con objetivo inexistente, y cero en
    `keepLatestPerFlow` demostrado como regla desactivada; los totales
    seleccionados quedan en cero y los excluidos conservan el universo exacto;
14. ningún miembro inicialmente excluido incorporado después;
15. revalidación sin cambios, reducción parcial e invalidación vacía;
16. cambio estructural de fuente o flujo que invalida sin adivinar;
17. inventario incompleto durante revalidación que deja el plan intacto;
18. reducción monotónica que nunca reincorpora miembros;
19. cancelación terminal, CAS y replay exacto;
20. expiración a las 24 horas con reloj inyectable y sin background;
21. concurrencia de creación, revalidación y cancelación;
22. rollback conjunto ante fallos de miembros, evento o recibo;
23. Archivo y Papelera como intenciones únicas, sin desuscripción;
24. conteos y tamaños exactos con `effectiveFreedBytes=null`;
    techo individual, techo agregado y overflow rechazados sin escritura;
25. muestras limitadas a la allowlist y paginación determinista; filtros
    `all`, `selected`, `eligible`, `excluded` y `removed` con sus predicados
    exactos y el solapamiento histórico esperado entre `selected` y `removed`;
26. IDs locales en HTTP y ausencia de `account_key` e IDs remotos;
27. Host, Origin, cookies, JSON, tamaño, queries duplicadas, CORS y `no-store`;
28. errores cerrados y redactados;
29. borrado de cuenta que elimina C6 y retry que no la recrea;
30. escaneo completo que conserva fotografía e impide falsa reducción parcial;
31. API v1 y las nueve rutas v2 preexistentes compatibles, además de las nueve
    rutas v3 exactas y aisladas;
32. `gmailConnection`, `oauth`, `externalNetwork`, `realData`,
    `messageMutation`, `unsubscribe` y `execute` en `false`;
33. ausencia de Gmail, OAuth, red, credenciales, datos reales y artefactos;
34. la misma `commandId` usada en otra ruta, otro plan o con otro cuerpo que
    produce conflicto y nunca replay cruzado;
35. el límite de 100.000 aplicado al universo alcanzado por objetivos antes de
    toda protección o filtro, incluso si la mayoría queda excluida;
36. replay, reloj, estado terminal y CAS resueltos bajo el mismo bloqueo, con
    carreras de cancelar, revalidar y vencer;
37. eventos acotados en detalle, paginación estable y cursor obsoleto rechazado;
    `catalogRevision` que evita mezclar resúmenes si otro comando ocurre entre
    páginas;
38. sobres de éxito y error cerrados, catálogos exactos y
    `/api/v2/context.capabilities.cleanupPlan=false` durante D7;
39. recálculo de `keepLatestPerFlow` cuando desaparecen miembros conservados,
    llegan mensajes nuevos o cambia una protección, sin incorporar ni
    reincorporar miembros;
40. replay exacto de creación, revalidación y cancelación durante inventario
    `running` o `requires_full_resync`, y cuenta eliminada que no se recrea;
41. fórmulas estables de IDs locales y `label` rechazado dentro de `targets[]`;
42. páginas con revisión o `listingAsOf` explícitos, orden total exacto de tipos
    y texto en objetivos, y defaults cerrados;
43. catálogo de etiquetas limitado a la allowlist de sistema, con etiquetas
    personalizadas ausentes y rechazadas como input;
44. variantes temporales, snapshots, disponibilidad dinámica, advertencias y
    eventos con sus DTO exactos y sin campos extra;
45. un único `commandNow` por comando nuevo, replay independiente del reloj,
    nulabilidad exacta de muestras, `commandRevision` y HTTP 200 contractual;
46. pool de revalidación limitado a 100.000 y flujo efectivo actual coherente;
47. pytest específico y global, Ruff, mypy, barrera de seguridad,
    `scripts/check.ps1`, HTTP loopback y `git diff --check`.

## 23. Puntos de detención

D7 no puede comenzar o continuar si:

- Joa no acepta C6;
- `main` no tiene un SHA limpio posterior al contrato y su prompt;
- se pretende ampliar o reutilizar los JSON abiertos de planes v1;
- una creación no usa fotografía coherente y CAS transaccional;
- una revalidación puede agregar o reincorporar mensajes;
- un mensaje protegido puede entrar mediante override;
- se pretende aceptar direcciones, cuentas o IDs remotos como selectores HTTP;
- se necesita modificar el contrato C5 silenciosamente;
- aparecen rutas de aprobación o ejecución;
- se requieren Gmail, OAuth, red, credenciales o datos reales;
- se necesita una dependencia nueva;
- una prueba abre navegador, conecta un servicio o usa datos privados;
- el diff contiene bases, builds, cachés, secretos o `grafo.txt`.

## 24. Condición de terminado y desbloqueo

C6 quedó estabilizado mediante esta secuencia:

1. Joa aceptó expresamente este contrato;
2. documentación y estados dejaron de presentar C6 como pendiente;
3. MAIN ejecutó las validaciones documentales y la batería global;
4. el cambio queda consolidado por el commit que contiene este estado;
5. `docs/WORKTREE_REGISTRY.md` continúa sin registrar un D7 inexistente.

El próximo artefacto es el prompt autosuficiente D7 redactado desde este contrato
y el SHA limpio resultante. La existencia de C6 no crea el worktree, no
implementa D7 y no habilita D8, Gmail real ni Limpieza Controlada.
