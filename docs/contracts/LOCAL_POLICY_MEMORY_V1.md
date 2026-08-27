# Contrato de memoria de políticas locales v1

Estado: contrato aprobado por Joa el 27 de agosto de 2026. Joa autorizó a MAIN a
consolidar el prompt autosuficiente y crear un único worktree D5
`local-policy-memory` para implementar este alcance. La puerta técnica de
descriptores públicos D4 definida en la sección 3.1 ya está consolidada. El
estado operativo del worktree se registra únicamente en
`docs/WORKTREE_REGISTRY.md`.

Autoridad: contrato del MVP, D1, D3 y D4 consolidadas, la planificación durable
de D5 y la aprobación de Joa para que MAIN defina y explique este contrato
antes de abrir una dependencia especialista.

Este contrato no autoriza Gmail, OAuth, navegador, red, credenciales, datos
reales, API pública, interfaz, planes reales ni acciones sobre mensajes.

## 1. Objetivo

D5 debe conservar localmente decisiones explícitas de Joa y reaplicarlas sobre
clasificaciones posteriores sin transformar una corrección puntual en una
regla global accidental.

La clasificación automática de D4 continúa siendo pura, inmutable y
explicable. D5 agrega una capa separada de política del usuario que debe mostrar
siempre:

- el valor inferido automáticamente;
- el valor efectivo después de aplicar una decisión;
- la decisión que produjo la diferencia;
- el estado de reconciliación de esa decisión;
- las protecciones automáticas y manuales que siguen vigentes.

## 2. Decisiones admitidas en v1

D5 admite únicamente comandos cerrados equivalentes a:

```python
PolicyDecisionCommand = (
    SetSourceDisplayName
    | SetSourceRubro
    | SetFlowDisplayName
    | SetFlowIntention
    | MergeSources
    | PartitionSource
    | ProtectTarget
)
LocalPolicyCommand = PolicyDecisionCommand | UndoPolicy
```

Los comandos permiten:

- elegir el nombre visible de una fuente o un flujo;
- corregir el rubro efectivo de una fuente;
- corregir la intención efectiva de un flujo;
- unir fuentes seleccionadas de manera explícita;
- separar una fuente mediante una partición completa y explícita;
- proteger un mensaje, remitente, etiqueta, fuente o flujo;
- deshacer lógicamente una decisión sin borrar su historia.

Quedan fuera de v1:

- unir flujos;
- quitar una protección automática;
- modificar suscripción, confianza, autenticación o evidencia técnica;
- notas libres, reglas por dominio o reglas heurísticas globales;
- aprendizaje estadístico o IA;
- acciones en Gmail o recomendaciones ejecutables.

## 3. Entrada y frontera con D4

La aplicación de políticas consume:

- registros `IndexedMessageRecord` de una sola `account_key`;
- un `ClassificationResult` producido por D4 para esos mismos registros;
- las políticas activas de esa cuenta.

La operación pública de dominio es equivalente a:

```python
apply_local_policies(
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    policies: Iterable[ActivePolicy],
) -> PolicyApplicationResult
```

`account_key` es obligatoria aun cuando el índice esté vacío, para poder marcar
políticas anteriores como huérfanas sin inferir una cuenta a partir de datos
ausentes. Antes de producir una salida debe materializar y validar toda la
entrada. Debe rechazar cuentas mezcladas, mensajes duplicados, referencias que
no pertenecen al resultado clasificado y versiones desconocidas mediante
errores controlados y redactados.

D5 no modifica objetos D4 ni reemplaza su evidencia. Sus resultados son una
proyección nueva que conserva los valores automáticos junto a los efectivos.

### 3.1. Descriptor público de identidad D4

La salida D4 expone el `List-ID` canónico, el tipo de ancla del flujo y la razón
estructural de aislamiento mediante descriptores públicos. D5 no puede duplicar
funciones privadas de D4 ni reconstruir esos valores por aproximación.

MAIN amplió el contrato y la salida pública de D4 con modelos cerrados,
inmutables, versionados y redactados equivalentes a:

```python
SourceIdentityDescriptor(
    version: int,
    kind: SourceAnchorKind,  # senders | isolated_message
    sender_addresses: tuple[str, ...],
    isolated_message_id: str | None,
)

FlowIdentityDescriptor(
    version: int,
    kind: FlowAnchorKind,  # list_intent | sender_intent | isolated_message
    source: SourceIdentityDescriptor,
    list_id: str | None,
    sender_address: str | None,
    automatic_intention: Intencion,
    isolated_message_id: str | None,
)
```

`ClassifiedSource` debe publicar su `identity_descriptor` y `ClassifiedFlow` el
suyo. Los campos mutuamente excluyentes se validan según `kind`. D4 genera esos
descriptores dentro de su propia normalización; D5 sólo los consume. Ninguna
representación o error muestra direcciones, `List-ID` o IDs remotos.

Esta ampliación no cambia las agrupaciones, taxonomías, IDs ni evidencias de D4.
La batería de la columna vertebral debe permanecer verde antes de preparar el
prompt especialista de D5.

### 3.2. Preparación tipada antes de persistir

Un `PolicyDecisionCommand` por sí solo no demuestra que su objetivo exista en
la clasificación actual, que una partición cubra exactamente sus anclas ni qué
binding observó Joa al decidir. Por eso toda decisión nueva atraviesa primero
una frontera pura y tipada equivalente a:

```python
prepare_policy_decision(
    *,
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    active_policies: Iterable[ActivePolicy],
    command: PolicyDecisionCommand,
) -> PreparedPolicyDecision
```

`PreparedPolicyDecision` es un modelo cerrado, inmutable, con `slots` y
versionado distinto del comando crudo. Contiene:

- el `PolicyDecisionCommand` original, sin mutarlo;
- los selectores y anclas canónicos que resolvieron en la entrada actual;
- el `observed_effective_id` y los IDs automáticos observados aplicables;
- los `structural_decision_ids` activos que formaban el objetivo;
- las relaciones tipadas de reemplazo y contexto estructural necesarias para
  reconstruir el binding histórico.

La preparación materializa y valida completamente registros, clasificación y
políticas activas. Debe comprobar la misma cuenta, versiones conocidas,
existencia y unicidad del objetivo, cobertura exacta de una partición,
participantes de una unión y conflictos visibles. Un objetivo inexistente
produce `target_not_found`; una entrada o partición inválida produce el error
controlado correspondiente. Ninguno de esos casos llega al repositorio.

La preparación no consulta SQLite, no persiste, no usa reloj ni aleatoriedad y
no crea identificadores implícitos. El repositorio no importa D4 ni intenta
reclasificar: recibe la decisión preparada y vuelve a validar su estructura,
versiones y consistencia interna antes de escribir. `UndoPolicy` no usa esta
frontera porque su objetivo es una decisión persistida; el repositorio valida
su existencia, cuenta y estado activo dentro de la transacción.

## 4. Identidad durable y selectores

Los `source_id` y `flow_id` de D4 son útiles para auditoría, pero no bastan como
identidad durable: pueden cambiar cuando cambia la composición de una fuente o
un flujo.

`PolicyTargetSelector` es una unión cerrada perteneciente a una cuenta. Puede
apuntar a:

- mensaje: `provider_message_id` exacto;
- remitente: dirección normalizada exacta;
- etiqueta: identificador de etiqueta del proveedor exacto;
- fuente: `EffectiveSourceSelector`;
- flujo: `EffectiveFlowSelector`.

Las anclas de una partición pueden ser un remitente, un
`FlowIdentityDescriptor` o, sólo cuando no hay un ancla reutilizable, un
`provider_message_id` exacto.

Una unión enumera todas las fuentes participantes. Una partición debe contener
grupos no vacíos, disjuntos y cubrir una sola vez todas las anclas canónicas
actuales de la fuente. Un mensaje futuro que coincida exactamente con un ancla
ya asignada hereda ese grupo y no invalida la política. Un ancla nueva no
contemplada, una ancla que cambia de grupo o un mensaje aislado nuevo produce
`NEEDS_REVIEW` y detiene la aplicación estructural. Si una entrada actual queda
sin asignar o aparece en dos grupos, el comando se rechaza antes de persistir.

Un selector de remitente o etiqueta es deliberadamente reutilizable para
mensajes futuros que coincidan exactamente. Un selector de fuente o flujo no se
generaliza por parecido de nombre, dominio, asunto, ID ni clasificación.

Los selectores pueden contener metadatos privados. Un hash no los vuelve
anónimos. Sus representaciones, errores y logs deben redactarlos, y su uso con
datos reales continúa bloqueado hasta resolver la protección en reposo de C4.

### 4.1. Topología e identidad efectivas

Las políticas estructurales de unión y partición se aplican antes que nombres,
rubros, intenciones y protecciones.

Los selectores efectivos son modelos cerrados equivalentes a:

```python
EffectiveSourceSelector(
    version: int,
    kind: EffectiveSourceKind,  # automatic | merged | partition_group
    automatic_sources: tuple[SourceIdentityDescriptor, ...],
    partition_anchors: tuple[PartitionAnchor, ...],
)

EffectiveFlowSelector(
    version: int,
    automatic_flow: FlowIdentityDescriptor,
    effective_source: EffectiveSourceSelector,
)
```

Para `automatic` existe una sola fuente automática y no hay anclas de
partición. Para `merged` hay al menos dos fuentes automáticas ordenadas y no hay
anclas de partición. Para `partition_group` existe una sola fuente automática y
un grupo no vacío y ordenado de anclas asignadas.

En v1 las políticas estructurales no se anidan: `MergeSources` enumera fuentes
automáticas D4 y `PartitionSource` divide una sola fuente automática D4. Para
cambiar la estructura se registra una decisión completa que reemplaza las
anteriores; no se fusiona un grupo ya partido ni se parte una fuente ya unida.

Los comandos no estructurales se anclan a la topología efectiva visible al
momento de registrarlos y se resuelven después de reconstruir esa topología. Si
se deshace o reemplaza la política estructural que originó su objetivo, pasan a
reconciliación; no se trasladan a otra fuente o flujo por semejanza.

Cada fuente y flujo efectivo recibe un identificador opaco, versionado y
determinista derivado de `account_key` y su selector efectivo canónico. Los
prefijos son `effective-source-v1-` y `effective-flow-v1-`; nunca se elige como
ganador el ID de una fuente participante ni se exponen metadatos en el ID.

Una unión conserva todos los mensajes y flujos participantes bajo la nueva
fuente efectiva. Una partición reasigna cada mensaje a exactamente una fuente
efectiva; si un flujo automático atraviesa más de un grupo, se divide de manera
determinista por fuente efectiva. La proyección conserva por separado todos los
`source_id`, `flow_id`, valores y evidencias automáticos de D4 que originaron
cada resultado.

`PolicyApplicationResult` valida como invariantes:

- cada mensaje actual pertenece a una sola fuente efectiva;
- cada mensaje actual pertenece a un solo flujo efectivo;
- cada flujo efectivo pertenece a una sola fuente efectiva;
- las relaciones mensaje, flujo y fuente son completas y bidireccionalmente
  coherentes;
- ningún mensaje se pierde o duplica por aplicar una política.

## 5. Reconciliación después de reclasificar

Cada política obtiene uno de estos estados cerrados:

| Estado | Significado | Aplicación automática |
|---|---|---|
| `EXACT` | Selector efectivo, contexto estructural e IDs observados siguen iguales. | Sí |
| `REBOUND` | Selector efectivo y contexto siguen iguales; sólo cambiaron IDs automáticos de origen. | Sí |
| `NEEDS_REVIEW` | Cambió la membresía o una fuente se dividió/fusionó. | No |
| `ORPHANED` | Ya no existe ningún objetivo compatible. | No |
| `AMBIGUOUS` | Más de un objetivo podría coincidir. | No |
| `CONFLICT` | Dos políticas estructurales o de reemplazo son incompatibles. | No |

Cada ancla persistida conserva:

- selector canónico completo y su versión;
- versión de `ClassificationResult` al registrar;
- `observed_effective_id`, cuando corresponda;
- conjuntos ordenados de `source_id` y `flow_id` automáticos de origen;
- conjunto ordenado de `structural_decision_ids` activos que formaban el
  objetivo efectivo;
- revisión de cuenta en la que se creó.

`PolicyBinding` compara esos valores históricos con los descriptores actuales y
expone los IDs anteriores, los actuales y el estado. `EXACT` exige igualdad del
selector efectivo, ID efectivo, IDs automáticos de origen y contexto
estructural. `REBOUND` exige igualdad del selector efectivo y de los
`structural_decision_ids`; sólo pueden haber cambiado IDs automáticos de origen.
En D4 v1 determinista normalmente no aparece. Si se deshace, reemplaza o cambia
una decisión estructural que formaba el objetivo, corresponde `NEEDS_REVIEW`
aunque los descriptores automáticos sigan iguales. Si cambia la versión del
selector, sólo una migración explícita aprobada por MAIN puede establecer
equivalencia; sin ella también corresponde `NEEDS_REVIEW`. Una versión de
política que el repositorio no sabe leer produce `unknown_policy_version`.

“Cambio de membresía” depende del selector:

- mensaje: cambios de sus metadatos no alteran el ancla; su desaparición la deja
  `ORPHANED`;
- remitente o etiqueta: nuevos mensajes con coincidencia exacta son crecimiento
  normal y heredan la política;
- fuente automática: nuevos mensajes de los mismos remitentes son crecimiento normal;
  agregar o quitar un remitente estructural produce `NEEDS_REVIEW`;
- flujo: nuevos mensajes con el mismo descriptor son crecimiento normal;
  cambiar `List-ID`, remitente, intención automática o aislamiento produce
  `NEEDS_REVIEW`;
- unión: cada fuente participante debe conservar su descriptor; cambios en sus
  mensajes no invalidan, pero cambios en sus anclas sí;
- partición: rigen las reglas de anclas reutilizables de la sección 4.

`AMBIGUOUS` se reserva para una migración versionada que produzca más de un
candidato actual o para un selector antes único que, tras una topología nueva,
resuelva a varios objetivos efectivos no equivalentes. Políticas activas
solapadas son `CONFLICT`; datos persistidos imposibles o corruptos producen un
error controlado.

Sólo `EXACT` y `REBOUND` modifican la vista efectiva. `NEEDS_REVIEW`,
`AMBIGUOUS` y `CONFLICT` marcan `review_required=True` y protegen la unión de
todos los candidatos actuales afectados. `ORPHANED` conserva visible la
política y su historia, pero no afecta mensajes porque no existe un objetivo
actual. D5 nunca elige por proximidad ni mejora artificialmente la confianza de
D4.

## 6. Comandos, revisiones e idempotencia

Todo `LocalPolicyCommand` contiene:

- `command_id` opaco para idempotencia;
- `account_key` opaca;
- tipo cerrado;
- instante UTC con zona horaria;
- `expected_revision`.

Un `PolicyDecisionCommand` agrega un selector cerrado, el valor tipado propio de
su clase y un `decision_id` opaco, nuevo e inmutable. Cuando reemplaza políticas
activas enumera todas en `supersedes_decision_ids`. `UndoPolicy` no contiene un
selector ni un valor ficticios y no crea una política nueva: identifica la
decisión activa mediante `target_decision_id`.

`expected_revision` refiere a una revisión monotónica del flujo de políticas de
la cuenta, que vale cero cuando todavía no existen eventos. Cada comando nuevo
aceptado incrementa esa revisión exactamente una vez. `policy_history` se
ordena por esa revisión y no por la hora del cliente.

Repetir el mismo `command_id` con el mismo contenido devuelve el evento ya
registrado aunque la cuenta haya avanzado de revisión. Reutilizarlo con
contenido distinto produce
`command_id_conflict`. Una revisión desactualizada produce
`revision_conflict` y no escribe nada.

No existe la regla implícita “gana la última fecha”. Una política reemplaza a
otra sólo si enumera explícitamente las decisiones reemplazadas. Dos políticas
estructurales solapadas sin ese vínculo rechazan el nuevo comando con
`policy_conflict`. `CONFLICT` se reserva para una incompatibilidad que aparece
al reconciliar políticas antes válidas con una clasificación posterior.

`UndoPolicy` agrega un evento nuevo que desactiva una decisión activa. No borra
ni reescribe eventos anteriores. Reactiva sus decisiones directamente
reemplazadas sólo cuando no fueron deshechas ni reemplazadas por otra decisión
activa. Se rechazan ciclos, decisiones inexistentes, referencias cruzadas entre
cuentas y transiciones incompatibles.

## 7. Precedencia de clasificación

- D4 conserva el nombre, rubro e intención automáticos y toda su evidencia.
- Una corrección `EXACT` o `REBOUND` define el valor efectivo correspondiente.
- La salida agrega evidencia tipada de decisión del usuario con su
  `decision_id`, sin copiar texto privado en representaciones o errores.
- Una corrección no cambia `Suscripcion`, `Confianza`, DKIM, DMARC ni evidencia
  automática.
- Una corrección nunca convierte confianza baja o contradictoria en una
  autorización para actuar.
- Deshacer restaura el valor automático o la política anterior explícitamente
  reemplazada.

### 7.1. Composición de la proyección efectiva

- Un mensaje conserva siempre sus valores automáticos D4. Su rubro efectivo es
  el rubro efectivo de su fuente y su intención efectiva es la de su flujo.
- Una fuente efectiva sin unión conserva el nombre automático de D4. Una unión
  sin nombre manual usa la etiqueta neutra `Fuente combinada`; una partición
  conserva como nombre automático el de la fuente original hasta una corrección.
- El rubro automático resumido de una fuente efectiva es el rubro común de sus
  mensajes automáticos; si hay más de uno, es `Rubro.DESCONOCIDO`.
  `SetSourceRubro` reemplaza sólo el rubro efectivo y lo proyecta sobre sus
  mensajes.
- Los flujos no se unen en v1. Una unión de fuentes conserva cada flujo
  participante por separado. Una partición puede dividir un flujo automático;
  cada fragmento conserva intención, suscripción, confianza y evidencia
  automáticas.
- `SetFlowIntention` cambia la intención efectiva del flujo seleccionado y de
  sus mensajes, sin alterar la intención automática.
- La confianza efectiva resumida de una fuente o flujo es siempre la peor
  confianza automática de sus mensajes según `ALTA`, `MEDIA`, `BAJA`,
  `CONTRADICTORIA`. Ninguna política puede mejorarla.
- La evidencia efectiva es la unión ordenada y sin duplicados de toda evidencia
  automática participante más la evidencia tipada de políticas aplicadas. No se
  elimina evidencia por una unión, partición o corrección.

## 8. Precedencia de protección

La protección es acumulativa y falla de forma segura. D5 no ofrece un comando
“desproteger”. Debe conservar como mínimo:

- `SENT`, `DRAFT`, `TRASH`, `STARRED` e `IMPORTANT`;
- etiquetas protegidas explícitamente por Joa;
- seguridad y recuperación de cuenta;
- documentos, comprobantes y facturas;
- comunicación personal;
- confianza baja o contradictoria;
- mensajes de una conversación que mezcle miembros protegidos y no protegidos;
- cualquier objetivo alcanzado por `ProtectTarget`.

Una corrección manual hacia seguridad, documento o comunicación personal puede
agregar protección. Una corrección en sentido contrario no elimina la
protección automática original.

La salida conserva razones múltiples y expone como mínimo:

- `automatic_protection: Proteccion`;
- `effective_protection: Proteccion`;
- `protected`;
- `review_required`;
- `hard_excluded`;
- códigos de razón y `decision_id` aplicables.

La protección se calcula primero por mensaje. Una fuente o flujo efectivo queda
protegido si al menos uno de sus mensajes está protegido y conserva el conjunto
de razones de todos sus miembros. `ProtectTarget` puede apuntar a un mensaje,
remitente, etiqueta, fuente efectiva o flujo efectivo; en estos dos últimos
casos todos sus mensajes actuales y futuros que mantengan el selector exacto
heredan la protección. Si cambia la topología, rigen los estados de
reconciliación y no se traslada por semejanza.

`automatic_protection` resume sólo reglas derivadas de registros y
clasificación automática. `effective_protection` agrega `ProtectTarget` y una
intención manual de seguridad, documento o comunicación personal. La categoría
`Rubro.PERSONAL` no protege por sí sola: la señal relevante es
`Intencion.PERSONAL`.

`hard_excluded=True` se reserva para `SENT`, `DRAFT` y `TRASH`. `STARRED`,
`IMPORTANT`, etiquetas protegidas y políticas manuales producen
`protected=True`; cualquier relajación futura pertenece al contrato de planes,
no a D5. `review_required` es independiente de la categoría principal y siempre
bloquea una acción.

Si un consumidor necesita una categoría principal de `Proteccion`, el orden de
mayor a menor precedencia es `CRITICA`, `DOCUMENTAL`, `USUARIO`, `REVISION`,
`ORDINARIA`. Ese resumen no descarta las demás razones. Todo estado de
reconciliación distinto de `EXACT` o `REBOUND` exige revisión y no puede
habilitar una acción.

## 9. Modelos y errores cerrados

`src/mailmap/policy_model.py` define modelos inmutables, con `slots`, sin
diccionarios arbitrarios:

- comandos tipados de la sección 2;
- `PreparedPolicyDecision` y sus anclas y relaciones tipadas;
- `PolicyEvent`;
- `PolicyTargetSelector`, `EffectiveSourceSelector`, `EffectiveFlowSelector` y
  anclas tipadas;
- `ActivePolicy`;
- `PolicyBinding`;
- proyecciones efectivas de mensaje, fuente y flujo;
- `PolicyApplicationResult`;
- enums de tipo, estado y error;
- un error controlado y redactado.

Los códigos mínimos de error son:

```text
invalid_input
mixed_accounts
unsupported_target
target_not_found
revision_conflict
command_id_conflict
policy_conflict
invalid_transition
unknown_policy_version
```

La representación y el mensaje público del error exponen únicamente su
`PolicyErrorCode`. Si la implementación necesita contexto programático, debe
modelarlo mediante campos cerrados y expresamente enumerados, con `repr=False`;
no admite texto libre, diccionarios, IDs, selectores, revisiones ni valores del
usuario.

`target_not_found` rechaza un comando cuyo selector nunca fue válido en la
entrada actual; una política anteriormente válida que pierde su objetivo
produce `ORPHANED`. `policy_conflict` rechaza un comando incoherente antes de
persistir; un conflicto surgido después por reclasificación produce `CONFLICT`.
`NEEDS_REVIEW`, `ORPHANED` y `AMBIGUOUS` son resultados normales de
reconciliación, no excepciones ni motivos para descartar historia.

## 10. Operaciones de repositorio

El repositorio ofrece operaciones tipadas equivalentes a:

```python
policy_event_for_command(command: LocalPolicyCommand) -> PolicyEvent | None
record_policy(prepared: PreparedPolicyDecision) -> PolicyEvent
undo_policy(command: UndoPolicy) -> PolicyEvent
policy_history(account_key: str) -> tuple[PolicyEvent, ...]
active_policies(account_key: str) -> tuple[ActivePolicy, ...]
```

`policy_event_for_command` es la puerta de replay anterior a la preparación. Si
encuentra `(account_key, command_id)` y el comando canónico completo coincide,
devuelve el evento previo; si el contenido difiere produce
`command_id_conflict`; si no existe devuelve `None`. Esta lectura permite
reintentar una decisión aun cuando su objetivo o clasificación hayan cambiado,
pero no demuestra ausencia frente a una carrera concurrente.

`record_policy` no acepta un `PolicyDecisionCommand` crudo para una decisión
nueva. Valida el objeto preparado completo antes de escribir. Registrar un
evento, todas sus anclas y sus relaciones usa una sola transacción. Un fallo
revierte el conjunto completo. Las consultas tienen orden determinista y aíslan
cuentas.

La búsqueda de un `command_id` previo, su comparación de contenido, la
validación de `expected_revision`, la detección de reemplazos o conflictos, la
inserción de evento, anclas y relaciones y el avance de revisión deben ocurrir
dentro de la misma transacción `BEGIN IMMEDIATE`. Dos comandos concurrentes con
`command_id` distintos y la misma revisión esperada no pueden ser aceptados:
exactamente uno avanza la revisión y el otro termina en `revision_conflict` sin
escritura parcial. Un mismo `command_id` se resuelve antes como replay exacto o
`command_id_conflict`.

La búsqueda idempotente dentro de `record_policy` ocurre antes de comparar la
revisión o el binding preparado y repite obligatoriamente la puerta de replay
bajo el lock. Si ya existe `(account_key, command_id)`, se compara el contenido
canónico completo del `PolicyDecisionCommand` original: si es idéntico se
devuelve el evento guardado, aunque la cuenta haya avanzado o una nueva
preparación observe otros IDs; si es distinto se produce
`command_id_conflict`. Un reintento nunca reemplaza las anclas históricas
guardadas por la primera aceptación.

`undo_policy` aplica el mismo orden dentro de su propia transacción: primero
replay exacto, después revisión y finalmente existencia, cuenta y estado activo
de la decisión objetivo. Un undo idéntico devuelve su evento aunque el objetivo
ya esté inactivo; un comando diferente con el mismo `command_id` produce
`command_id_conflict`.

Ninguna operación D5 crea `indexed_accounts` ni llama al helper D1 que la crea.
`record_policy` y `undo_policy` comienzan `BEGIN IMMEDIATE`, comprueban que la
cuenta indexada ya existe y sólo entonces continúan. Una decisión preparada para
una cuenta inexistente produce `target_not_found`; un undo nuevo sobre una
cuenta inexistente produce `invalid_transition`, siempre sin escribir.
`policy_event_for_command`, `policy_history` y `active_policies` tampoco crean
cuentas.

`delete_account_index` es una frontera terminal de privacidad: elimina por
cascada políticas, historia y ledger de idempotencia. Un preparado, retry o undo
anterior no puede recrear la cuenta y deja de ser un replay después del olvido.
La carrera entre borrado y escritura queda serializada por `BEGIN IMMEDIATE`: si
el borrado gana, la escritura falla sin recrear; si la escritura gana, el borrado
posterior elimina todo y el estado final permanece olvidado.

## 11. Migración acumulativa v3

La siguiente migración debe conservar intactas las migraciones v1 y v2 y crear
como mínimo:

```text
local_policy_events
local_policy_anchors
local_policy_relations
```

Requisitos:

- eventos append-only;
- anclas normalizadas y tipadas, con orden y grupo explícitos;
- relaciones normalizadas y tipadas para `supersedes`, `undoes` y contexto
  estructural; no se serializan listas de decisiones dentro de una columna;
- versión de selector, versión D4, IDs automáticos observados y referencias a
  decisiones estructurales suficientes para reconstruir cada binding histórico;
- unicidad de `(account_key, command_id)`;
- unicidad de `(account_key, decision_id)` para eventos que crean una decisión;
- unicidad de `(account_key, account_revision)`;
- claves foráneas activas y borrado en cascada desde `indexed_accounts`;
- fechas UTC, versión y revisiones validadas;
- restricciones que impidan combinaciones imposibles por tipo de comando;
- ningún `payload_json`, `extra`, blob o diccionario genérico capaz de eludir el
  modelo cerrado;
- una base nueva y una base migrada terminan con el mismo esquema efectivo.

`start_full_index` reemplaza mensajes y checkpoint, pero conserva las políticas
para poder reconciliarlas con el nuevo escaneo. `delete_account_index` elimina
también políticas e historia de esa cuenta como medida de privacidad. Revocar o
desconectar una sesión no equivale por sí solo a borrar el índice ni sus
políticas.

Antes de usar datos reales siguen pendientes ubicación por usuario, ACL,
cifrado autenticado, retención, respaldo y borrado verificable.

## 12. Pureza, privacidad y límites

El dominio de aplicación de políticas es local y puro:

- no importa ni ejecuta red, Gmail, OAuth, navegador o SDKs externos;
- no usa reloj o aleatoriedad implícitos;
- no abre archivos, variables de entorno ni bases por sí mismo;
- no registra ni imprime metadatos;
- no modifica D4, D3, sesión, API, servicio, frontend, fixtures ni planes;
- no agrega dependencias;
- usa exclusivamente direcciones y dominios sintéticos reservados `.example`
  durante D5.

La persistencia guarda decisiones privadas además de los selectores necesarios.
No debe guardar tokens, credenciales, cuerpos, HTML, snippets, MIME, adjuntos,
destinatarios, encabezados genéricos ni errores remotos crudos.

## 13. Archivos permitidos para la futura entrega

La futura dependencia especialista queda limitada a:

```text
src/mailmap/policy_model.py
src/mailmap/policy_domain.py
src/mailmap/repository.py
tests/test_local_policy_memory.py
tests/test_base_segura_safety.py
```

`repository.py` sólo puede cambiar para agregar la migración y las operaciones
del presente contrato. Cualquier necesidad de modificar D4, D3, API, servicio,
frontend, contratos o dependencias detiene la entrega y vuelve a MAIN.

## 14. Pruebas obligatorias

La futura entrega debe demostrar con datos sintéticos:

1. esquema equivalente en base nueva y migrada desde v2;
2. rollback conjunto de evento, anclas y relaciones;
3. preparación tipada que rechaza un objetivo inexistente, una unión inválida o
   una partición incompleta antes de persistir, y repositorio que rechaza una
   decisión nueva sin preparación;
4. replay exacto anterior a la preparación, comparación del comando original y
   repetición de esa comprobación dentro de `BEGIN IMMEDIATE`;
5. idempotencia y conflicto de `command_id`, incluido el caso concurrente en
   que una sola revisión avanza y el perdedor obtiene `revision_conflict` sin
   escritura parcial;
6. historial append-only, reemplazo explícito y undo lógico, incluido replay de
   un undo ya aplicado;
7. binding histórico, `EXACT`, `REBOUND` por cambio aislado de ID y revisión si
   cambia el selector sin migración versionada;
8. crecimiento normal de mensajes sin invalidación y revisión ante cambios de
   anclas, expansión, reducción, fusión o división estructural;
9. estados huérfano, ambiguo y conflicto sin aplicación silenciosa;
10. corrección de nombre, rubro e intención sin mutar D4;
11. unión y partición exactas, completas y deterministas, con IDs efectivos e
    invariantes relacionales;
12. nombre, rubro, intención y protección dirigidos a fuentes unidas, grupos
    partidos y flujos fragmentados mediante selectores efectivos;
13. undo o reemplazo estructural que deja esas políticas en revisión en vez de
    trasladarlas;
14. no generalización por nombre, dominio o similitud;
15. aislamiento entre cuentas;
16. protección automática, por remitente, etiqueta, fuente, flujo y mensaje;
17. conversación mixta y contradicción protegidas;
18. undo manual incapaz de rebajar una protección automática;
19. escaneo completo que conserva políticas;
20. borrado de cuenta que elimina índice, políticas e historia sólo de esa
    cuenta, y preparado, retry o undo anteriores que no pueden recrearla,
    incluido el orden concurrente entre borrado y escritura;
21. modelos, errores y representaciones redactados;
22. ausencia de red, Gmail, OAuth, credenciales, datos reales y capacidades de
    ejecución;
23. composición conservadora de rubro, intención, confianza y evidencia;
24. consumo de descriptores públicos D4 sin duplicar su normalización privada;
25. compatibilidad con toda la batería de Base Segura, D1, D2, D3 y D4.

## 15. Puntos de detención

La implementación no puede comenzar ni continuar si:

- Joa no autorizó D5 de forma explícita;
- `main` no tiene un commit base limpio posterior a este contrato;
- la identidad propuesta depende sólo de `source_id` o `flow_id`;
- se pretende rebajar una protección automática;
- una decisión nueva podría llegar a persistencia sin
  `PreparedPolicyDecision`;
- una operación D5 podría crear o recrear `indexed_accounts`;
- hace falta modificar D4, C1, C4 o C5 silenciosamente;
- aparece una migración concurrente;
- se requieren Gmail, OAuth, red, credenciales, datos reales, API o UI;
- una prueba necesita abrir navegador o conectarse a un servicio externo.

## 16. Terminado

D5 estará entregada para auditoría cuando:

1. MAIN haya integrado primero los descriptores públicos D4 sin cambiar sus
   resultados actuales;
2. implemente solamente los comandos, modelos, reconciliación y persistencia de
   este contrato;
3. toda decisión nueva se prepare y valide contra D4 antes de persistir y todo
   replay cuyo ledger siga existiendo se resuelva sin exigir que su objetivo
   siga existiendo; después de `delete_account_index` rige la frontera terminal
   de privacidad de la sección 10;
4. D4 permanezca pura e inmutable durante la entrega D5;
5. sólo `EXACT` y `REBOUND` se reapliquen automáticamente;
6. la protección nunca disminuya;
7. historial, undo, idempotencia y aislamiento estén probados;
8. las migraciones sean acumulativas y atómicas;
9. pasen pruebas específicas, pytest completo, Ruff, mypy y la barrera de
   seguridad;
10. el diff contenga únicamente los cinco archivos autorizados;
11. no existan red, Gmail, OAuth, credenciales, datos reales ni artefactos.

La entrega especialista no se integra ni habilita D6 por sí sola. MAIN debe
auditarla, repetir la batería y obtener las autorizaciones que correspondan.
