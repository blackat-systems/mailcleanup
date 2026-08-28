# Prompt D6 — Mapa Total UI

## QUÉ HACE

Implementa la dependencia especialista D6 `mapa-total-ui`: la experiencia React
que consume la API local `/api/v2` ya consolidada y permite comprender el mapa
sintético de fuentes y flujos, su evidencia, protecciones, estado de inventario
y decisiones locales reversibles.

D6 migra la superficie activa desde los DTO de Base Segura `/api/v1` hacia el
contrato cerrado de Mapa Total. No conecta una cuenta, no controla una
sincronización y no propone ni ejecuta limpieza.

## POR QUÉ EXISTE

C5 ya compone D1, D4 y D5 en una fotografía coherente, versionada y sintética.
D6 vuelve comprensible esa proyección sin copiar al navegador las reglas de
clasificación, precedencia o protección. La persona puede distinguir qué fue
observado, qué fue inferido y qué decidió Joa antes de autorizar datos reales o
un proceso posterior.

## ROL

Sos la dependencia especialista D6 `mapa-total-ui` de MailCleanup. No sos MAIN.
Implementá exclusivamente la interfaz sintética de Mapa Total. Tu entrega será
evidencia parcial para una auditoría independiente de MAIN: no la declares
integrada, aceptada ni publicada.

## UBICACIÓN Y BASE OBLIGATORIAS

- Worktree: el checkout aislado creado por Codex para esta tarea.
- Rama esperada: una rama `codex/*` exclusiva de D6; MAIN informará su nombre
  real en el mensaje de despacho.
- Commit base: el SHA exacto que MAIN informe al crear el worktree. Debe ser el
  commit limpio que contiene C5, este prompt y la autorización D6.
- Estado inicial esperado: limpio, sin archivos no rastreados.
- Remoto: puede existir `origin` por configuración conocida de MAIN; no lo uses.

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
4. `docs/contracts/MAPA_TOTAL_API_V1.md`.
5. `docs/contracts/SECURITY_PRIVACY_V1.md`.
6. `docs/contracts/API_V1.md`, sólo para preservar compatibilidad del backend;
   D6 no consume sus DTO.
7. La sección D6 y el protocolo de `docs/PLAN_DEPENDENCIAS.md`.
8. `docs/DECISIONES.md`.
9. `frontend/package.json`, `frontend/vite.config.ts` y los `tsconfig`.
10. Todo `frontend/src`, incluidas pruebas, fixtures, páginas, componentes y CSS.
11. `src/mailmap/map_api.py` y `src/mailmap/map_model.py` sólo como evidencia de
    la frontera HTTP; no importes código Python ni los modifiques.
12. `tests/test_map_api.py` y `tests/test_base_segura_safety.py` para entender las
    barreras ya verificadas; no los modifiques.
13. `scripts/check.ps1`, `scripts/run.ps1` y `pyproject.toml`.

Para D6 prevalecen `SECURITY_PRIVACY_V1.md` y `MAPA_TOTAL_API_V1.md`. No los
modifiques para acomodar la interfaz. Ante una contradicción material, detenete
y devolvela a MAIN.

## OBJETIVO VISIBLE

Entregar una aplicación local, clara y responsive que permita:

1. reconocer de inmediato que usa datos de demostración sintéticos;
2. ver estado de conexión, índice y sincronización sin controles inexistentes;
3. comprender volumen, período, fuentes, flujos y protecciones;
4. recorrer una fuente y hasta cinco muestras de metadatos permitidos;
5. comparar valores automáticos con valores efectivos decididos por Joa;
6. inspeccionar evidencia automática y evidencia de políticas sin mezclarlas;
7. revisar decisiones que necesitan atención;
8. registrar las siete decisiones D5 admitidas por C5 y deshacer las que sean
   `undoable`;
9. manejar carga, vacío, parcialidad, conflictos y errores sin prometer acciones
   no disponibles;
10. funcionar en escritorio y a 390 px sin pérdida de información esencial.

## ALCANCE AUTORIZADO

Podés crear, modificar o eliminar exclusivamente:

```text
frontend/src/**
frontend/index.html
```

Una eliminación dentro de `frontend/src` sólo está permitida cuando retira una
pantalla o módulo v1 sin consumidores después de la migración. Conservá y adaptá
primitivas, iconos SVG locales, estilos y utilidades que sigan siendo útiles.

No modifiques `frontend/package.json`, lockfile, configuración Vite/TypeScript o
ESLint. No agregues dependencias. React, el navegador, Testing Library y Vitest
vigentes alcanzan para esta entrega.

La organización interna recomendada, sin volverla un requisito nominal, es:

```text
tipos cerrados de API v2
        ↓
cliente HTTP same-origin
        ↓
workspace de lecturas, revisiones y mutaciones
        ↓
rutas/páginas de Panorama, Fuentes, Detalle, Correcciones y Estado
        ↓
componentes y estilos responsive
```

Separá estado de transporte, estado de formulario y proyección recibida. No
actualices clasificación o políticas de forma optimista.

## FRONTERA HTTP CERRADA

D6 consume únicamente rutas relativas bajo `/api/v2`:

```text
GET  /context
GET  /connection
GET  /sync
GET  /index
GET  /map
GET  /map/sources/{sourceId}
GET  /decisions
POST /decisions
POST /decisions/{decisionId}/undo
```

No uses `/api/v1` desde la superficie activa, aunque el backend la conserve. No
inventes rutas para conectar, autorizar, escanear, pausar, reanudar, refrescar,
revocar, olvidar, borrar, planificar o ejecutar.

El cliente debe:

- usar únicamente paths relativos; no aceptar una base URL configurable;
- usar `credentials: "omit"` en todas las solicitudes;
- no enviar cookies ni headers de autorización;
- enviar `Content-Type: application/json` sólo en los `POST`;
- dejar que el navegador produzca naturalmente el `Origin` same-origin; nunca
  intentar escribir manualmente el header prohibido `Origin`;
- codificar `sourceId` y `decisionId` como segmentos de path;
- interpretar el error cerrado `{error: {code, message}}`;
- reemplazar respuestas malformadas o errores de transporte por mensajes
  locales seguros, sin concatenar payloads ni excepciones;
- no registrar requests, responses, IDs, direcciones, asuntos o errores crudos.

No incorpores un SDK, cliente Gmail, OAuth, WebSocket, telemetría, analytics ni
otra conexión. La aplicación productiva sigue servida sólo desde
`http://127.0.0.1:8765`; el proxy Vite existente es únicamente desarrollo local.

## TIPOS Y CAPACIDADES

Modelá en TypeScript uniones discriminadas y DTO cerrados que reflejen
`MAPA_TOTAL_API_V1.md`. No uses `any`, índices arbitrarios, extensiones genéricas
o casting amplio para silenciar diferencias.

El frontend siempre toma capacidades de `GET /context`. No las calcula a partir
del modo ni las activa por conveniencia. En esta entrega deben verse y probarse:

```text
dataMode: synthetic
mapRead: true
policyWrite: true
policyUndo: true
gmailConnection: false
oauth: false
externalNetwork: false
realData: false
syncControl: false
cleanupPlan: false
messageMutation: false
unsubscribe: false
execute: false
```

Si el contrato, modo o capacidades son incompatibles con D6, mostrale a la
persona un estado bloqueado y no renderices controles de escritura.

Reutilizá exactamente los valores cerrados de Rubro, Intención, Suscripción,
Confianza, Protección, estado de binding y estado de sincronización. Podés
asignarles etiquetas explicativas de presentación, pero no sumar taxonomías ni
replicar reglas de precedencia.

## RECORRIDO DE LA INTERFAZ

La navegación activa de Mapa Total debe contener, como mínimo:

- **Panorama**: resumen, condición parcial, período y volumen mensual;
- **Fuentes**: lista, búsqueda y filtros puramente presentacionales;
- **Detalle de fuente**: identidad, flujos, evidencia, protección y muestra;
- **Correcciones**: decisiones, estado de binding, revisión y undo;
- **Estado**: contexto, conexión, índice y sincronización de sólo lectura.

Retirá del recorrido activo:

- `#/plan` y Estudio de Limpieza;
- selección “Sumar al plan”;
- candidatos, recomendaciones o intención dominante de fuente;
- espacio recuperable;
- botones para conectar Gmail, iniciar OAuth, sincronizar, pausar, reanudar,
  borrar el índice, archivar, enviar a Papelera, desuscribir o ejecutar.

No presentes “mapa real”, “cuenta conectada” o “Gmail analizado”. Usá lenguaje
honesto como “Mapa Total con datos de demostración” y “estado sintético”.

## VISTAS DE FUENTES

Fuente y Flujo permanecen separados. No calcules una intención o suscripción
dominante para una fuente.

Las vistas auxiliares son filtros sobre campos explícitos, no nuevos inventarios:

- **Suscripciones**: incluir una fuente si alguno de sus flujos tiene
  `subscription` exactamente en `Confirmada`, `Probable`, `Baja solicitada` o
  `Posible incumplimiento`;
- **Spam**: incluirla si algún flujo tiene `effectiveIntention` exactamente
  `Sospechoso`;
- **Protegidas**: incluirla si `protectedMessageCount > 0`.

No incluyas `Desconocido` por aproximación ni uses nombre, dominio o asunto para
decidir pertenencia. Permití además filtrar por valores individuales de los
enums sin inferir relaciones nuevas.

## INFORMACIÓN Y EXPLICABILIDAD

Mostrá de forma inequívoca:

- valores **automáticos** y **efectivos** cuando difieran;
- las decisiones de Joa como una capa agregada, nunca como evidencia automática;
- confianza baja o contradictoria;
- protección automática, efectiva, revisión obligatoria y exclusión dura;
- razones múltiples de protección sin resumirlas en una falsa causa única;
- `partial: true` como “mapa parcial” en cualquier estado no completado;
- `totalBytes` como “volumen indexado estimado”, nunca espacio liberable;
- primera y última aparición conocidas;
- evidencia de clasificación con fuerza y origen;
- evidencia de política con su `decisionId`, sin revelar selectores internos;
- bindings `NEEDS_REVIEW`, `ORPHANED`, `AMBIGUOUS` y `CONFLICT` como estados que
  requieren revisión, sin aplicarlos silenciosamente.

Las muestras respetan el máximo de cinco elementos y muestran únicamente los
campos de `recentMessages`. No renderices HTML, snippets, MIME, adjuntos,
destinatarios, cabeceras genéricas, URLs ni contenido remoto.

## ESTADO DE SINCRONIZACIÓN

Representá y probá:

```text
not_started
running
paused
completed
requires_full_resync
failed
```

Mostrá `processedCount`, fechas disponibles, modo y `errorCode` cerrado. D6 sólo
informa estos estados. No ofrece controles de inicio, pausa, reanudación o
resincronización porque `syncControl` es `false` y C5 no publica esos comandos.

## CORRECCIONES D5

Implementá formularios explícitos para los siete tipos admitidos:

1. `setSourceDisplayName`;
2. `setSourceRubro`;
3. `setFlowDisplayName`;
4. `setFlowIntention`;
5. `mergeSources`;
6. `partitionSource`;
7. `protectTarget`.

También implementá undo mediante la ruta separada para eventos `undoable`.

Todo comando nuevo debe usar:

- `commandId` UUID v4 nuevo con `crypto.randomUUID()`;
- `decisionId` UUID v4 nuevo para una decisión;
- `occurredAt` UTC terminado en `Z` mediante `new Date().toISOString()`;
- `expectedMapRevision` y `expectedPolicyRevision` de la proyección vigente;
- `supersedesDecisionIds: []` en D6 v1.

D6 no adivina reemplazos. Si ya existe una corrección activa incompatible, el
usuario debe deshacerla primero desde el historial. Un `policy_conflict` explica
ese recorrido; no sintetices relaciones `supersedes` desde parecido.

Reglas de interacción:

- normalizá y validá nombres entre 1 y 120 caracteres antes de enviar;
- usá únicamente IDs, remitentes y etiquetas expuestos por la API;
- nunca envíes `accountKey`, selectores D5, reglas por dominio, notas libres ni
  campos extra;
- deshabilitá el envío mientras una escritura está pendiente;
- evitá que doble click produzca dos comandos;
- no apliques la respuesta como clasificación optimista;
- después de éxito o replay, releé mapa e historial;
- conservá la entrada del formulario ante conflicto para que Joa pueda revisar;
- ante conflicto de revisión, refrescá la vista sólo después de informar y nunca
  reenvíes automáticamente con una revisión nueva;
- un retry exacto por fallo de transporte puede reutilizar el mismo body sólo si
  el usuario confirma que no lo cambió; cualquier edición genera IDs nuevos.

### Unir fuentes

Permití seleccionar al menos dos fuentes. Como ayuda puramente pública, una
fuente es candidata estructural sólo si `automaticSourceIds.length === 1` y
`structuralDecisionIds.length === 0`; el servidor sigue siendo la autoridad y
`unsupported_target` debe manejarse como error cerrado. No unas automáticamente
por nombre, dominio o similitud.

### Separar una fuente

Ofrecé partición manual sólo para una fuente candidata estructural con al menos
dos flujos. En D6 v1 usá anclas `flow`: cada flujo actual debe aparecer una sola
vez, todos deben quedar cubiertos, cada grupo debe ser no vacío y deben existir
al menos dos grupos. No decidas grupos automáticamente.

### Proteger

Permití proteger, según el contexto visible, una fuente, flujo, mensaje reciente,
remitente o etiqueta. No existe desprotección. No confundas protección con Spam,
confianza o recomendación.

## ESTADOS OBLIGATORIOS

La interfaz y sus pruebas deben cubrir:

- carga inicial coordinada;
- mapa disponible y mapa vacío;
- mapa parcial;
- historial vacío;
- `map_unavailable` y `account_unavailable`;
- fuente inexistente;
- error local de transporte o respuesta inválida;
- escritura pendiente, aplicada y replay exacto;
- `map_revision_conflict`, `policy_revision_conflict`,
  `command_id_conflict`, `policy_conflict` e `invalid_transition`;
- `target_not_found` y `unsupported_target`;
- undo pendiente, aplicado, replay y conflicto;
- los seis estados de sincronización;
- los cuatro estados de binding que requieren revisión.

Cada error conserva un camino explícito y seguro de reintento o regreso. Nunca
dejes la pantalla en carga indefinida.

## DISEÑO, RESPONSIVE Y ACCESIBILIDAD

Evolucioná la identidad visual local existente —papel cálido, verde, jerarquía
editorial e iconos SVG propios— sin cargar fuentes, imágenes o assets remotos.
La interfaz debe verse deliberada, no como un panel genérico.

En escritorio y a 390 px:

- evitá overflow horizontal;
- apilá comparaciones automático/efectivo sin esconder una de las capas;
- no uses tablas que obliguen a desplazamiento lateral para flujos o historial;
- cortá visualmente IDs y textos largos sin perder acceso al valor permitido;
- mantené controles táctiles de al menos 44 px;
- no escondas protección, contradicción, parcialidad o revisión obligatoria;
- no dependas sólo del color;
- respetá `prefers-reduced-motion`.

Accesibilidad mínima:

- un `h1` único y jerarquía semántica por ruta;
- foco visible;
- controles con nombre accesible y labels asociados;
- carga y éxito con `role="status"` o región viva apropiada;
- errores y conflictos con `role="alert"`;
- navegación móvil con estado accesible, cierre por Escape y retorno de foco;
- formularios y operaciones estructurales utilizables por teclado;
- texto explícito para automático, efectivo y decidido por Joa.

## SEGURIDAD Y PRIVACIDAD

D6 trabaja sólo con el fixture canónico `.example` servido por C5.

Queda prohibido:

- Gmail, OAuth, navegador de autorización, credenciales, tokens o datos reales;
- cualquier request fuera del origen local y las nueve rutas permitidas;
- guardar respuestas en `localStorage`, `sessionStorage`, IndexedDB o archivos;
- telemetría, analytics, logs de metadatos o reportes externos;
- `dangerouslySetInnerHTML` o renderizado de contenido de correo;
- links externos, imágenes remotas, CDN, webfonts o scripts remotos;
- cuerpos, HTML, snippets, MIME, adjuntos, destinatarios o headers genéricos;
- planes, recomendaciones, Archivo, Papelera, desuscripción o ejecución;
- cálculo de espacio recuperable;
- nuevas dependencias;
- modificar backend, contratos, pruebas Python, scripts o configuración.

No toques `New folder/grafo.txt`, incluso si fuera visible desde otro worktree.

## PRUEBAS OBLIGATORIAS

Usá fixtures TypeScript derivados de las respuestas HTTP C5 y únicamente
direcciones `.example`. No importes modelos Python.

Como mínimo probá:

1. las nueve rutas y el transporte same-origin relativo;
2. `credentials: "omit"`, ausencia de auth/cookies y JSON sólo en POST;
3. modo sintético y capacidades falsas visibles;
4. panorama, fuentes, filtros y detalle;
5. diferencias automático/efectivo y evidencia separada;
6. protección, revisión obligatoria y exclusión dura;
7. carga, vacío, parcialidad y errores cerrados;
8. los seis estados de sincronización;
9. bindings que requieren revisión;
10. serialización de los siete comandos sin campos extra;
11. undo únicamente cuando `undoable` es verdadero;
12. doble envío bloqueado;
13. conflicto sin retry ciego y con formulario conservado;
14. replay exacto y recarga posterior;
15. ausencia de Estudio de Limpieza, ejecución, conexión y controles de sync;
16. navegación y menú móvil semánticos;
17. ausencia de `/api/v1`, URLs externas, recursos remotos y datos no `.example`
    en la superficie D6.

No rebajes pruebas vigentes para adaptar el resultado. Podés reemplazar pruebas
v1 del frontend cuando el comportamiento activo que verificaban fue retirado por
este contrato; documentá esa sustitución en el handoff.

## VALIDACIÓN OBLIGATORIA

Ejecutá desde el worktree:

```powershell
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_safety.py tests\test_map_api.py
.\scripts\check.ps1
git diff --check
git status --short --untracked-files=all
git status --short --ignored --untracked-files=all
git diff -- frontend
git ls-files --others --exclude-standard -- frontend
```

La base previa a D6 tiene como evidencia 296 pruebas Python, Ruff aprobado, mypy
estricto sobre 24 archivos, ESLint, 4 pruebas Vitest y build Vite aprobado. Tus
conteos frontend deben aumentar de manera material; la batería global no puede
retroceder por la sustitución de las dos pruebas v1 de recorrido.

No uses red para reconstruir entornos. Reutilizá temporalmente `.venv`, pnpm,
Node y dependencias ya instaladas en MAIN o provistas por Codex sin modificar
scripts/configuración. Si creás enlaces locales o artefactos para validar,
retirá únicamente los tuyos al terminar; no uses `git clean`.

Realizá además, si las herramientas funcionan:

1. un recorrido HTTP local desde `http://127.0.0.1:8765`;
2. revisión visual en escritorio;
3. revisión visual a 390 px;
4. captura de evidencia o descripción exacta de cada pantalla y defecto.

La revisión del especialista no reemplaza la revisión visual final de MAIN y
Joa. Si la herramienta visual no funciona, informalo como pendiente; no afirmes
que revisaste la interfaz.

Retirá antes del handoff `frontend/dist`, cachés, bases, logs, temporales y
enlaces únicamente si fueron creados por vos durante esta tarea. No borres un
artefacto ignorado preexistente sin verificar su origen, ni `node_modules` o
`.venv` ajenos.

## PUNTOS DE DETENCIÓN

Detenete y devolvé el bloqueo si:

- ruta, rama, SHA o estado inicial no coinciden;
- necesitás tocar un archivo fuera de `frontend/src/**` o `frontend/index.html`;
- necesitás modificar contrato, backend, API, script, configuración o dependencia;
- una respuesta C5 no permite representar un estado obligatorio sin inferencia;
- una operación exige enviar `accountKey`, selector interno o dato no publicado;
- no podés implementar una partición completa sólo con anclas visibles;
- necesitás inventar elegibilidad, precedencia o clasificación en TypeScript;
- aparece una ruta de conexión, sincronización o acción no autorizada;
- necesitás Gmail, OAuth, red externa, credenciales o datos reales;
- una prueba requiere un servicio externo;
- la batería previa falla por una regresión real.

No cambies silenciosamente el contrato para superar un stop point.

## GIT

No hagas commit, push, fetch, pull, merge, rebase, reset, clean, publicación ni
integración en `main`. No crees ramas, worktrees o remotos adicionales. Dejá
únicamente el diff frontend auditable en tu worktree.

## DONE WHEN

D6 queda entregada para auditoría únicamente cuando:

1. la superficie activa consume exclusivamente las nueve rutas `/api/v2`;
2. mapa, fuente, flujo, evidencia, protección y decisiones preservan el contrato;
3. las siete correcciones y undo funcionan con CAS e idempotencia desde el cliente;
4. conflictos y estados parciales fallan de manera segura y comprensible;
5. no existen controles ni mensajes que adelanten procesos posteriores;
6. escritorio y 390 px son utilizables y accesibles;
7. pruebas, lint, build y batería global aprueban;
8. sólo existen cambios dentro de los dos alcances autorizados;
9. no quedan builds, cachés, bases, secretos ni datos privados;
10. no se ejecutó ninguna operación Git o externa prohibida.

## HANDOFF A MAIN

Entregá un único informe autosuficiente con:

1. `QUÉ HACE`.
2. `POR QUÉ EXISTE`.
3. ruta, rama, base, HEAD y estado inicial/final.
4. archivos creados, modificados o eliminados.
5. arquitectura frontend, rutas y tipos `/api/v2`.
6. estados, correcciones, conflictos y decisiones de UX implementadas.
7. pruebas y validaciones exactas con conteos.
8. recorrido HTTP y revisión visual realmente ejecutados, diferenciando pendientes.
9. diff, no rastreados, ignorados y búsqueda de secretos/artefactos.
10. riesgos, limitaciones y estados que siguen bloqueados.
11. confirmación explícita de ausencia de Gmail, OAuth, red externa,
    credenciales, datos reales, `/api/v1` activo, Estudio de Limpieza, acciones,
    nuevas dependencias y operaciones Git.

No declares D6 integrada ni Mapa Total aceptado. MAIN debe auditarla,
revalidarla y mostrarla a Joa.

## QUÉ HACE, AL CIERRE

Deja una candidata D6 completa, sintética, responsive y auditable en su worktree.

## POR QUÉ EXISTE, AL CIERRE

Permite que MAIN y Joa evalúen la experiencia de Mapa Total sin confundir una
interfaz de demostración con acceso a Gmail ni adelantar la limpieza.
