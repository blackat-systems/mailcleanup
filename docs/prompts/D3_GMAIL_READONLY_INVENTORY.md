# Prompt D3 — Gmail Read-only Inventory

## Rol

Sos la dependencia especialista D3 `gmail-readonly-inventory` de MailCleanup.
No sos MAIN. Implementá únicamente el inventario Gmail de sólo metadatos con
puertos y datos sintéticos. Tu entrega será evidencia para una auditoría
independiente de MAIN.

## Ubicación y base obligatorias

- Worktree: el checkout aislado creado por Codex para este task.
- Rama esperada: una rama `codex/*` exclusiva del task.
- Commit base: el SHA exacto indicado por MAIN junto con este prompt.
- Estado inicial esperado: limpio.

Antes de editar ejecutá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short
git worktree list --porcelain
```

Si el SHA, la rama, la limpieza o el alcance no coinciden, detenete. No uses
reset, rebase, merge, limpieza destructiva ni cambios para ocultar la diferencia.

## Lectura obligatoria

Leé completamente:

1. `AGENTS.md`.
2. `docs/CONTRATO_MVP.md`.
3. `docs/contracts/SECURITY_PRIVACY_V1.md`.
4. `docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`.
5. `docs/contracts/GMAIL_SESSION_V1.md`.
6. `docs/contracts/INDEX_PERSISTENCE_V1.md`.
7. La sección D3 de `docs/PLAN_DEPENDENCIAS.md`.
8. `docs/DECISIONES.md`.
9. `src/mailmap/gmail_readonly_policy.py`.
10. `src/mailmap/index_model.py`.
11. `src/mailmap/repository.py`.
12. `src/mailmap/session_model.py`.
13. `tests/test_base_segura_safety.py`.
14. `scripts/check.ps1`.

Para D3 prevalecen `GMAIL_READONLY_INVENTORY_V1.md` y
`SECURITY_PRIVACY_V1.md`. No los modifiques para acomodar la implementación.

## Objetivo

Construir la orquestación comprobable de un inventario Gmail de sólo metadatos:

- listado paginado de IDs;
- detalle `METADATA` con encabezados exactos;
- normalización a `IndexedMessageRecord`;
- persistencia atómica de página y checkpoint mediante D1;
- escaneo completo y parcial;
- reanudación, cancelación y errores controlados;
- 404 de historial convertido en `requires_full_resync`;
- Spam separado;
- exclusión previa a persistencia de Enviados, Borradores y Papelera.

Todo se implementa con un transporte inyectable y dobles sintéticos. No existe
un adaptador productivo ni se abre una cuenta real.

## Archivos permitidos

Podés crear o modificar exclusivamente:

- `src/mailmap/gmail_inventory_model.py`;
- `src/mailmap/gmail_inventory.py`;
- `tests/test_gmail_readonly_inventory.py`;
- `tests/test_base_segura_safety.py`, sólo para ampliar las barreras de D3 sin
  debilitar las vigentes.

No modifiques `repository.py`, modelos D1/D2, API, servicio, frontend, fixtures,
scripts, configuración, dependencias ni documentación. Si encontrás un defecto
en esas áreas, documentalo y devolvelo a MAIN.

## Diseño obligatorio

### Frontera de transporte

Definí un protocolo cerrado e inyectable. Sus operaciones deben corresponder
exactamente a perfil, etiquetas, lista de mensajes, detalle `METADATA` e
historial. El dominio no recibe respuestas libres ni clientes HTTP.

No importes ni uses `socket`, `urllib.request`, `http.client`, `requests`,
`httpx`, SDKs Google, `webbrowser`, OAuth ni almacenamiento de credenciales.
No agregues dependencias. Las pruebas deben fallar si se intenta red o navegador.

### Datos cerrados

Usá dataclasses inmutables con `slots=True`, enums cerrados y códigos de error
controlados. Rechazá campos arbitrarios, tipos ambiguos, IDs vacíos, fechas sin
zona, tamaños negativos y valores fuera de los límites fijados.

Nunca conserves ni expongas cuerpo, HTML, `snippet`, `raw`, MIME, adjuntos,
destinatarios, encabezados no aprobados, secretos OAuth ni payload remoto crudo.
Tampoco produzcas inferencias de fuente, flujo, rubro, intención o protección.

Un campo extra en una respuesta sintética se descarta en la frontera y una
cabecera no autorizada nunca ingresa al modelo normalizado.

### Solicitudes

- Scope exacto `gmail.metadata`, sin duplicar el literal fuera de
  `session_model.py`.
- Sólo operaciones de lectura y origen exacto de
  `gmail_readonly_policy.py`.
- `messages.list`: hasta 500, sin `q`.
- `messages.get`: `format=METADATA` y allowlist exacta de encabezados.
- No aceptar opciones genéricas de `format`, `fields`, URL, método o scope que
  permitan ampliar la lectura desde un consumidor.

### Escaneo completo

El recorrido normal excluye Spam y Papelera. El recorrido Spam usa la etiqueta
`SPAM` en una rama separada. Después de obtener etiquetas del detalle, descartá
antes de persistir cualquier mensaje con `SENT`, `DRAFT` o `TRASH`; esa regla
prevalece sobre toda otra etiqueta.

Guardá una página validada y su checkpoint mediante una sola llamada
`save_index_page`. No escribas registros de a uno y luego avances el checkpoint.
Un reintento debe ser idempotente.

### Escaneo parcial

Partí del `history_id` consolidado. Tratá altas, cambios de etiquetas y bajas sin
afectar otras cuentas. Si el historial venció, no continúes con resultados
parciales: persistí el estado `requires_full_resync` conforme al contrato.

### Reintentos, cancelación y observabilidad

- máximo cinco intentos;
- sólo 429/500/502/503/504 y códigos de cuota cerrados;
- backoff exponencial truncado, jitter y reloj/sleeper inyectables;
- tope de 32 segundos;
- cancelación antes de cada llamada y antes de persistir;
- nada de `sleep` real en pruebas;
- no logs de contenido, IDs, direcciones, asuntos, encabezados o URLs.

## Casos mínimos de prueba

1. modelos cerrados, inmutables y validados;
2. página única, varias páginas, página vacía y token final;
3. límite de página y ausencia de `q`;
4. detalle sólo `METADATA` con encabezados exactos;
5. descarte de cuerpo, snippet, MIME, adjuntos y encabezados extra;
6. límites por encabezado y total;
7. fechas UTC, etiquetas canónicas y tamaño;
8. Spam separado y precedencia de `SENT`, `DRAFT` y `TRASH`;
9. checkpoint atómico y rollback ante fallo;
10. interrupción y reanudación sin duplicados;
11. cancelación antes de persistir;
12. sync parcial: alta, cambio de etiquetas y baja;
13. historial 404 a `requires_full_resync`;
14. aislamiento entre cuentas;
15. reintentos acotados y sin retry de errores permanentes;
16. redacción de `repr` y errores;
17. bloqueo efectivo de socket, `urlopen` y navegador;
18. `oauthAvailable: false`, `canExecute: false` y ausencia de rutas Gmail.

Usá exclusivamente dominios reservados `.example`, IDs sintéticos y bases
temporales. No uses secretos con forma real ni copies respuestas de Gmail.

## Validación obligatoria

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gmail_readonly_inventory.py
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_safety.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
git status --short
```

Si el runtime Node de Codex no está en `PATH`, incorporalo sólo a la terminal.
No modifiques scripts ni configuración por esa razón.

## Prohibiciones

- No abrir OAuth ni navegador.
- No conectar Gmail ni ejecutar red externa.
- No solicitar ni usar credenciales o datos reales.
- No persistir un índice real.
- No implementar cliente productivo, API pública, UI o clasificación.
- No cambiar scopes ni añadir escritura.
- No tocar Estudio de Limpieza o Limpieza Controlada.
- No hacer commit, push, merge, rebase, publicación ni despliegue.
- No crear otros worktrees o tareas.

## Stop points

Detenete y devolvé el bloqueo si el contrato exige un campo no autorizado; D1
no puede representar el resultado sin cambiar su contrato; necesitás red, SDK,
dependencia, API o credenciales; una respuesta real sería necesaria; aparece
una decisión material de privacidad; o hay trabajo ajeno fuera del alcance.

## Handoff

Entregá objetivo; ruta, rama, base, HEAD y estado; cambios y archivos exactos;
contratos; barreras negativas; comandos y resultados; hallazgos, riesgos y
pendientes; diff y no rastreados; confirmación de ausencia de red, OAuth, Gmail,
credenciales, datos reales y operaciones Git; y `NEXT: esperar auditoría de MAIN`.

## Done when

El inventario completo y parcial funciona contra dobles, persiste de forma
atómica, respeta límites y exclusiones, pasa todas las validaciones y deja sólo
los cuatro archivos permitidos como cambios sin commit. Esto no habilita Gmail
real.
