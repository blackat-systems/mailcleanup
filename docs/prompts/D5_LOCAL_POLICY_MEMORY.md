# Prompt D5 — Local Policy Memory

## QUÉ HACE

Implementa la dependencia especialista D5 `local-policy-memory`: una capa local,
sintética, determinista y explicable que recuerda decisiones explícitas de Joa
sobre nombres, rubros, intenciones, uniones, particiones y protecciones.

La entrega prepara y persiste esas decisiones con historial append-only, undo
lógico, revisión optimista y reconciliación conservadora sobre clasificaciones
D4 posteriores. No conecta la memoria con API, interfaz ni Gmail.

## POR QUÉ EXISTE

D4 infiere automáticamente fuentes y flujos, pero una inferencia no debe borrar
ni confundir una corrección humana. D5 mantiene ambas capas separadas: conserva
el valor automático y proyecta un valor efectivo sólo cuando la decisión sigue
vinculada de manera exacta o mediante un cambio aislado de ID.

La frontera evita que una corrección puntual se transforme en una regla global,
que una política se traslade por parecido y que una decisión manual debilite una
protección automática.

## ROL

Sos la dependencia especialista D5 `local-policy-memory` de MailCleanup. No sos
MAIN. Implementá exclusivamente el contrato de memoria local sobre datos
sintéticos. Tu entrega será evidencia parcial para la auditoría independiente de
MAIN: no la declares integrada ni habilites consumidores posteriores.

## UBICACIÓN Y BASE OBLIGATORIAS

- Worktree: el checkout aislado que MAIN cree para esta tarea.
- Rama exacta esperada: `codex/local-policy-memory`.
- Commit base: el SHA exacto que MAIN informe al crear el worktree. Debe ser el
  commit limpio que contiene este prompt, D4 pública y el contrato D5 vigente.
- Estado inicial esperado: limpio, sin archivos no rastreados.
- Remoto esperado: ninguno.

Antes de editar ejecutá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git remote -v
```

Detenete si la ruta no es el worktree asignado, la rama o el SHA no coinciden,
el árbol no está limpio o existe trabajo fuera del alcance. No uses reset,
checkout destructivo, clean, merge, rebase ni maniobras para ocultar diferencias.

## LECTURA OBLIGATORIA

Leé completamente antes de implementar:

1. `AGENTS.md`.
2. Este prompt.
3. `docs/CONTRATO_MVP.md`.
4. `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`.
5. `docs/contracts/CLASSIFICATION_DOMAIN_V1.md`.
6. `docs/contracts/INDEX_PERSISTENCE_V1.md`.
7. `docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`.
8. `docs/contracts/SECURITY_PRIVACY_V1.md`.
9. La sección D5 de `docs/PLAN_DEPENDENCIAS.md`.
10. `docs/DECISIONES.md`.
11. `src/mailmap/model.py`.
12. `src/mailmap/index_model.py`.
13. `src/mailmap/classification_model.py`.
14. `src/mailmap/classification_domain.py`, sólo para comprender la frontera;
    D5 no puede importar helpers privados ni duplicar su normalización.
15. `src/mailmap/repository.py` completo, incluidas migraciones y transacciones.
16. `tests/test_index_persistence.py`.
17. `tests/test_real_classification_domain.py`.
18. `tests/test_base_segura_domain.py`.
19. `tests/test_base_segura_safety.py`.
20. `scripts/check.ps1` y `pyproject.toml`.

Para D5 prevalece `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`. No lo modifiques
para acomodar la implementación. Si otra fuente lo contradice materialmente,
detenete y devolvé la diferencia a MAIN.

## OBJETIVO CONTRACTUAL

Implementá dos capacidades separadas:

1. Un dominio puro que:
   - prepare una decisión nueva contra registros, clasificación y políticas
     activas actuales;
   - aplique políticas persistidas sin mutar D4;
   - reconstruya topología efectiva;
   - reconcilie bindings históricos;
   - componga valores y protecciones de manera conservadora.
2. Una persistencia SQLite v3 que:
   - registre eventos, anclas y relaciones atómicamente;
   - preserve historial e idempotencia;
   - resuelva revisiones concurrentes;
   - permita undo lógico;
   - aísle cuentas;
   - sobreviva a un escaneo completo y se borre al olvidar el índice de la
     cuenta correspondiente.

## ARCHIVOS AUTORIZADOS

Podés crear o modificar exclusivamente:

```text
src/mailmap/policy_model.py
src/mailmap/policy_domain.py
src/mailmap/repository.py
tests/test_local_policy_memory.py
tests/test_base_segura_safety.py
```

Estado final esperado, salvo una justificación contractual concreta:

```text
 M src/mailmap/repository.py
 M tests/test_base_segura_safety.py
?? src/mailmap/policy_domain.py
?? src/mailmap/policy_model.py
?? tests/test_local_policy_memory.py
```

No modifiques D1-D4 fuera de la ampliación v3 de `repository.py`, API, servicio,
frontend, fixtures, scripts, configuración, dependencias ni documentación. No
agregues un sexto archivo. Si resulta necesario, detenete y volvé a MAIN.

## MODELOS CERRADOS

En `policy_model.py` definí únicamente modelos tipados, inmutables, con `slots`,
versiones exactas y representaciones redactadas. No uses `dict` arbitrarios,
`**kwargs`, payloads extensibles, strings libres para enums ni campos `extra`.

El módulo debe cubrir lo establecido por el contrato, como mínimo:

- los siete `PolicyDecisionCommand` cerrados;
- `UndoPolicy` y `LocalPolicyCommand`;
- selectores de mensaje, remitente, etiqueta, fuente efectiva y flujo efectivo;
- `EffectiveSourceSelector`, `EffectiveFlowSelector` y `PartitionAnchor`;
- `PreparedPolicyDecision`, anclas preparadas y relaciones preparadas tipadas;
- `PolicyEvent`, `ActivePolicy` y `PolicyBinding`;
- estados `EXACT`, `REBOUND`, `NEEDS_REVIEW`, `ORPHANED`, `AMBIGUOUS` y
  `CONFLICT`;
- proyecciones efectivas de mensaje, fuente y flujo;
- `PolicyApplicationResult`;
- enums cerrados de comando, selector, relación, protección, estado y error;
- una excepción controlada cuyo mensaje y representación sólo expongan
  `PolicyErrorCode`. Cualquier contexto programático adicional debe ser cerrado,
  expresamente enumerado y `repr=False`; no uses texto libre ni diccionarios.

Todos los `LocalPolicyCommand` comparten `command_id`, `account_key`, tipo,
instante UTC y `expected_revision`. Sólo `PolicyDecisionCommand` agrega selector,
valor, `decision_id` y reemplazos. `UndoPolicy` agrega
`target_decision_id` y no inventa selector, valor o `decision_id`.

Validá estrictamente:

- cadenas normalizadas y no vacías;
- IDs opacos y `account_key` sin forma de correo;
- fechas timezone-aware normalizadas a UTC;
- versiones exactas, rechazando también `bool` como entero;
- tuplas canónicas, ordenadas, únicas y no vacías cuando corresponda;
- campos mutuamente excluyentes según tipo;
- referencias de una sola cuenta;
- `decision_id`, `command_id`, revisión y relaciones coherentes;
- ausencia de metadatos privados en `repr`, `str` de errores o mensajes.

Reutilizá `Rubro`, `Intencion`, `Suscripcion`, `Proteccion` y `Confianza` desde
`model.py`. Consumí los modelos públicos D4 directamente desde
`classification_model.py`: `ClassificationResult` v2,
`SourceIdentityDescriptor` v1, `FlowIdentityDescriptor` v1,
`SourceAnchorKind` y `FlowAnchorKind`. No copies ni reimplementes normalización
privada de `classification_domain.py`.

## PREPARACIÓN TIPADA Y REPLAY

Implementá en `policy_domain.py` la operación pública equivalente a:

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

Debe materializar y validar toda la entrada antes de producir salida. Para una
decisión nueva:

1. verificá cuenta única, IDs únicos y versiones conocidas;
2. reconstruí la topología efectiva actual;
3. resolvé el selector en exactamente un objetivo admitido;
4. validá participantes completos de una unión;
5. validá que una partición tenga grupos no vacíos, disjuntos y cubra una sola
   vez todas las anclas actuales de una fuente automática;
6. detectá conflictos con políticas activas;
7. capturá selectores, IDs observados y contexto estructural canónicos;
8. devolvé un `PreparedPolicyDecision` distinto del comando crudo.

La preparación es pura: no abre SQLite ni archivos, no usa entorno, reloj,
aleatoriedad, logs o red y no crea IDs. Un objetivo inexistente produce
`target_not_found` antes de cualquier persistencia.

El repositorio ofrece:

```python
policy_event_for_command(command: LocalPolicyCommand) -> PolicyEvent | None
record_policy(prepared: PreparedPolicyDecision) -> PolicyEvent
undo_policy(command: UndoPolicy) -> PolicyEvent
policy_history(account_key: str) -> tuple[PolicyEvent, ...]
active_policies(account_key: str) -> tuple[ActivePolicy, ...]
```

El flujo correcto para una decisión es:

1. consultar `policy_event_for_command`;
2. si devuelve evento, terminar como replay sin volver a preparar;
3. si devuelve `None`, ejecutar `prepare_policy_decision`;
4. enviar el resultado a `record_policy`;
5. dentro de `record_policy`, repetir obligatoriamente la comprobación de
   `command_id` bajo `BEGIN IMMEDIATE` antes de revisar la revisión.

La consulta previa no reemplaza la comprobación transaccional. La igualdad de
replay compara el `PolicyDecisionCommand` original completo y tipado, no el
objeto preparado, su `repr` ni solamente un hash. Un comando idéntico devuelve
el evento previo aunque revisión o clasificación hayan cambiado; uno diferente
con el mismo `command_id` produce `command_id_conflict`. Nunca reemplaces el
binding histórico original durante un replay.

`record_policy` no debe aceptar un comando crudo como decisión nueva.
`UndoPolicy` no requiere preparación D4: `undo_policy` resuelve replay, revisión,
cuenta, actividad del objetivo, ciclos y reactivaciones contra el ledger dentro
de una sola transacción.

## APLICACIÓN Y RECONCILIACIÓN

Implementá la operación pública:

```python
apply_local_policies(
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    classification: ClassificationResult,
    policies: Iterable[ActivePolicy],
) -> PolicyApplicationResult
```

Reglas obligatorias:

1. Validá y materializá toda la entrada antes de calcular.
2. No mutes registros, clasificación, evidencias ni modelos D4.
3. Aplicá primero `MergeSources` y `PartitionSource`.
4. Las políticas estructurales v1 no se anidan.
5. Aplicá después nombres, rubros, intenciones y protecciones.
6. Reaplicá automáticamente sólo `EXACT` y `REBOUND`.
7. `NEEDS_REVIEW`, `AMBIGUOUS` y `CONFLICT` no cambian el valor efectivo,
   exigen revisión y protegen todos los candidatos afectados.
8. `ORPHANED` conserva política e historia, pero no afecta mensajes actuales.
9. Nunca elijas un candidato por nombre, dominio, asunto, cercanía o parecido.
10. Un remitente o etiqueta exactos pueden abarcar mensajes futuros; una fuente
    o flujo sólo persiste por su descriptor exacto.
11. Un ancla nueva en una partición lleva la política estructural a revisión.
12. Los IDs efectivos son opacos, versionados y deterministas, con prefijos
    `effective-source-v1-` y `effective-flow-v1-`.
13. Una unión conserva todos los mensajes y flujos; una partición no pierde ni
    duplica mensajes.
14. La evidencia efectiva agrega decisiones tipadas sin borrar evidencia D4.
15. Una política no cambia suscripción, autenticación ni confianza automática.
16. La confianza efectiva nunca mejora la peor confianza material participante.

## PROTECCIÓN CONSERVADORA

La protección es acumulativa y falla de forma segura:

- no existe comando para desproteger;
- `SENT`, `DRAFT` y `TRASH` siguen como exclusiones duras;
- `STARRED`, `IMPORTANT`, etiquetas protegidas, seguridad, recuperación,
  documentos, comprobantes, facturas, comunicación personal, baja confianza,
  contradicción y conversaciones mixtas siguen protegidas;
- `ProtectTarget` sólo puede agregar protección;
- una corrección hacia seguridad, documento o comunicación personal puede
  agregar protección;
- una corrección en sentido contrario nunca elimina una razón automática;
- cada salida conserva razones múltiples y `decision_id` aplicables;
- cualquier estado distinto de `EXACT` o `REBOUND` bloquea acciones futuras.

D5 no ejecuta acciones y no modifica `canExecute: false`.

## SQLITE Y MIGRACIÓN V3

En `repository.py` agregá exclusivamente la migración acumulativa v3 y las
operaciones D5. No modifiques el texto ni la semántica de las migraciones v1 y
v2. El script v3 no contiene su propio `BEGIN`, `COMMIT` o `ROLLBACK`: `_migrate`
ya controla la transacción y registra la versión después del DDL.

La migración crea como mínimo:

```text
local_policy_events
local_policy_anchors
local_policy_relations
```

El diseño relacional puede elegir nombres internos claros, pero debe demostrar:

- eventos append-only;
- columnas tipadas por comando, sin `payload_json`, `extra`, blobs ni
  serialización genérica;
- anclas normalizadas, versionadas, ordenadas y agrupadas explícitamente;
- relaciones normalizadas y cerradas para reemplazo, undo y contexto;
- unicidad de `(account_key, command_id)`, `(account_key, decision_id)` cuando
  corresponda y `(account_key, account_revision)`;
- claves foráneas compuestas que impidan referencias cruzadas entre cuentas;
- FK con cascada desde `indexed_accounts`;
- ninguna FK desde anclas hacia `indexed_messages`;
- checks que impidan combinaciones imposibles por tipo de comando;
- índices para historia por revisión, comando y relaciones;
- mismo esquema efectivo en base nueva y migrada desde v2;
- claves foráneas activas en todas las conexiones.

Dentro de una única `BEGIN IMMEDIATE`, `record_policy` debe:

1. buscar el `command_id` y resolver replay o conflicto;
2. validar `expected_revision` contra el ledger actual;
3. validar `decision_id`, reemplazos, conflictos y contexto preparado;
4. insertar evento, todas las anclas y todas las relaciones;
5. avanzar la revisión exactamente una vez;
6. revertir todo ante cualquier fallo.

No uses `ON CONFLICT DO UPDATE` sobre eventos. Dos preparados idénticos
concurrentes producen un solo evento y ambos observan ese mismo resultado. Dos
comandos con `command_id` distintos y la misma revisión esperada producen
exactamente un ganador; el otro obtiene `revision_conflict` sin escritura
parcial. Un mismo `command_id` se resuelve antes como replay exacto o
`command_id_conflict`.

Reconstruí `active_policies` desde un snapshot consistente usando una misma
conexión. No llames métodos públicos que abren otras conexiones desde dentro de
una transacción D5; agregá helpers privados que reciban la conexión existente.

`start_full_index` conserva políticas e historia. `delete_account_index` las
elimina por cascada sólo para esa cuenta. No cambies el comportamiento de D1.

Ninguna operación D5 puede crear ni recrear `indexed_accounts` o reutilizar
`_ensure_index_account`. `record_policy` y `undo_policy` deben comprobar la
existencia de la cuenta dentro de su `BEGIN IMMEDIATE`: una decisión preparada
para una cuenta ausente produce `target_not_found`; un undo nuevo produce
`invalid_transition`, sin escritura. Las consultas tampoco crean cuentas.

El borrado de cuenta es terminal: elimina también el ledger de idempotencia. Un
preparado, retry o undo anterior no puede resucitarla y ya no cuenta como replay
después del olvido. Probá la carrera con `delete_account_index`: si el borrado
gana, la escritura falla; si la escritura gana, el borrado posterior elimina
todo. En ambos órdenes el estado final queda olvidado.

## BARRERA DE SEGURIDAD

Ampliá `tests/test_base_segura_safety.py` de forma mínima:

- `policy_model.py` y `policy_domain.py` son los únicos consumidores nuevos
  permitidos de modelos públicos D4;
- esos dos módulos sólo pueden consumir D4 mediante
  `mailmap.classification_model`; tienen prohibido importar
  `mailmap.classification_domain` o `classify_indexed_records`;
- la allowlist no habilita `repository.py`, API, servicio, frontend ni otro
  módulo como consumidor de clasificación;
- `repository.py` no importa ningún módulo D4 y opera únicamente mediante tipos
  o factories públicos de `policy_model.py`;
- D5 no importa red, Gmail, OAuth, navegador, SQLite desde el dominio, logging,
  IA externa, reloj, aleatoriedad ni filesystem;
- no hay datos reales, secretos, tokens, credenciales, cuerpos, HTML, snippets,
  MIME, adjuntos, destinatarios ni encabezados genéricos;
- todo correo sintético usa `.example`;
- no aparecen rutas API, adaptadores productivos ni capacidades de ejecución;
- `oauthAvailable` continúa falso y `canExecute` continúa falso.

No debilites ninguna barrera D1-D4 para hacer pasar D5.

## PRUEBAS OBLIGATORIAS

En `tests/test_local_policy_memory.py`, con datos exclusivamente sintéticos,
cubrí las 25 familias de la sección 14 del contrato. Incluí expresamente:

- base nueva y base migrada exactamente desde v2 con igual esquema efectivo;
- rollback de una migración v3 fallida;
- rollback conjunto si falla la última relación después de evento y anclas;
- preparación que rechaza objetivo ausente, unión inválida y partición
  incompleta sin abrir escritura;
- rechazo de una decisión nueva cruda sin preparación;
- replay previo a preparación cuando el objetivo ya cambió o desapareció;
- carrera entre consulta previa y `record_policy`, cerrada nuevamente bajo lock;
- replay que compara el comando original y no reemplaza el binding guardado;
- idempotencia, `command_id_conflict` y revisión concurrente con un único
  ganador;
- dos preparados idénticos concurrentes que devuelven el mismo evento;
- undo idéntico después de desactivar el objetivo y undo conflictivo con el
  mismo `command_id`;
- historial ordenado por revisión, reemplazo explícito, reactivación y ciclos;
- `EXACT`, `REBOUND`, revisión, huérfano, ambigüedad y conflicto;
- crecimiento normal y cambios estructurales;
- correcciones de nombre, rubro e intención sin mutar D4;
- unión, partición, IDs efectivos y conservación exacta de membresía;
- no generalización por similitud;
- aislamiento estricto entre cuentas;
- todas las formas de protección y conversación mixta;
- imposibilidad de rebajar protección automática;
- escaneo completo que conserva políticas;
- borrado de una cuenta que elimina sólo su índice, políticas e historia;
- preparado, retry y undo viejos incapaces de recrear una cuenta borrada, en
  ambos órdenes concurrentes entre borrado y escritura;
- corrupción, versión desconocida y referencias cruzadas rechazadas;
- introspección real de columnas, checks, índices y claves foráneas;
- representaciones y errores redactados;
- ausencia de capacidades externas.

No modifiques las regresiones D1-D4 para adaptar expectativas, salvo la
ampliación de seguridad expresamente autorizada.

## SEGURIDAD Y LÍMITES

D5 utiliza únicamente datos sintéticos y dominios reservados `.example`.

D5 no autoriza:

- Gmail real o simulado mediante red;
- OAuth, navegador, credenciales o tokens;
- datos privados;
- cuerpos, HTML, snippets, MIME, adjuntos o destinatarios;
- persistencia de clasificaciones automáticas;
- API, servicio, frontend o UI;
- planes de limpieza o acciones;
- IA externa, telemetría o logging de metadatos;
- nuevas dependencias;
- D6 ni otra dependencia;
- uso productivo del índice o de la memoria.

Antes de datos reales siguen pendientes ubicación por usuario, ACL, cifrado
autenticado, retención, respaldo y borrado verificable. SQLite v3 no resuelve
esa puerta de privacidad.

## VALIDACIÓN OBLIGATORIA

Ejecutá desde el worktree:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_local_policy_memory.py
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_safety.py
.\.venv\Scripts\python.exe -m pytest tests\test_index_persistence.py tests\test_real_classification_domain.py tests\test_local_policy_memory.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
git status --short --untracked-files=all
git status --short --ignored --untracked-files=all
git diff -- src/mailmap/repository.py tests/test_base_segura_safety.py
git ls-files --others --exclude-standard
```

La base anterior a D5 tenía como evidencia 168 pruebas Python, Ruff aprobado,
mypy estricto sobre 17 módulos, 4 pruebas frontend y build Vite aprobado. D5
debe conservar toda esa cobertura; los nuevos conteos serán mayores.

No uses red ni ejecutes `setup.ps1` para reconstruir dependencias. Si el
worktree no contiene los runtimes ignorados, reutilizá temporalmente los ya
instalados en MAIN o los provistos por Codex, forzando `PYTHONPATH` al `src` de
este worktree. No modifiques scripts ni configuración. Retirá solamente enlaces,
cachés, bases, builds y temporales que vos hayas creado, sin usar `git clean` ni
borrar artefactos ajenos.

Una advertencia de permisos sobre `.pytest_cache`, la advertencia preexistente
Starlette/httpx o el aviso LF a CRLF deben informarse por separado; no cuentan
como pruebas fallidas si el proceso termina con código cero.

Revisá también:

- contenido completo de los tres archivos nuevos;
- diff completo de los dos archivos modificados;
- archivos ignorados y no rastreados;
- ausencia de secretos, correos no `.example`, bases y artefactos;
- ausencia de imports o consumidores fuera de la allowlist.

## PUNTOS DE DETENCIÓN

Detenete y devolvé el bloqueo si:

- ruta, rama, SHA o estado inicial no coinciden;
- necesitás un archivo fuera de los cinco autorizados;
- necesitás modificar un contrato, D4, API, frontend o dependencia;
- un comando nuevo podría persistirse sin `PreparedPolicyDecision`;
- una operación D5 podría crear o recrear `indexed_accounts`;
- el replay no puede resolverse antes de preparar y repetirse bajo lock;
- la migración v3 exige alterar v1 o v2;
- aparece otra migración concurrente;
- no podés aislar cuentas o mantener atomicidad completa;
- una política puede generalizarse por parecido o rebajar protección;
- necesitás Gmail, OAuth, red, navegador, credenciales o datos reales;
- una prueba requiere un servicio externo;
- la batería previa falla por una regresión real.

No cambies silenciosamente el contrato para superar un stop point.

## GIT

No hagas commit, push, merge, rebase, reset, clean, publicación ni integración
en `main`. No crees ramas, worktrees o remotos adicionales. Dejá los cinco
archivos como cambios auditables en tu worktree.

## DONE WHEN

D5 queda entregada para auditoría únicamente cuando:

1. la preparación tipada y el replay respetan exactamente el contrato;
2. la proyección conserva D4 automática y aplica sólo políticas válidas;
3. topología, reconciliación, undo y protección son conservadores;
4. la migración v3 es acumulativa, normalizada y atómica;
5. historial, idempotencia, concurrencia y aislamiento están probados;
6. Base Segura y D1-D4 permanecen verdes;
7. sólo existen cambios en los cinco archivos autorizados;
8. no quedan cachés, bases, builds, secretos ni datos privados;
9. no se ejecutó ninguna operación Git o externa prohibida;
10. el handoff informa pruebas aprobadas, omitidas, fallidas y no ejecutadas sin
    confundirlas.

## HANDOFF A MAIN

Entregá un único informe autosuficiente con:

1. `QUÉ HACE`.
2. `POR QUÉ EXISTE`.
3. ruta, rama, base, HEAD y estado inicial/final.
4. archivos creados o modificados.
5. modelos, preparación, replay y operaciones públicas.
6. reglas de identidad, topología, reconciliación y protección.
7. esquema v3, transacciones, idempotencia y concurrencia.
8. pruebas exactas ejecutadas y resultados exactos.
9. diff, no rastreados, ignorados y búsqueda de secretos/artefactos.
10. riesgos, limitaciones y casos que permanecen en revisión.
11. confirmación explícita de ausencia de Gmail, OAuth, navegador, red,
    credenciales, datos reales, API, UI, acciones, D6 y operaciones Git.

No declares D5 integrada. MAIN debe auditarla independientemente.

## QUÉ HACE, AL CIERRE

Deja una candidata D5 completa, sintética, verde y auditable en su worktree.

## POR QUÉ EXISTE, AL CIERRE

Permite que MAIN evalúe memoria y políticas locales sin confundir una entrega
especialista con integración ni abrir ninguna capacidad externa.
