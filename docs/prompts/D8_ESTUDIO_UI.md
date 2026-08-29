# Prompt D8 — Interfaz de Estudio de Limpieza

## QUÉ HACE

Implementa D8 `estudio-ui`: la experiencia React que consume la API local
`/api/v3/study` ya consolidada y permite crear, comprender, enumerar,
revalidar y cancelar planes sintéticos de Estudio de Limpieza.

La interfaz presenta una vista previa exacta y explicable. Archivo y Papelera
son intenciones inertes del plan: D8 no aprueba, ejecuta ni simula una mutación
sobre mensajes.

## POR QUÉ EXISTE

D7 ya congela objetivos, miembros, exclusiones, tamaños, muestras y eventos con
CAS, replay e idempotencia. D8 vuelve comprensible ese agregado sin trasladar al
navegador reglas de elegibilidad, clasificación o protección. Joa debe poder
entender qué ocurriría y qué queda fuera antes de considerar cualquier puerta
de Limpieza Controlada.

## ROL

Sos la dependencia especialista D8 `estudio-ui` de MailCleanup. No sos MAIN.
Implementá exclusivamente la interfaz sintética de Estudio de Limpieza y
devolvé una entrega auditable.

No redefinas el contrato, D7, la API, la arquitectura ni las reglas de
protección. Si una exigencia no puede cumplirse dentro del frontend autorizado,
detenete y devolvé el bloqueo a MAIN. Tu handoff no equivale a integración,
aceptación ni publicación.

## BASE Y WORKTREE OBLIGATORIOS

Base anterior al prompt verificada por MAIN:

```text
main: c8c7b3241d7731679fd9f775bb05c1c3d8acd38a
D7: integrada, consolidada y publicada
```

MAIN debe entregarte en el mensaje de despacho:

- ruta absoluta del único worktree D8;
- rama exacta `codex/estudio-ui`;
- SHA base limpio exacto que contiene este prompt y la autorización D8;
- estado esperado limpio.

Ese SHA debe descender de la base anterior. No lo sustituyas por `main` móvil,
otro commit o una rama parecida. Antes de editar ejecutá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git remote -v
```

Detenete si la ruta, rama, SHA o limpieza no coinciden. No uses `reset`,
`clean`, checkout destructivo, merge, rebase ni maniobras para ocultar una
divergencia.

`New folder/grafo.txt` es una excepción no rastreada conocida del worktree de
MAIN. No forma parte de D8: no lo leas, copies, edites, muevas, borres, stages ni
incluyas en ningún diff o commit.

`origin` puede aparecer por la configuración compartida. No lo uses: D8 no
autoriza fetch, pull, push, publicación ni otra red externa.

## LECTURA OBLIGATORIA

Leé completamente antes de implementar:

1. `AGENTS.md`;
2. este prompt;
3. `docs/CONTRATO_MVP.md`;
4. `docs/contracts/CLEANUP_PLAN_V1.md`;
5. `docs/contracts/SECURITY_PRIVACY_V1.md`;
6. `docs/contracts/MAPA_TOTAL_API_V1.md`;
7. la sección D8 y el protocolo de `docs/PLAN_DEPENDENCIAS.md`;
8. `docs/DECISIONES.md`, `docs/ESTADO_BASE_SEGURA.md` y
   `docs/WORKTREE_REGISTRY.md`;
9. `frontend/package.json`, configuración Vite/TypeScript/ESLint y todo
   `frontend/src`, incluidas pruebas y fixtures;
10. `src/mailmap/cleanup_plan_model.py` y
    `src/mailmap/cleanup_plan_api.py`, sólo para verificar la frontera pública;
11. `tests/test_cleanup_plan_api.py` y
    `tests/test_base_segura_safety.py`, sin modificarlas;
12. `scripts/check.ps1`, `scripts/run.ps1` y `pyproject.toml`.

Para D8 prevalecen `SECURITY_PRIVACY_V1.md` y `CLEANUP_PLAN_V1.md`. Si este
prompt o el frontend vigente los contradicen materialmente, no acomodes el
contrato: señalá archivo, sección y consecuencia y devolvé la decisión a MAIN.

## OBJETIVO VISIBLE

Entregá una experiencia local, minimalista, progresiva y responsive que permita:

1. reconocer siempre que trabaja con datos de demostración y sin efectos;
2. consultar disponibilidad sin perder acceso a planes ya congelados;
3. elegir objetivos públicos de fuente, flujo o remitente;
4. definir una intención inerte de Archivo o Papelera, fecha civil, lectura,
   etiquetas excluidas y últimos N por flujo;
5. revisar criterios antes de crear el estudio;
6. listar planes y comprender estado, caducidad, selección y exclusiones;
7. inspeccionar muestras, miembros y eventos mediante divulgación progresiva;
8. revalidar de forma conservadora y cancelar el plan local;
9. resolver replay, resultado incierto, conflictos y cursores obsoletos sin
   reenvíos ciegos;
10. funcionar en escritorio y a 390 px sin pérdida de información esencial.

## ALCANCE AUTORIZADO

Podés crear, modificar o eliminar exclusivamente:

```text
frontend/src/**
```

No modifiques `frontend/index.html`, `frontend/package.json`, lockfile,
configuración Vite/TypeScript/ESLint, backend, pruebas Python, contratos,
documentación ni scripts. No agregues dependencias.

Una organización recomendada, sin imponer nombres innecesarios, es:

```text
frontend/src/study/
├── types.ts
├── decoders.ts
├── api.ts
├── commands.ts
├── hooks.ts
├── test/fixtures.ts
├── components/**
├── pages/**
└── *.test.ts(x)
```

Los cambios transversales deben ser mínimos y pueden alcanzar `App.tsx`,
`routing.ts`, `Shell.tsx`, `Icon.tsx`, `styles.css`, `App.test.tsx` y las
primitivas compartidas vigentes. No anexes D8 a `CorrectionsPage.tsx`, no
mezcles eventos D5 con eventos D7 y no reutilices `WorkspaceData` para DTO v3.

No reintroduzcas el `PlanPage.tsx` legado ni la ruta `#/plan`. D8 consume el
agregado nuevo bajo una ruta propia.

## ARQUITECTURA FRONTEND EXIGIDA

La aplicación actual carga `useMapWorkspace()` antes de resolver la página. D8
debe separar el árbol por ruta mediante componentes hijos, sin hooks
condicionales:

```text
App
├── rutas de Mapa Total
│      ↓
│   MapApplication → workspace v2 vigente
│
└── #/study y detalle de plan
       ↓
    StudyApplication → workspace v3 propio
```

Esta separación es contractual:

- una falla de la fotografía actual de Mapa Total no puede impedir leer
  historia, detalle, miembros o eventos ya congelados;
- las rutas D6 no deben consultar `/api/v3/study`;
- Estudio no consulta `/api/v2/map` para reconstruir objetivos o elegibilidad;
- el bloqueo de Estudio no inutiliza Panorama, Fuentes, Correcciones o Estado;
- ninguna regla de selección, protección o revalidación se duplica en
  TypeScript.

Usá como ruta principal:

```text
#/study
```

y una ruta inequívoca para detalle:

```text
#/study/plans/{planId}
```

El rótulo visible del proceso es siempre **Estudio de Limpieza**. Conservá una
ruta desconocida como regresión de `not_found`. Agregá un enlace principal
descubrible con ese nombre en la navegación. Tanto `#/study` como
`#/study/plans/{planId}` deben mantenerlo marcado con `aria-current="page"`.

## COMPOSICIÓN DE CONTEXTOS

D8 debe integrar sin confundir:

- `GET /api/v2/context`, que conserva
  `capabilities.cleanupPlan: false` por contrato de Mapa Total;
- `GET /api/v3/study/context`, autoridad de capacidades y disponibilidad de
  Estudio de Limpieza.

No cambies el valor v2 a `true` y no lo uses para bloquear D8. Al entrar a
Estudio, comprobá la compatibilidad de ambos contextos sin cargar el mapa ni las
otras cinco lecturas v2.

El contexto v3 debe exigir exactamente `contractVersion: 1`,
`dataMode: synthetic`, `canExecute: false`, límites contractuales y estas
capacidades:

```text
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
```

Una incompatibilidad de contrato, modo o capacidades bloquea los comandos D8 de
forma cerrada. La disponibilidad dinámica no bloquea toda la aplicación:
historia, detalle, miembros, eventos y cancelación permanecen accesibles según
el contrato aunque catálogo, creación o revalidación no estén disponibles.

## FRONTERA HTTP CERRADA

D8 consume exactamente estas nueve rutas relativas:

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

La única lectura adicional admitida en la integración es
`GET /api/v2/context`, por la composición exigida en la sección anterior. No
uses `/api/v1`, otras rutas v2 ni inventes endpoints.

El transporte debe:

- usar paths relativos y ninguna base URL configurable;
- usar `credentials: "omit"`, `mode: "same-origin"` y `redirect: "error"`;
- no enviar cookies ni headers de autorización;
- enviar `Content-Type: application/json` sólo en `POST`;
- no intentar escribir el header `Origin` desde JavaScript;
- codificar `planId`, filtros y cursores con las primitivas correctas;
- limitar cada cuerpo a 64 KiB antes de enviar;
- aplicar un timeout acotado y tratar un fallo posterior a un `POST` como
  resultado incierto;
- interpretar exclusivamente el sobre de error v3 cerrado;
- reemplazar respuestas malformadas o fallos de transporte por mensajes locales
  seguros;
- no registrar requests, responses, IDs, cursores, direcciones, asuntos,
  cuerpos ni excepciones crudas.

El error v3 contiene `contractVersion`, `dataMode`, `canExecute` y `error`; no
relajes el decodificador v2 para aceptarlo. Implementá una frontera tipada v3 o
una separación equivalente.

## DTO CERRADOS

Modelá en TypeScript todas las uniones y respuestas de
`CLEANUP_PLAN_V1.md`. Rechazá campos extra, enums desconocidos, booleanos donde
se exige entero, fechas no canónicas, IDs o cursores inválidos, cardinalidades y
capacidades inesperadas.

No uses `any`, índices arbitrarios, payloads genéricos ni casts amplios para
silenciar diferencias. Reutilizá el patrón estricto vigente de decodificación,
sin importar modelos Python.

Traducí de forma local y cerrada:

- los cinco estados de plan;
- los seis estados de inventario;
- los cinco filtros de miembros;
- los cinco tipos de evento;
- los cuatro warnings;
- los 21 motivos de exclusión y retiro;
- todos los errores públicos v3.

Las colecciones que el contrato declara únicas y ordenadas —en particular
motivos y warnings— deben conservar el orden contractual y el decodificador
debe rechazar duplicados o desorden, no corregirlos silenciosamente.

No uses el texto recibido del servidor como HTML ni como explicación técnica.
Los mensajes visibles de error son constantes locales por código.

## CATÁLOGO Y CONSTRUCTOR

El catálogo se pagina por `kind`, cursor y límite. Los objetivos seleccionables
son únicamente:

- `source`;
- `flow`;
- `sender`.

Los elementos `label` sirven exclusivamente para `excludedLabelIds` y nunca
entran en `targets[]`. No aceptes valores escritos libremente, IDs remotos,
cuentas, selectores D5 ni direcciones proporcionadas por el usuario.

El constructor debe usar etapas comprensibles:

1. **Qué estudiar:** de 1 a 100 objetivos públicos únicos.
2. **Intención:** exactamente Archivo o Papelera como disposición inerte.
3. **Período y lectura:** una variante temporal cerrada y `any`, `read` o
   `unread`.
4. **Exclusiones:** hasta 100 etiquetas de sistema y `keepLatestPerFlow` entre
   0 y 10.000.
5. **Revisión final:** resumen canónico antes de crear.

Las fechas son fechas civiles de `America/Argentina/Cordoba`. Explicá que
`beforeDate` es exclusiva, que el rango incluye el inicio y excluye el final, y
que `olderThanDays` usa días civiles completos. No conviertas la UI en autoridad
del corte UTC persistido.

La creación usa las revisiones `mapRevision` y `policyRevision` de la misma
respuesta de catálogo. Si cambia la fotografía, conservá el formulario para
revisión, refrescá explícitamente y no reenvíes en forma automática.

Un universo no vacío completamente excluido produce un plan válido en estado
`invalidated`; no lo presentes como fallo de creación.

## PLANES, DETALLE Y PAGINACIÓN

El historial muestra primero un resumen breve: estado, disposición, creación,
vencimiento, conteos y volumen estimado. Permite filtrar por estado y paginar
sin interpretar el cursor.

El detalle muestra siempre, fuera de paneles plegables:

- estado efectivo;
- intención Archivo o Papelera;
- cantidad y tamaño vigentes;
- creación, vencimiento y última revalidación;
- warnings críticos presentes y selección reducida, cuando correspondan;
- fotografía actual no disponible sólo cuando el warning contractual
  `current_snapshot_unavailable` esté presente;
- texto inequívoco: “Vista previa sin efectos; no modifica Gmail”.

Usá divulgación progresiva para:

- objetivos y filtros congelados;
- muestras incluidas y excluidas;
- miembros y sus razones;
- eventos completos;
- revisiones e IDs de diagnóstico.

Los snapshots de nombres son históricos e inmutables. No los sustituyas por
nombres actuales del mapa.

Los miembros admiten exactamente `all`, `selected`, `eligible`, `excluded` y
`removed`. `selected` y `removed` se superponen deliberadamente: un retirado
sigue perteneciendo a la selección original y no se vuelve una exclusión
inicial.

Para objetivos, planes, miembros y eventos:

- tratá `nextCursor` como opaco;
- mantené ruta, filtro y límite de la página original;
- no mezcles resultados de revisiones distintas;
- ante `cursor_stale` o `invalid_cursor`, descartá la colección acumulada y
  ofrecé reiniciar explícitamente desde la primera página;
- no reinicies ni reenvíes en silencio.

## ESTADOS, REVALIDACIÓN Y CANCELACIÓN

Representá exactamente:

```text
frozen
reduced
invalidated
cancelled
expired
```

El servidor es autoridad del vencimiento. Podés mostrar tiempo restante como
ayuda, pero no cambiar localmente el estado contractual.

La revalidación:

- se ofrece sólo en `frozen` o `reduced`, con fotografía completa y revisiones
  actuales disponibles;
- envía revisión de plan, mapa y política actuales;
- puede conservar, reducir o invalidar;
- nunca agrega ni reincorpora mensajes;
- después de éxito o replay relee el detalle y refresca contexto e historial.

La cancelación:

- se ofrece sólo en `frozen` o `reduced`;
- envía la revisión vigente del plan;
- cancela exclusivamente el plan local;
- no revierte, mueve ni modifica mensajes;
- permanece disponible aunque la fotografía actual no pueda materializarse.

No muestres botones llamados “Aprobar”, “Ejecutar”, “Archivar ahora”, “Mover a
Papelera ahora” o “Desuscribir”. Los verbos permitidos son “Crear estudio”,
“Revalidar alcance” y “Cancelar plan”.

## TAMAÑOS Y EFECTOS

Mostrá por separado:

- tamaño estimado seleccionado al crear;
- tamaño estimado excluido al crear;
- tamaño estimado actualmente elegible;
- `effectiveFreedBytes: null` como ausencia de una medición de liberación.

Para Archivo, `storageEffect: none`: archivar no libera almacenamiento. Para
Papelera, `storageEffect: not_guaranteed`: mover a Papelera no garantiza una
liberación inmediata ni definitiva.

No uses “espacio recuperable”, “espacio liberado”, “ahorro” ni una equivalencia
entre bytes seleccionados y almacenamiento efectivamente liberado.

## COMANDOS, CAS, REPLAY Y RESULTADO INCIERTO

Cada comando nuevo usa `crypto.randomUUID()` y un UUID v4 distinto. Mientras un
`POST` está pendiente, deshabilitá el doble envío y marcá el formulario con
`aria-busy`.

No hagas actualización optimista. Después de cualquier éxito o replay:

1. releé `GET /plans/{planId}`;
2. refrescá contexto e historial;
3. recién entonces presentá el estado actual.

Si el comando fue aceptado pero la relectura falla, informá que el estado no
pudo confirmarse y que no debe reenviarse como comando nuevo.

Ante timeout o fallo de transporte de un `POST`:

- conservá en memoria el mismo `commandId`, ruta y cuerpo serializado;
- marcá el resultado como incierto;
- no reintentes automáticamente;
- no generes otro UUID;
- permití repetir exactamente el mismo envío sólo después de una acción
  explícita de Joa;
- cualquier edición del formulario invalida ese retry y genera un comando nuevo
  al confirmar.

Ante `map_revision_conflict`, `policy_revision_conflict` o
`plan_revision_conflict`, conservá el formulario, mostrá un alerta, ofrecé
actualizar y nunca reenvíes automáticamente con revisiones nuevas.

`command_id_conflict` bloquea el replay de ese cuerpo. Sólo una nueva decisión
confirmada puede generar otro comando.

## ERRORES Y RECUPERACIÓN

Implementá el catálogo exacto v3 y caminos seguros:

- `map_revision_conflict`, `policy_revision_conflict`: actualizar contexto y
  catálogo, manteniendo la selección para revisión manual;
- `plan_revision_conflict`: actualizar detalle sin repetir el comando;
- `cursor_stale`, `invalid_cursor`: descartar páginas y reiniciar sólo por
  acción explícita;
- `plan_expired`, `invalid_transition`: actualizar detalle y explicar el estado
  terminal;
- `target_not_found`: actualizar catálogo;
- `plan_too_large`: pedir menos objetivos; no sugerir que filtros posteriores
  eluden el límite;
- `inventory_incomplete`, `account_unavailable`, `study_unavailable`: bloquear
  catálogo/creación/revalidación y mantener lecturas históricas;
- respuesta desconocida o malformada: cierre seguro, sin comandos disponibles.

No dejes una pantalla en carga indefinida ni muestres payloads o excepciones.

## JERARQUÍA MINIMALISTA

Preservá la identidad visual aceptada de D6 y su divulgación progresiva. No
repliques la densidad de `CorrectionsPage`.

La pantalla inicial muestra sólo:

1. estado seguro y disponibilidad;
2. acción principal para crear un estudio;
3. planes recientes con resumen breve;
4. advertencias bloqueantes.

El constructor despliega una etapa por vez y conserva un resumen visible. El
detalle presenta primero el estado y el alcance actual. Criterios, muestras,
razones, miembros, eventos e IDs se abren cuando aportan contexto.

Nunca ocultes dentro de un panel cerrado:

- estado invalidado, cancelado o vencido;
- selección reducida;
- fotografía actual no disponible;
- conflicto o resultado incierto;
- ausencia de capacidad de ejecución;
- protecciones y exclusiones relevantes para el resumen.

No uses tablas que requieran desplazamiento lateral. IDs y textos largos deben
quebrarse o truncarse visualmente conservando acceso al valor permitido.

## ACCESIBILIDAD Y RESPONSIVE

En escritorio y a un viewport CSS de 390 px:

- evitá todo overflow horizontal;
- mantené controles táctiles de al menos 44 px;
- no comuniques estados sólo por color;
- respetá `prefers-reduced-motion`;
- preservá menú móvil, cierre por Escape, fondo inerte y retorno de foco;
- recuperá foco al contenido al cambiar de ruta;
- permití completar formularios y paginación sólo con teclado.

Exigencias semánticas:

- un único `h1` por ruta;
- `fieldset` y `legend` para objetivos, disposición, período, lectura y
  exclusiones;
- labels asociados y errores de campo mediante `aria-describedby`;
- `role="status"` o región viva para carga, éxito y cambios de conteos;
- `role="alert"` para conflictos, bloqueos y errores;
- nombres accesibles inequívocos en botones y paginación;
- texto explícito para las fechas civiles de Córdoba y la ausencia de efectos.

## SEGURIDAD Y PRIVACIDAD

D8 trabaja exclusivamente con el fixture sintético `.example` servido por D7.

Queda prohibido:

- Gmail, OAuth, navegador de autorización, SDK Google, credenciales, tokens o
  datos reales;
- requests fuera del origen local y las rutas enumeradas;
- guardar formularios o respuestas en `localStorage`, `sessionStorage`,
  IndexedDB, archivos, cookies o caché persistente;
- WebSocket, telemetría, analytics o logs de metadatos;
- `dangerouslySetInnerHTML`, HTML de correo, snippets, MIME, adjuntos,
  destinatarios, cabeceras genéricas o recursos remotos;
- linkificar asuntos, remitentes o direcciones;
- exponer `account_key`, `provider_message_id`, selectores D5 o IDs remotos;
- aprobación, ejecución, Archivo/Papelera reales, desuscripción o cualquier
  acción sobre mensajes;
- D9, Limpieza Controlada y controles que anticipen esas capacidades;
- dependencias nuevas o cambios fuera de `frontend/src/**`.

La UI debe mantener visible: “Vista previa sin efectos; no modifica Gmail”.

## ESTADOS OBLIGATORIOS

La interfaz y sus pruebas cubren al menos:

- carga, vacío, error local y respuesta inválida;
- cuenta sintética ausente;
- inventario `not_started`, `running`, `paused`, `completed`,
  `requires_full_resync` y `failed`;
- historia legible con fotografía actual no disponible;
- catálogo disponible y bloqueado;
- plan `frozen`, `reduced`, `invalidated`, `cancelled` y `expired`;
- creación completamente excluida e invalidada;
- los cuatro warnings contractuales;
- muestras nulas y acotadas;
- paginación de objetivos, planes, miembros y eventos;
- filtros `all`, `selected`, `eligible`, `excluded` y `removed`;
- creación pendiente, éxito, replay, conflicto y resultado incierto;
- revalidación sin cambios, reducida e invalidada;
- cancelación y cada estado terminal;
- cursores obsoletos o inválidos;
- todos los errores públicos v3;
- ausencia de controles de ejecución o Limpieza Controlada.

## PRUEBAS OBLIGATORIAS

Usá fixtures TypeScript derivados de las respuestas D7 y únicamente correos
`.example`. No importes modelos Python.

Como mínimo probá:

1. rutas D6 que continúan usando únicamente v2;
2. composición exacta de `/api/v2/context` y `/api/v3/study/context`;
3. las nueve rutas v3, métodos, queries, segmentos y cursores;
4. transporte relativo, `credentials: "omit"`, same-origin, sin auth/cookies y
   JSON sólo en POST;
5. DTO y errores cerrados, con campos extra rechazados;
6. contexto incompatible que bloquea D8 sin romper Mapa Total;
7. navegación descubrible “Estudio de Limpieza”, `#/study`, detalle, estado
   activo, foco y `not_found`;
8. catálogo, constructor y validación de las cuatro variantes temporales;
9. etiquetas sólo como exclusiones y límites del formulario;
10. historial, detalle, miembros, eventos y paginación;
11. selected/removed superpuestos sin reclasificación incorrecta;
12. tamaños y efecto de almacenamiento presentados sin promesa falsa;
13. doble envío bloqueado, CAS, replay y relectura posterior;
14. resultado incierto con retry exacto y nunca automático;
15. conflicto con formulario conservado y actualización explícita;
16. revalidación monotónica y cancelación local sin efectos;
17. carga, vacío, disponibilidad bloqueada, warnings y estados terminales;
18. navegación y menú móvil semánticos;
19. ausencia de `/api/v1`, URLs externas, almacenamiento persistente, recursos
    remotos, HTML peligroso y datos no `.example`;
20. ausencia de aprobación, ejecución, Gmail, OAuth, credenciales, datos reales,
    acciones sobre mensajes y D9.

La prueba vigente que rechazaba Estudio debe sustituirse expresamente por la
nueva ruta. Conservá otra ruta desconocida como prueba de `not_found` y no
debilites las regresiones de Mapa Total.

## VALIDACIÓN OBLIGATORIA

Ejecutá desde el worktree:

```powershell
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
.\.venv\Scripts\python.exe -m pytest tests\test_cleanup_plan_api.py tests\test_base_segura_safety.py
.\scripts\check.ps1
git diff --check
git status --short --untracked-files=all
git status --short --ignored --untracked-files=all
git diff -- frontend/src
git ls-files --others --exclude-standard -- frontend/src
```

La base D7 publicada tiene como evidencia 391 pruebas Python, Ruff aprobado,
mypy estricto sobre 27 archivos, ESLint, 98 pruebas Vitest y build Vite. Repetí
la batería: ese informe previo no reemplaza tu validación.

No uses red para reconstruir entornos. Reutilizá temporalmente `.venv`, Node,
pnpm y dependencias ya instaladas en MAIN o provistas por Codex sin modificar
configuración. Si creás enlaces o artefactos locales, retirá únicamente los
tuyos al terminar; no uses `git clean`.

Realizá además, si las herramientas funcionan:

1. recorrido HTTP local desde `http://127.0.0.1:8765`;
2. revisión visual en escritorio;
3. revisión visual con viewport CSS exacto de 390 px;
4. historial vacío y poblado, constructor, detalle, miembros, eventos,
   conflicto y estado bloqueado;
5. navegación completa por teclado y menú móvil;
6. inspección de consola y de requests para confirmar cero recursos externos.

Comprobá `scrollWidth <= clientWidth`. La revisión especialista no reemplaza la
auditoría visual final de MAIN y Joa. Si una herramienta no funciona, registrá
el pendiente; no afirmes que la usaste.

Retirá antes del handoff `frontend/dist`, cachés, bases, logs, temporales y
enlaces creados por vos. No borres un artefacto preexistente ni `.venv` o
`node_modules` ajenos.

## PUNTOS DE DETENCIÓN

Detenete y devolvé el bloqueo si:

- ruta, rama, SHA o estado inicial no coinciden;
- necesitás tocar fuera de `frontend/src/**`;
- necesitás backend, contrato, API, script, configuración o dependencia nueva;
- necesitás cambiar `cleanupPlan: false` de `/api/v2/context`;
- no podés leer planes congelados sin una fotografía actual disponible;
- no podés conservar exactamente un retry incierto;
- una respuesta D7 exige inferir reglas no publicadas;
- necesitás IDs remotos, cuenta interna o selectores privados;
- aparece cualquier ruta o control de aprobación o ejecución;
- necesitás Gmail, OAuth, red externa, credenciales o datos reales;
- necesitás almacenamiento persistente del navegador;
- una prueba requiere un servicio externo;
- la batería base falla por una regresión real;
- el diff contiene bases, builds, cachés, secretos, datos privados o
  `grafo.txt`.

No cambies silenciosamente el contrato para superar un punto de detención.

## GIT

No hagas commit, push, fetch, pull, merge, rebase, reset, clean, publicación ni
integración en `main`. No crees ramas, worktrees ni remotos adicionales. Dejá
únicamente el diff frontend auditable en tu worktree.

## DONE WHEN

D8 queda entregada para auditoría únicamente cuando:

1. la subaplicación de Estudio carga por ruta propia y no depende del mapa
   actual para leer historia congelada;
2. ambos contextos se componen sin cambiar `cleanupPlan: false` de v2;
3. sólo se consumen las nueve rutas v3 y el contexto v2 permitido;
4. DTO, errores, cursores, CAS, replay y retry incierto respetan C6;
5. crear, listar, detallar, paginar, revalidar y cancelar funcionan sin efectos;
6. información completa y alertas críticas usan una jerarquía progresiva clara;
7. `canExecute: false` y la ausencia de efectos permanecen visibles;
8. escritorio y 390 px son utilizables, accesibles y sin overflow;
9. lint, pruebas, build, batería global y HTTP aprueban;
10. sólo existen cambios dentro de `frontend/src/**`;
11. no quedan builds, cachés, bases, secretos ni datos privados;
12. no se realizó ninguna operación Git o externa prohibida.

## HANDOFF A MAIN

Entregá un único informe autosuficiente con:

1. `QUÉ HACE`.
2. `POR QUÉ EXISTE`.
3. ruta, rama, base, HEAD y estado inicial/final.
4. archivos creados, modificados o eliminados.
5. arquitectura route-aware, transporte, rutas y DTO v3.
6. estados, constructor, paginación, comandos, conflictos y decisiones UX.
7. pruebas y validaciones exactas con conteos.
8. recorrido HTTP y revisión visual realmente ejecutados.
9. diff, no rastreados, ignorados y búsqueda de secretos/artefactos.
10. riesgos, limitaciones y pendientes.
11. confirmación explícita de ausencia de Gmail, OAuth, red externa,
    credenciales, datos reales, backend, nuevas dependencias, aprobación,
    ejecución, acciones sobre mensajes, D9 y operaciones Git.

No declares D8 integrada, aceptada ni publicada. MAIN debe auditarla y Joa debe
revisar la experiencia antes de cualquier proceso posterior.

## QUÉ HACE, AL CIERRE

Deja una candidata D8 sintética, minimalista, responsive y auditable en su
worktree especialista.

## POR QUÉ EXISTE, AL CIERRE

Permite que MAIN y Joa evalúen una vista previa exacta antes de considerar
Limpieza Controlada, sin confundir planificación con ejecución.
