# Contrato de API de Mapa Total v1

Estado: contrato C5 estabilizado por MAIN el 27 de agosto de 2026 para una
implementación exclusivamente local y sintética. No habilita D6 hasta que el
backend, los fixtures contractuales y la batería HTTP estén integrados en un
commit limpio.

Autoridad: `CONTRATO_MVP.md`, `SECURITY_PRIVACY_V1.md`, los contratos D1-D5 y
la planificación durable de C5. Ante una contradicción de seguridad prevalece
`SECURITY_PRIVACY_V1.md`.

Este contrato no autoriza OAuth, Gmail real, credenciales, red externa, datos
privados, adaptadores productivos, modificación de mensajes, planes reales,
desuscripción, publicación ni despliegue.

## 1. Objetivo y frontera

C5 compone en una única vista pública:

```text
índice D1 + checkpoint D3 + políticas D5
              ↓ fotografía SQLite coherente
       clasificación automática D4
              ↓
       aplicación de políticas D5
              ↓
     proyección tipada de Mapa Total
              ↓
         API local `/api/v2`
```

La API debe permitir que una futura interfaz D6:

- distinga metadatos observados, inferencias automáticas y decisiones de Joa;
- recorra fuentes y flujos sin mezclarlos;
- vea confianza, evidencia, suscripción y protecciones;
- conozca el estado del inventario y si la vista es parcial;
- registre y deshaga únicamente las siete decisiones admitidas por D5;
- detecte una vista obsoleta antes de persistir una corrección.

`/api/v1` permanece congelada como Base Segura. C5 usa `/api/v2` porque elimina
conceptos de limpieza que no pertenecen a Mapa Total y cambia la forma pública.
No se cambian silenciosamente los DTO existentes.

## 2. Invariantes públicas

1. Toda respuesta declara `contractVersion: 1` y `dataMode: "synthetic"`.
2. La `account_key` interna nunca sale por HTTP ni se deriva de un correo.
3. Las colecciones son deterministas, únicas y ordenadas.
4. Las fechas son RFC 3339 en UTC y los tamaños son enteros no negativos.
5. Los valores `automatic*` nunca son reemplazados por valores efectivos.
6. La confianza efectiva nunca mejora la automática.
7. La protección efectiva nunca debilita la automática.
8. `reviewRequired` y `hardExcluded` permanecen separados de `protected`.
9. Un checkpoint distinto de `completed` se presenta como mapa parcial.
10. No se presenta una suscripción agregada ni una intención única de fuente.
11. `totalBytes` es volumen estimado indexado; nunca espacio recuperable.
12. No existen candidatos, recomendaciones, Archivo, Papelera ni ejecución.
13. Los errores exponen códigos cerrados, nunca excepciones o payloads internos.
14. Ninguna ruta inicia OAuth, red, inventario real o una acción sobre Gmail.

## 3. Fotografía coherente de entrada

Las lecturas públicas actuales de D1 y D5 abren transacciones independientes.
C5 requiere una operación nueva de repositorio que, con una sola conexión y un
solo `BEGIN`, materialice:

```text
account_exists
indexed_account_keys: tuple[str, ...]
fixture_version: str | None
records: tuple[IndexedMessageRecord, ...]
checkpoint: SyncCheckpoint | None
active_policies: tuple[ActivePolicy, ...]
policy_history: tuple[PolicyEvent, ...]
policy_revision: int
input_revision: identificador opaco y determinista
```

Reglas:

- `policy_revision` es el máximo evento del ledger, incluso si un undo deja cero
  políticas activas;
- cuenta inexistente implica registros y políticas vacíos, checkpoint ausente y
  revisión cero;
- una cuenta existente y vacía no se confunde con una cuenta inexistente;
- `indexed_account_keys` contiene el conjunto completo, único y ordenado de
  cuentas del índice, y `fixture_version` el marcador observado dentro de la
  misma transacción;
- registros, checkpoint, políticas y revisión pertenecen a la misma cuenta y a
  la misma fotografía SQLite;
- `input_revision` cambia si cambia cualquier fila relevante del índice, el
  checkpoint, el ledger de políticas, `map_fixture_version` o el conjunto
  completo de `indexed_accounts`;
- la representación del snapshot sólo muestra contadores, versiones y estados.

La clasificación y aplicación de políticas ocurren después de cerrar la
transacción sobre las tuplas inmutables ya materializadas.

`mapRevision` se deriva de `input_revision`, de las versiones de los modelos
D1, D4 y D5 y de una constante `MAP_COMPOSITION_VERSION` mediante una
serialización canónica y SHA-256. Todo cambio semántico de composición debe
incrementar esa constante aunque no cambien los modelos de dominio. Tiene el formato
`map-v1-<hex>` y se trata como opaco. No contiene direcciones, asuntos, IDs
remotos ni otra información reconstruible.

C5 agrega una migración acumulativa para un ledger mínimo de idempotencia HTTP.
Por cada comando aceptado guarda únicamente cuenta opaca, `commandId`, versión
de contrato y la huella SHA-256 de la solicitud pública canónica. No guarda el
JSON, nombres, direcciones, IDs visibles duplicados ni selectores genéricos. La
fila se inserta en la misma transacción que el evento D5 y se elimina por
cascada al borrar la cuenta.

### 3.1. Puerta sintética ejecutable

La aplicación activa de este corte usa exclusivamente la constante interna
`SYNTHETIC_MAP_ACCOUNT_KEY = "synthetic-map-v1"` y el marcador versionado
`map_fixture_version` de `app_meta`. Nunca elige “la primera cuenta” de SQLite.

Antes de responder `dataMode: "synthetic"`, C5 verifica conjuntamente:

- marcador y versión exactos del fixture;
- existencia de esa cuenta opaca y ausencia de otra cuenta indexada;
- todos los remitentes y valores con forma de correo bajo `.example`;
- todo dominio autenticado, `List-ID` y host de URL bajo `.example`;
- ausencia de cuerpos, snippets, MIME, adjuntos y destinatarios por esquema;
- checkpoint y registros pertenecientes a la cuenta fija.

Si una condición no se cumple, responde `map_unavailable` y no proyecta filas.
El marcador no convierte datos en sintéticos: es sólo una condición adicional
a la validación completa. Esta puerta forma parte de la fotografía coherente.
Toda escritura C5 vuelve a comprobarla dentro del mismo `BEGIN IMMEDIATE` que
revalida `input_revision` y persiste el evento; dejar de cumplirla aborta la
transacción sin escribir.

## 4. Composición

C5 ejecuta exactamente:

```python
classification = classify_indexed_records(snapshot.records)
effective = apply_local_policies(
    account_key,
    snapshot.records,
    classification,
    snapshot.active_policies,
)
```

Después une cada resultado con su `IndexedMessageRecord` por
`provider_message_id`. Un registro ausente, duplicado o perteneciente a otra
cuenta invalida la composición completa mediante un error controlado.

Derivaciones permitidas:

- cantidad de mensajes y flujos;
- primera y última fecha;
- suma de `size_estimate_bytes`;
- cantidad protegida, en revisión y excluida;
- remitentes y dominios de los miembros reales del resultado efectivo;
- volumen mensual exacto por `YYYY-MM`.

No se infiere una etiqueta humana de frecuencia. `monthlyVolume` contiene
hechos contados y evita inventar categorías como “diario” o “semanal”. En una
partición, remitentes y dominios se calculan desde los mensajes asignados a esa
fuente efectiva; nunca se copia completa la identidad automática original.

`senders` conserva los valores `sender_address` observados en D1, únicos por
igualdad exacta y ordenados por `casefold` e igualdad original. `domains` es la
unión en minúsculas de `authenticated_domain` y de la parte posterior al último
`@` de esos remitentes. C5 no reutiliza funciones privadas ni heurísticas de D4
para producir estas listas.

## 5. Rutas activas

Base: `http://127.0.0.1:8765/api/v2`.

| Método | Ruta | Resultado |
|---|---|---|
| `GET` | `/context` | modo, versión y capacidades efectivamente habilitadas |
| `GET` | `/connection` | estado de conexión sintético, sin cuenta ni acciones |
| `GET` | `/sync` | estado de la fotografía de inventario sintético |
| `GET` | `/index` | presencia, versión y volumen del índice sintético |
| `GET` | `/map` | resumen y fuentes efectivas |
| `GET` | `/map/sources/{sourceId}` | detalle, flujos, evidencia y muestra METADATA |
| `GET` | `/decisions` | historial local redactado y estado de binding |
| `POST` | `/decisions` | registra una decisión D5 sobre la revisión esperada |
| `POST` | `/decisions/{decisionId}/undo` | agrega un undo lógico |

No existen rutas activas para conectar, autorizar, escanear, pausar, reanudar,
refrescar, revocar, olvidar, borrar el índice, crear planes o ejecutar acciones.
Esas fronteras necesitan contratos y autorizaciones posteriores.

## 6. Contexto y capacidades

`GET /context` responde:

```json
{
  "contractVersion": 1,
  "dataMode": "synthetic",
  "appVersion": "0.1.0",
  "account": {"state": "synthetic", "displayAddress": null},
  "capabilities": {
    "mapRead": true,
    "policyWrite": true,
    "policyUndo": true,
    "gmailConnection": false,
    "oauth": false,
    "externalNetwork": false,
    "realData": false,
    "syncControl": false,
    "cleanupPlan": false,
    "messageMutation": false,
    "unsubscribe": false,
    "execute": false
  }
}
```

Los booleanos describen rutas realmente montadas. No son promesas futuras y no
pueden calcularse desde el frontend.

`GET /connection` responde únicamente `state: "synthetic"`,
`displayAddress: null` y las capacidades de conexión en `false`. `GET /index`
responde `state: "synthetic_fixture"`, `fixtureVersion`, `schemaVersion`,
`messageCount`, `partial` y `canDelete: false`. Ninguno expone cuenta, path,
clave, checkpoint interno ni una ruta de borrado.

## 7. Estado de sincronización

`GET /sync` y el campo `sync` del mapa exponen únicamente:

```text
state: not_started | running | paused | completed |
       requires_full_resync | failed
mode: full | partial | null
processedCount: int
startedAt: datetime | null
updatedAt: datetime | null
errorCode: string cerrado | null
partial: bool
```

No se exponen `account_key`, `scan_id`, `page_token` ni `history_id`. `partial`
es `false` sólo cuando el checkpoint está `completed`; en cualquier otro estado
es `true`. Un error remoto crudo nunca reemplaza `errorCode`.

## 8. Proyección del mapa

`GET /map` contiene:

```text
contractVersion
dataMode
mapRevision
policyRevision
sync
summary
policyReview
sources[]
```

`summary` contiene:

```text
messageCount
sourceCount
flowCount
protectedMessageCount
reviewRequiredMessageCount
hardExcludedMessageCount
totalBytes
firstSeen
lastSeen
```

`policyReview` contiene el total y los bindings cuyo estado no es `EXACT` ni
`REBOUND`. Cada elemento publica sólo `decisionId`, `status` y los IDs efectivos
actuales; no expone selectores históricos ni metadatos privados.

### 8.1. Fuente efectiva

Cada fuente de `/map` y del detalle contiene:

```text
id
automaticSourceIds[]
automaticDisplayName
effectiveDisplayName
automaticRubro
effectiveRubro
automaticConfidence
effectiveConfidence
messageCount
flowCount
protectedMessageCount
reviewRequiredMessageCount
hardExcludedMessageCount
totalBytes
firstSeen
lastSeen
senders[]
domains[]
monthlyVolume[]
protection
automaticEvidence[]
effectiveEvidence[]
decisionIds[]
structuralDecisionIds[]
flows[]
```

`monthlyVolume` agrupa cada `received_at` por fecha civil de
`America/Argentina/Cordoba`, se ordena por mes ascendente y contiene `month`,
`messageCount` y `totalBytes`. Fuentes se ordenan por `messageCount`
descendente, `effectiveDisplayName` normalizado e `id` ascendente.

### 8.2. Flujo efectivo

Cada flujo contiene:

```text
id
sourceId
automaticFlowId
automaticDisplayName
effectiveDisplayName
automaticIntention
effectiveIntention
subscription
automaticConfidence
effectiveConfidence
messageCount
protectedMessageCount
reviewRequiredMessageCount
hardExcludedMessageCount
totalBytes
firstSeen
lastSeen
protection
automaticEvidence[]
effectiveEvidence[]
decisionIds[]
structuralDecisionIds[]
```

No contiene un rubro propio ni una recomendación. Flujos se ordenan por
`messageCount` descendente, `effectiveDisplayName` normalizado e `id`.

### 8.3. Protección

La proyección común `protection` contiene:

```text
automatic: Proteccion
effective: Proteccion
protected: bool
reviewRequired: bool
hardExcluded: bool
reasons: PolicyProtectionReason[]
```

Los motivos son únicos y ordenados. `SENT`, `DRAFT` y `TRASH` permanecen como
exclusión dura. Una política manual no puede eliminar motivos automáticos.

### 8.4. Evidencia

La evidencia es una unión cerrada:

```text
classification:
  kind, code, label, detail, strength, origin

policy:
  kind, code, decisionId
```

`automaticEvidence` contiene sólo evidencia D4. `effectiveEvidence` conserva
toda evidencia automática y agrega evidencia de políticas aplicadas. La API no
convierte inferencias en hechos ni oculta contradicciones.

### 8.5. Detalle y muestras

`GET /map/sources/{sourceId}` devuelve la misma fuente más `recentMessages`,
con un máximo de cinco elementos ordenados por fecha descendente e ID ascendente.

Cada muestra contiene exclusivamente:

```text
id
receivedAt
senderName
senderAddress
subject
labelIds[]
category
sizeEstimateBytes
sourceId
flowId
automaticRubro
effectiveRubro
automaticIntention
effectiveIntention
subscription
automaticConfidence
effectiveConfidence
protection
```

`id` es un identificador local `message-v1-<hex>` derivado mediante SHA-256 de
la cuenta opaca y `provider_message_id`; el ID remoto no sale por HTTP. El
servidor conserva el mapeo únicamente dentro de la fotografía actual para
resolver una decisión sobre mensaje.

No contiene cuerpo, HTML, snippet, MIME, adjuntos, destinatarios, cabeceras
genéricas, URL de baja, tokens ni errores remotos.

## 9. Taxonomías

C5 reutiliza exactamente los enums vigentes; no los traduce ni amplía:

- `Rubro`: Medios y contenido; Software y servicios digitales; Comercio y
  compras; Finanzas; Trabajo y educación; Salud y gobierno; Viajes y
  entretenimiento; Social y comunidades; Servicios domésticos; Personal;
  Desconocido.
- `Intencion`: Seguridad; Documento o comprobante; Operativo o soporte;
  Notificación; Informativo o editorial; Promocional o venta; Comunicación
  personal; Sospechoso; Desconocido.
- `Suscripcion`: Confirmada; Probable; No corresponde; Baja solicitada;
  Posible incumplimiento; Desconocido.
- `Confianza`: Alta; Media; Baja; Contradictoria.
- `Proteccion`: Crítica; Documental; Elegida por el usuario; Ordinaria;
  Revisión obligatoria.

Una ampliación requiere versionar contrato y tipos. El frontend no replica sus
reglas de precedencia.

## 10. Decisiones públicas

Todo `POST` usa un modelo cerrado con `extra=forbid` y contiene:

```text
commandId: UUID v4
occurredAt: datetime UTC
expectedMapRevision: map-v1-...
expectedPolicyRevision: int >= 0
type: discriminante cerrado
```

Una decisión nueva agrega `decisionId: UUID v4` y opcionalmente
`supersedesDecisionIds[]`. La cuenta y los selectores internos se resuelven en
el servidor desde la fotografía esperada; nunca llegan desde el navegador.

Tipos admitidos:

| `type` | Campos propios |
|---|---|
| `setSourceDisplayName` | `sourceId`, `displayName` |
| `setSourceRubro` | `sourceId`, `rubro` |
| `setFlowDisplayName` | `flowId`, `displayName` |
| `setFlowIntention` | `flowId`, `intention` |
| `mergeSources` | `sourceIds` con al menos dos fuentes automáticas |
| `partitionSource` | `sourceId`, `groups` completos y disjuntos |
| `protectTarget` | `target` cerrado |

`target` es exactamente una de estas formas:

```json
{"kind": "source", "sourceId": "effective-source-v1-..."}
{"kind": "flow", "flowId": "effective-flow-v1-..."}
{"kind": "message", "messageId": "message-v1-..."}
{"kind": "sender", "senderAddress": "boletin@ejemplo.example"}
{"kind": "label", "labelId": "IMPORTANT"}
```

Una partición usa `groups: [{"anchors": [...]}]`; cada ancla es exactamente
`flow`, `message` o `sender` con la misma forma anterior. Los grupos deben ser
no vacíos, completos, disjuntos y cubrir una vez todas las anclas canónicas de
la fuente. MAIN resuelve cada ID visible al descriptor o selector D5 actual y
rechaza cualquier objetivo que no pertenezca a la fuente indicada.

Quedan prohibidos tipos genéricos, selectores D5 serializados por el cliente,
`accountKey`, reglas por dominio, “confiable”, “ignorar”, “spam”, desprotección,
notas libres y valores fuera de las taxonomías.

Los nombres visibles tienen entre 1 y 120 caracteres después de normalizar
espacios. El cuerpo JSON no supera 64 KiB. IDs y colecciones tienen límites
explícitos en los modelos HTTP; una partición no puede exceder 100 grupos ni
1.000 anclas y una unión no puede exceder 100 fuentes.

El JSON se decodifica rechazando claves duplicadas antes de Pydantic. La huella
canónica usa método en mayúsculas, path normalizado, versión de contrato y el
modelo validado: fechas UTC terminadas en `Z`, nombres con espacios
normalizados, enums por valor y colecciones únicas ordenadas. Se serializa en
UTF-8 con claves ordenadas y separadores compactos antes de aplicar SHA-256.

## 11. Revisión, idempotencia y atomicidad de escritura

Orden obligatorio de un comando:

1. validar Host, Origin, método, tipo y tamaño;
2. materializar el cuerpo cerrado;
3. calcular la huella de la solicitud pública canónica;
4. obtener la fotografía coherente actual para resolver el pedido;
5. comparar `expectedMapRevision` y `expectedPolicyRevision`;
6. resolver IDs públicos a selectores actuales;
7. construir el comando D5 y ejecutar `prepare_policy_decision`;
8. ingresar a una operación C5 del repositorio con `BEGIN IMMEDIATE`;
9. volver a buscar bajo ese lock el recibo y el evento por `commandId`: un
   recibo con la misma huella devuelve replay antes del CAS; otra huella es
   conflicto; un recibo sin evento es corrupción; un evento sin recibo es una
   colisión con un comando interno y también es conflicto;
10. volver a materializar bajo el lock la puerta sintética y la fotografía,
    incluida la versión del fixture y todas las cuentas indexadas;
11. comparar otra vez `input_revision` y la revisión de políticas esperadas;
12. validar el preparado D5 contra las políticas activas actuales y persistir
    evento D5 y recibo HTTP en esa misma transacción;
13. recomponer y devolver las revisiones nuevas.

La implementación puede hacer un lookup previo sólo como optimización, pero la
decisión autoritativa de replay siempre se repite bajo `BEGIN IMMEDIATE` antes
del CAS. No puede abrir una carrera entre la revisión del mapa y el commit. Si
cambió el índice, checkpoint, ledger, conjunto de cuentas, marcador de fixture
o topología, no escribe y responde conflicto.

Un replay exacto devuelve el evento original con `replayed: true` aunque las
revisiones hayan avanzado o el ID efectivo ya no exista. El recibo permite
resolverlo antes de consultar la topología actual.

La huella cubre el método, la ruta —incluido el `decisionId` de un undo— y todo
el cuerpo canónico, incluidos `expectedMapRevision` y
`expectedPolicyRevision`. Un retry debe repetir exactamente esa solicitud.
Reutilizar `commandId` con otra huella produce `command_id_conflict`. Dos
comandos nuevos sobre la misma revisión no pueden ser aceptados: exactamente
uno avanza el ledger. Un recibo sin evento es corrupción y produce un error
controlado. Un evento D5 anterior o interno sin recibo C5 es válido, pero un
pedido HTTP que reutilice su `commandId` se rechaza como conflicto y nunca se
presenta como replay.

La respuesta exitosa contiene:

```text
status: applied
replayed: bool
decisionId
policyRevision
mapRevision
bindingStatus: PolicyBindingStatus | null
```

`bindingStatus` puede ser `null` en un replay cuya decisión ya quedó inactiva;
D5 no persiste un binding histórico que permita inventar ese estado. El cliente
vuelve a leer el mapa; la respuesta no duplica toda la proyección.

## 12. Undo

`POST /decisions/{decisionId}/undo` recibe:

```text
commandId
occurredAt
expectedMapRevision
expectedPolicyRevision
```

El `decisionId` de la ruta debe existir, pertenecer a la cuenta local y estar
activo para un comando nuevo. El undo es un evento append-only y no borra
historia. Replay exacto conserva la semántica de D5.

## 13. Historial público

`GET /decisions` se ordena por revisión ascendente. Cada evento publica:

```text
decisionId | null para un evento undo
commandId
type
revision
occurredAt
active
undoable
targetDecisionId | null
supersedesDecisionIds[]
bindingStatus | null
currentTargetIds[]
```

El valor visible usa una unión cerrada por `type`:

| `type` | Proyección adicional |
|---|---|
| `setSourceDisplayName` | `sourceId`, `displayName` |
| `setSourceRubro` | `sourceId`, `rubro` |
| `setFlowDisplayName` | `flowId`, `displayName` |
| `setFlowIntention` | `flowId`, `intention` |
| `mergeSources` | `sourceIds` observados |
| `partitionSource` | `sourceId`, `groupCount` y resúmenes redactados de grupos |
| `protectTarget` | resumen redactado del objetivo observado |
| `undoPolicy` | sólo `targetDecisionId` |

No expone `account_key`, selectores, anclas históricas, direcciones incluidas en
selectores, relaciones internas ni payloads de persistencia. Los valores
visibles necesarios para explicar nombres, rubros e intenciones se proyectan en
una unión cerrada por `type`.

Un resumen redactado de objetivo contiene únicamente:

```text
kind
observedEffectiveId | null
observedSourceIds[]
observedFlowIds[]
```

Un resumen de grupo de partición contiene únicamente:

```text
groupIndex
anchorCount
anchorKinds[]
observedSourceIds[]
observedFlowIds[]
```

Estos campos se derivan de `role`, `group_order`, `selector_kind`,
`observed_effective_id`, `observed_source_ids` y `observed_flow_ids` ya
persistidos por D5. Nunca publican la dirección de un selector sender, un ID
remoto de mensaje, un `label_id` histórico ni un descriptor interno. Si una
fila no permite construir el resumen cerrado, el historial responde un error
controlado en vez de completar datos por inferencia.

## 14. Seguridad HTTP local

Para todas las rutas `/api/v2`:

- el servidor continúa enlazado sólo a `127.0.0.1:8765`;
- `Host` debe ser exactamente `127.0.0.1:8765`;
- no se habilita CORS ni `Access-Control-Allow-Origin: *`;
- métodos no enumerados responden sin ejecutar lógica de dominio;
- respuestas agregan `Cache-Control: no-store`;
- no se registran cuerpos, queries, IDs, direcciones, asuntos ni excepciones.
- un `GET` permite `Origin` ausente; si está presente debe ser exactamente
  `http://127.0.0.1:8765`.

Antes de habilitar `policyWrite`, FastAPI debe desactivar Swagger UI, ReDoc y
cualquier otra página local que cargue JavaScript, CSS, fuentes o imágenes desde
CDN. El esquema OpenAPI puede mantenerse como JSON local sin ejecutar recursos
remotos. Servir documentación interactiva vuelve a requerir assets locales
auditados y una decisión expresa de MAIN.

Además, todo `POST` exige:

- `Origin: http://127.0.0.1:8765`;
- `Content-Type: application/json`;
- cuerpo de hasta 64 KiB;
- ausencia de cookies como mecanismo de autorización;
- un modelo cerrado y discriminado.

Origen ausente, `localhost`, otro puerto, otro host, JSON inválido o tipo
incorrecto se rechazan antes de consultar o escribir SQLite. La documentación
interactiva no obtiene una excepción para estas reglas.

## 15. Errores públicos

Toda falla usa:

```json
{
  "error": {
    "code": "map_revision_conflict",
    "message": "La vista cambió. Actualizá el mapa antes de reintentar."
  }
}
```

`message` es una frase fija asociada al código; no concatena excepciones ni
datos. Códigos mínimos:

| HTTP | Código |
|---|---|
| 400 | `invalid_request` |
| 403 | `invalid_local_origin` |
| 404 | `source_not_found`, `decision_not_found` |
| 409 | `map_revision_conflict`, `policy_revision_conflict`, `command_id_conflict`, `policy_conflict`, `invalid_transition` |
| 413 | `payload_too_large` |
| 415 | `json_required` |
| 422 | `target_not_found`, `unsupported_target` |
| 503 | `map_unavailable`, `account_unavailable` |
| 500 | `internal_error` |

Errores de clasificación, política, SQLite, JSON o fechas se traducen a este
conjunto. Nunca se devuelve traceback, SQL, path local, cuenta, token, URL,
dirección, asunto, selector ni error remoto crudo.

## 16. Fixture contractual

Antes de abrir D6, MAIN debe construir un corpus canónico de
`IndexedMessageRecord` exclusivamente `.example`, con una `account_key` opaca,
checkpoint sintético y políticas sintéticas canónicas. Debe cubrir:

- múltiples remitentes de una fuente sólo cuando D4 permite unirlos;
- varios flujos por fuente;
- suscripciones confirmadas, probables, desconocidas y contradictorias;
- Spam separado;
- confianza alta, media, baja y contradictoria;
- protecciones automáticas y manuales;
- bindings `EXACT` y al menos un caso que requiere revisión;
- mapa completado como estado activo;
- nombres, rubros e intenciones automáticos frente a efectivos.

El fixture completo es el único corpus sembrado en la aplicación activa. Los
escenarios vacío, parcial y fallido usan bases temporales separadas en pruebas;
no pretenden coexistir como un único estado persistido. Ninguno contiene datos
reales ni hints privados de Base Segura. D6 consume respuestas HTTP o fixtures
derivados de este contrato; no importa modelos Python.

## 17. Pruebas obligatorias de C5

1. fotografía de cuenta inexistente, vacía y poblada;
2. lectura atómica ante escritura concurrente de índice o política;
3. revisión del ledger correcta después de undo sin políticas activas;
4. clasificación D4 y aplicación D5 sobre exactamente los mismos registros;
5. fuente particionada sin remitentes o dominios ajenos a sus miembros;
6. totales, fechas, tamaños y volumen mensual deterministas;
7. mapa parcial salvo checkpoint completado;
8. automático y efectivo preservados en mensaje, flujo y fuente;
9. confianza y protección nunca mejoradas o debilitadas;
10. bindings no aplicables visibles; los candidatos afectados quedan protegidos
    cuando D5 lo exige y un binding huérfano no inventa mensajes afectados;
11. orden determinista de todas las colecciones;
12. ausencia de recomendaciones, candidatos y espacio recuperable;
13. resolución servidor-side de cada comando público admitido;
14. rechazo de `accountKey`, selectores crudos y campos extra;
15. recibo HTTP y evento D5 atómicos, replay exacto y conflicto de
    `commandId` por huella distinta;
16. CAS de ambas revisiones y carrera entre cambio de índice y decisión sin
    escritura obsoleta;
17. undo append-only e idempotente;
18. Host, Origin, JSON, tamaño, CORS, `Cache-Control` y ausencia de assets
    remotos ejecutados bajo el origen local;
19. errores cerrados y redactados;
20. muestras limitadas a la allowlist METADATA;
21. IDs de mensaje locales y ausencia de IDs remotos en HTTP;
22. puerta sintética, cuenta fija y rechazo de una base inesperada;
23. API v1 y frontend actual sin cambios;
24. `oauthAvailable: false`, `canExecute: false` y barrera global intactos;
25. pytest, Ruff, mypy, batería global, HTTP real y `git diff --check`.

## 18. Puntos de detención

C5 no puede declararse implementada si:

- la lectura usa conexiones separadas para índice, checkpoint y políticas;
- una corrección puede escribirse sobre una revisión de mapa obsoleta;
- evento D5 y recibo HTTP pueden persistirse por separado;
- se pretende reutilizar `MailmapService` y su clasificador legado como mapa D4;
- hace falta modificar `/api/v1` o el frontend para hacer pasar el backend;
- se inventan candidatos, recomendaciones, frecuencia o espacio liberable;
- aparecen selectores D5, `account_key` o secretos en HTTP;
- se requieren OAuth, Gmail, red, credenciales o datos reales;
- una prueba necesita abrir navegador, contactar Google o instalar dependencias;
- el diff contiene bases, builds, cachés o `grafo.txt`.

## 19. Terminado

C5 queda lista para ser consumida por D6 sólo cuando:

1. el contrato esté reflejado en modelos y rutas cerradas;
2. exista la fotografía SQLite coherente y su CAS de escritura;
3. el recibo idempotente y el evento D5 se guarden atómicamente;
4. el fixture contractual sintético recorra el pipeline D1-D5 real;
5. la API v1 permanezca compatible;
6. pasen las pruebas específicas, seguridad y batería global;
7. MAIN compruebe HTTP real en loopback;
8. no existan capacidades, datos ni artefactos prohibidos;
9. documentación, Git y un SHA limpio reflejen la integración.

La existencia del contrato no crea ni autoriza D6. MAIN debe completar primero
la implementación C5, auditarla y consolidarla.
