# PROJECT AGENTS — MAILCLEANUP

# 0. INICIALIZACIÓN DE LA PLANTILLA

Esta sección conserva el contrato de inicialización del gobierno específico del
proyecto. MAIN inicializó este archivo el 18 de agosto de 2026 después de
inspeccionar Git, código, pruebas, configuración y documentación vigente.

Al inicializar o revisar estas reglas, MAIN debe:

1. deducir la información específica desde fuentes verificables del repositorio;
2. mantener el archivo alineado con el alcance, la arquitectura y el estado real;
3. eliminar ejemplos genéricos que no describan MailCleanup;
4. no inventar datos para completar una sección;
5. registrar como `PENDIENTE`, con su razón, aquello que requiera una decisión
   material de Joa;
6. consultar a Joa sólo si falta una decisión sobre alcance, arquitectura,
   seguridad, privacidad, costos o comportamiento esperado.

No deben permanecer campos de plantilla sin resolver. Este archivo contiene
únicamente reglas específicas de MailCleanup y complementa las reglas globales
de Codex sin duplicarlas.

Antes de cambios importantes, leer este archivo y las fuentes de verdad que
correspondan a la tarea.

---

# 1. PROYECTO

## Nombre

MailCleanup. El repositorio se llama `mailcleanup`, la distribución Python
mantiene por ahora el nombre técnico `limpiar-mails` y el paquete activo es
`mailmap`.

## Propósito

Construir una aplicación local para Windows que ayude a una persona a comprender
qué recibe en Gmail mediante un mapa explicable de fuentes y flujos antes de
preparar cualquier limpieza. Debe separar identidad, rubro, intención,
suscripción, protección, confianza y evidencia, y preservar por defecto aquello
que sea importante, ambiguo o contradictorio.

## Estado actual

`DEVELOPMENT` — Joa aceptó Base Segura el 18 de agosto de 2026. MAIN completó
el 27 de agosto de 2026 el recorrido visual instrumental de Panorama, Fuentes,
detalle, Estudio y Estado tanto en escritorio como a 390 px, sin defectos
bloqueantes.

La preparación sintética de Mapa Total mediante D2 fue auditada e integrada en
MAIN. D3 `gmail-readonly-inventory` fue auditada e integrada después de ampliar
D1 para aplicar altas, actualizaciones, bajas y checkpoint en una transacción e
iniciar un escaneo completo reemplazando de forma controlada el índice anterior.
D4 `real-classification-domain` fue auditada e integrada en el árbol de trabajo
de MAIN con correcciones conservadoras de agrupación, baja, confianza y sus
regresiones; quedó consolidada en `0fe5111`. MAIN redactó
`LOCAL_POLICY_MEMORY_V1.md`, Joa aprobó ese contrato y autorizó a MAIN a agregar
los descriptores públicos de identidad D4 que requiere. Esa columna vertebral
quedó consolidada en `9f55b93` sin cambiar agrupaciones, IDs, taxonomías ni
evidencias. Joa autorizó la creación del prompt autosuficiente y un único
worktree D5. MAIN consolidó la base `663d8a9`, creó D5 en
`C:\Users\Joaquin\.codex\worktrees\9623\mailcleanup`, rama
`codex/local-policy-memory`, y auditó su entrega. La integración en el árbol de
MAIN quedó aprobada con una corrección conservadora: los fragmentos de un flujo
particionado conservan la confianza automática original de D4. D5 queda
consolidada por el commit que contiene este estado. No están autorizados abrir
OAuth, conectar Gmail, solicitar credenciales ni usar datos reales. Existen
nueve worktrees: MAIN y las fuentes D1-D8 conservadas como evidencia.
D6
permanece en
`C:\Users\Joaquin\.codex\worktrees\bbbc\mailcleanup`, rama
`codex/mapa-total-ui`. `origin` apunta al repositorio privado
`https://github.com/blackat-systems/mailcleanup.git`. Sólo MAIN puede publicar
`main` después de verificar destino, alcance y autorización; los worktrees
especialistas no publican ramas ni usan el remoto para ampliar su alcance.
La primera publicación de `main` quedó verificada desde `6310c76`.

MAIN definió `MAPA_TOTAL_API_V1.md` e implementó C5: fotografía SQLite coherente,
composición D4+D5, fixture canónico, puerta sintética cerrada y API local
`/api/v2`. La auditoría y la batería global están verdes y C5 quedó consolidada
en `67b00c7`. MAIN consolidó el prompt D6 en `75764c9`, creó un único worktree
`mapa-total-ui` desde ese SHA y le entregó el alcance completo. El 28 de agosto
de 2026 MAIN auditó e integró su entrega en el árbol de trabajo con siete
correcciones de seguridad, contrato, privacidad y accesibilidad. La batería
global y el recorrido visual inicial en escritorio y 390 px están verdes. A
pedido de Joa, MAIN aplicó después una segunda pasada de jerarquía visual:
navegación primaria reducida, filtros avanzados y diagnósticos plegables, y
detalle progresivo sin retirar información ni alertas. Esa pasada tiene batería
global y HTTP local verdes. Joa aceptó explícitamente D6 el 28 de agosto de 2026;
quedó consolidada y publicada en `963af89`. Joa autorizó después comenzar
Estudio de Limpieza y preparar C6. MAIN auditó el contrato
`CLEANUP_PLAN_V1.md`; Joa lo aceptó el 29 de agosto de 2026 y autorizó su commit.
Quedó consolidado en `5c913f2`. Joa autorizó después a MAIN a preparar el prompt
autosuficiente D7. El prompt quedó auditado y consolidado en `e92a77a`. Joa
autorizó después crear e iniciar el único worktree D7, ubicado en
`C:\Users\Joaquin\.codex\worktrees\4d09\mailcleanup`, rama
`codex/real-plan-engine`, desde esa base exacta. MAIN verificó ruta, rama, HEAD y
limpieza antes de enviar `docs/prompts/D7_REAL_PLAN_ENGINE.md`. El especialista
entregó D7 y MAIN la auditó e integró en el árbol de trabajo con correcciones de
invariantes persistidas, coherencia de muestras y paginación SQL acotada. La
batería global quedó verde con 391 pruebas Python y 98 pruebas frontend. Joa
autorizó después su commit y publicación; D7 quedó consolidada y publicada en
`c8c7b32`. Su alcance permanece sintético y sin efectos. Joa autorizó luego a
MAIN a preparar, consolidar y despachar un único worktree D8 `estudio-ui`.
`docs/prompts/D8_ESTUDIO_UI.md` fija una frontera exclusivamente frontend y
sintética. MAIN consolidó el prompt en `a1cf0ff`, creó y verificó D8 en
`C:\Users\Joaquin\.codex\worktrees\83bb\mailcleanup`, rama
`codex/estudio-ui`, y le entregó el prompt completo en la tarea
`01a04d55-2cae-7051-a2d9-2534c15dd793`. El especialista entregó D8 y MAIN
auditó e integró únicamente sus 22 cambios autorizados bajo
`frontend/src/**`. Joa aceptó D8 y Estudio de Limpieza exclusivamente en modo
sintético. La batería global, el recorrido HTTP local y la revisión visual en
escritorio y 390 px quedaron verdes. D8 quedó consolidada en `3ff29bd`; no
habilita capacidades externas ni acciones.

El 31 de agosto de 2026 Joa autorizó a MAIN a preparar C7 exclusivamente como
contrato documental de Limpieza Controlada. MAIN redactó
`docs/contracts/CONTROLLED_EXECUTION_V1.md`, Joa lo aceptó y autorizó consolidar
únicamente su documentación. C7 quedó consolidado y publicado en `49e2e58`.
El contrato no habilita D9, `gmail.modify`, OAuth, Gmail real, credenciales,
datos privados ni modificaciones. Joa autorizó después a MAIN a preparar dos
extensiones documentales: C3-A `GMAIL_ACTION_SESSION_V1.md` y C4-P
`PRIVATE_LOCAL_VAULT_V1.md`. Joa aceptó ambas con compatibilidad escalonada y
autorizó consolidarlas y publicarlas. Quedan consolidadas por el commit que
contiene este estado y siguen sin constituir controles implementados. No se creó
D9 ni un worktree nuevo.

## Objetivo actual

Conservar verdes Estudio de Limpieza y los contratos documentales C7, C3-A y
C4-P aceptados. Esperar otra autorización antes de preparar un spike técnico,
implementar esos contratos o crear un prompt/worktree D9. Gmail, OAuth,
`gmail.modify`, credenciales, datos privados y acciones reales permanecen
bloqueados.

---

# 2. PRIORIDAD

Conservar verdes y auditables D3 y D4 sintéticas consolidadas. Todo cambio debe
respetar el permiso mínimo, la allowlist de lectura,
la atomicidad del índice, la clasificación conservadora, la separación de
secretos y la barrera de no escritura sobre Gmail o mensajes.

Mapa Total y Estudio de Limpieza están aceptados exclusivamente con alcance
sintético. C6, D7 y D8 están consolidadas. C7 existe como contrato documental
aceptado. Limpieza Controlada, D9 y toda capacidad
real permanecen detrás de autorizaciones y puertas independientes. Las ideas
futuras se registran sin incorporarlas al alcance activo.

---

# 3. FUENTES DE VERDAD

Para determinar alcance y autorización:

1. `docs/CONTRATO_MVP.md` — prevalece ante diferencias.
2. `docs/AUDITORIA_PRE_DESARROLLO.md`.
3. `docs/ESPECIFICACION_FUNCIONAL.md` — visión futura, no autorización.

Para determinar implementación y estado actual:

1. código en `src/mailmap` y `frontend/src`;
2. pruebas en `tests` y `frontend/src`;
3. `docs/contracts/API_V1.md`;
4. `docs/contracts/MAPA_TOTAL_API_V1.md` para C5 y D6;
5. `docs/contracts/CLEANUP_PLAN_V1.md` para C6 y D7 integrada;
6. `docs/contracts/CONTROLLED_EXECUTION_V1.md` para C7 aceptado como contrato
   documental, sin capacidad operativa;
7. `docs/contracts/GMAIL_ACTION_SESSION_V1.md` para C3-A aceptada sólo
   documentalmente;
8. `docs/contracts/PRIVATE_LOCAL_VAULT_V1.md` para C4-P aceptada sólo
   documentalmente;
9. `docs/adr/0001-arquitectura-base-segura.md`;
10. `pyproject.toml`, `frontend/package.json`, lockfile y scripts;
11. `docs/ESTADO_BASE_SEGURA.md`;
12. `docs/DECISIONES.md`.

Para coordinación de MAIN y dependencias:

1. `docs/PROMPT_MAESTRO_MAIN.md`;
2. `docs/PLAN_DEPENDENCIAS.md`;
3. `docs/WORKTREE_REGISTRY.md`;
4. `docs/prompts/PLANTILLA_DEPENDENCIA.md`.
5. `docs/prompts/D7_REAL_PLAN_ENGINE.md` para la delegación D7 entregada;
6. `docs/prompts/D8_ESTUDIO_UI.md` para la delegación D8 entregada e integrada.

Para D2 prevalece `docs/contracts/GMAIL_SESSION_V1.md`. Para D3 prevalecen
`docs/contracts/SECURITY_PRIVACY_V1.md` y
`docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`. Para D4 prevalece
`docs/contracts/CLASSIFICATION_DOMAIN_V1.md`. Para D5 prevalece el contrato
aprobado `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`. Su integración sintética no
habilita Gmail, OAuth ni datos reales. Para C5 y D6 prevalece
`docs/contracts/MAPA_TOTAL_API_V1.md`; su API `/api/v2` es exclusivamente local
y sintética. Para C6 prevalece el contrato aceptado
`docs/contracts/CLEANUP_PLAN_V1.md`. Es el contrato de D7, pero no autoriza
por sí solo datos reales o ejecución. El prompt D7 traduce ese contrato a una
frontera especialista y D7 quedó consolidada. D8 fue preparada mediante
`docs/prompts/D8_ESTUDIO_UI.md`, entregada, auditada, integrada y aceptada
exclusivamente como frontend sintético. Esta aceptación no se extiende a Gmail,
OAuth, datos reales, ejecución ni Limpieza Controlada.
`docs/contracts/CONTROLLED_EXECUTION_V1.md` es C7 aceptado sólo documentalmente: no
prevalece sobre la sesión de sólo metadatos ni habilita una excepción operativa
a `SECURITY_PRIVACY_V1.md`.
`docs/contracts/GMAIL_ACTION_SESSION_V1.md` y
`docs/contracts/PRIVATE_LOCAL_VAULT_V1.md` son C3-A y C4-P aceptadas con alcance
exclusivamente documental. Hasta que exista implementación auditada y nuevas
autorizaciones, no prevalecen como capacidades ni desbloquean D9.

Si código, pruebas y documentación se contradicen, investigar la divergencia.
No ampliar alcance apoyándose en una implementación accidental ni cambiar un
contrato sin evidencia y decisión de MAIN.

---

# 4. STACK

## Lenguajes y runtime

- Python 3.11 o posterior.
- TypeScript 6 en modo estricto.
- PowerShell para preparación, ejecución y verificación.
- Node.js con pnpm 11 para el frontend.

## Backend

- FastAPI, Pydantic y Uvicorn.
- SQLite mediante la biblioteca estándar de Python.
- `tzdata` y `zoneinfo` para `America/Argentina/Cordoba`.

## Frontend

- React 19, TypeScript 6 y Vite 8.
- Navegación local por hash. D6 reemplaza el consumo frontend activo de
  `/api/v1` por la API sintética `/api/v2`; el backend v1 permanece compatible.

## Persistencia

- SQLite local con migraciones versionadas.
- Base generada en `data/mailmap-base-segura.db`.
- `data/` es regenerable e ignorado por Git.

## Calidad

- pytest, Ruff y mypy estricto.
- Vitest, Testing Library, jsdom y ESLint.
- Build TypeScript y Vite.

Windows es la plataforma objetivo inicial. La compatibilidad escalonada aceptada
mantiene Windows 10/11 como objetivo de la experiencia sintética y exige
Windows 11 build 22000 para datos y acciones reales mientras no exista una
alternativa local equivalente aceptada. Esto es una política, no evidencia de
que Windows 10 ya haya sido probado. No reemplazar tecnologías centrales ni
agregar dependencias importantes sin necesidad demostrada y, cuando afecte
arquitectura o seguridad, aprobación de Joa.

---

# 5. ARQUITECTURA

MailCleanup es una aplicación web local. FastAPI compone dominio, persistencia y
API y sirve el build estático de React. Toda la aplicación se enlaza a loopback.
Base Segura usa sólo fixtures sintéticos y no contiene clientes de Gmail, OAuth
ni red externa.

```text
fixtures sintéticos
        ↓
clasificación determinista y explicable
        ↓
repositorio SQLite con migraciones
        ↓
servicio de fuentes, flujos, protecciones y planes simulados
        ↓
API local v1
        ↓
interfaz React/TypeScript
```

El candidato C5 agrega una rama backend separada, sin sustituir la anterior:

```text
índice sintético D1 + políticas D5
        ↓ fotografía SQLite única
clasificación D4 + aplicación conservadora D5
        ↓
proyección explicable de Mapa Total
        ↓
API local v2 cerrada
```

## Componentes

- `model.py`, `fixtures.py`, `classifier.py`: modelo versionado, dataset canónico
  y reglas de identidad, intención, confianza y protección.
- `repository.py`: migraciones, siembra sintética y persistencia de mensajes y
  planes simulados; no almacena credenciales.
- `service.py`, `api.py`, `main.py`: agregación, planes incapaces de ejecutarse,
  API y servidor fijado a `127.0.0.1:8765`.
- `map_model.py`, `map_composition.py`, `map_fixtures.py`,
  `map_synthetic_gate.py` y `map_api.py`: contrato ejecutable C5, composición,
  fixture `.example`, puerta sintética y API local v2; no conectan Gmail.
- `cleanup_plan_model.py`, `cleanup_plan_domain.py` y `cleanup_plan_api.py`:
  planes sintéticos congelados, migración SQLite v5 y nueve rutas cerradas
  `/api/v3/study`; no ejecutan acciones.
- `frontend/src`: presentación, navegación y consumo tipado de `/api/v2` para
  Mapa Total y `/api/v3/study` para Estudio de Limpieza; no duplica reglas de
  clasificación, planificación o seguridad y no ofrece ejecución.
- `tests`, pruebas frontend y `scripts/check.ps1`: invariantes, contrato HTTP,
  barrera de seguridad, lint, tipos, pruebas y build.

Mantener separadas evidencia, inferencia, decisión del usuario, plan y futura
ejecución. No mover reglas entre capas como efecto secundario de una tarea local.

---

# 6. ESTRUCTURA DEL REPOSITORIO

```text
mailcleanup/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/mailmap/
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── src/
├── scripts/
├── tests/
└── docs/
    ├── adr/
    ├── contracts/
    └── prompts/
```

- `src/mailmap`: backend, dominio y persistencia de Base Segura.
- `frontend/src`: interfaz y tipos consumidores de la API.
- `tests`: pruebas Python de dominio, API y seguridad.
- `scripts`: recorrido oficial de preparación, ejecución y batería global.
- `docs`: contratos, arquitectura, decisiones, estado y coordinación.
- `data`: estado SQLite local generado; puede no existir y no se versiona.

El prototipo `src/gmail_cleaner` sólo existe en el historial Git. No
reintroducirlo, instalarlo ni usarlo como atajo.

---

# 7. COMANDOS OFICIALES

Ejecutar desde la raíz del repositorio en PowerShell.

## Instalar y construir

```powershell
.\scripts\setup.ps1
```

## Ejecutar

```powershell
.\scripts\run.ps1
```

Sirve la aplicación compilada en `http://127.0.0.1:8765`.

## Batería global

```powershell
.\scripts\check.ps1
```

Ejecuta pytest, Ruff, mypy, ESLint, Vitest y build; se detiene ante fallos.

## Comprobaciones específicas

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
pnpm --dir frontend lint
pnpm --dir frontend test
pnpm --dir frontend build
```

El build frontend ejecuta `tsc -b` antes de Vite. No hay un script independiente
de typecheck frontend. No declarar que un comando pasó si no fue ejecutado.

---

# 8. REGLAS DE IMPLEMENTACIÓN

- Implementar sólo el proceso autorizado.
- Mantener clasificación y precedencia en una fuente lógica del backend.
- Preservar API v1 o versionarla si MAIN aprueba un cambio incompatible.
- Añadir la prueba mínima que demuestre cada cambio funcional.
- Usar fixtures sintéticos con dominios reservados `.example`.
- Modificar SQLite mediante migraciones, no editando bases generadas.
- Mantener `canExecute: false` incondicional durante Base Segura y Estudio de
  Limpieza.
- Sincronizar documentación cuando cambien contratos, arquitectura o estado.
- Evitar refactors oportunistas, dependencias nuevas y cambios fuera de alcance.

---

# 9. MAIN

MAIN conserva visión, contrato MVP, arquitectura, modelo compartido, API,
fixtures, batería global, seguridad, estado y registro de worktrees.

Antes de dividir trabajo debe explicitar:

```text
TASKS
DEPENDENCIES
PARALLELIZABLE
BLOCKED
INTEGRATION ORDER
```

MAIN puede construir columna vertebral y cambios transversales, pero no absorber
por defecto cada módulo funcional. Antes de delegar necesita commit base limpio,
contrato estable, límites, validación y prompt autosuficiente.

MAIN revisa diff completo y archivos no rastreados, integra controladamente y
repite las pruebas relevantes. El informe especialista no sustituye su auditoría.

---

# 10. ESPECIALISTAS

Los worktrees fuente de D1 `real-index-persistence`, D2
`secure-gmail-session`, D3 `gmail-readonly-inventory`, D4
`real-classification-domain` y D5 `local-policy-memory` se conservan como
evidencia de entregas integradas. La fuente D6 `mapa-total-ui` también se
conserva: su entrega fue auditada, integrada, aceptada por Joa y consolidada por
el commit que contiene este estado. D7 `real-plan-engine` fue entregada, auditada
e integrada con correcciones en el árbol de MAIN; su worktree desde `e92a77a`
se conserva como evidencia. La integración quedó consolidada en `c8c7b32`; la
fuente especialista continúa sin commit. D8 `estudio-ui` fue entregada,
auditada, integrada y aceptada por Joa con alcance sintético. Su fuente se
conserva en `C:\Users\Joaquin\.codex\worktrees\83bb\mailcleanup`, rama
`codex/estudio-ui`, desde la base exacta `a1cf0ff`, sin commit especialista.

Cuando MAIN habilite una dependencia debe completar
`docs/prompts/PLANTILLA_DEPENDENCIA.md` con tarea, contexto, entradas, salida,
alcance, dependencias, prohibiciones, validación y cierre.

- Verificar ruta, rama, SHA base, `HEAD`, estado y worktrees antes de editar.
- Trabajar sobre una responsabilidad cohesiva.
- No cambiar contratos, arquitectura o alcance sin devolver la decisión a MAIN.
- No integrar en `main`.
- No hacer commit, push, merge, rebase ni publicar salvo autorización explícita
  de Joa transmitida por MAIN.
- Entregar handoff con cambios, pruebas, riesgos y estado Git.

---

# 11. DEPENDENCIAS

```text
Base Segura aceptada por Joa
        ↓
D1 integrada + D2 integrada + contratos de privacidad e inventario
        ↓
D3 con dobles sintéticos → auditoría MAIN → integración consolidada
        ↓
D4 + D5 + C5 + D6 sintéticas aceptadas
        ↓ autorización de Estudio recibida
C6 aceptada + prompt D7 consolidado en `e92a77a`
        ↓ autorización independiente recibida
D7 `real-plan-engine` INTEGRADA EN EL ÁRBOL DE MAIN
        ↓ commit y publicación autorizados por Joa
D7 CONSOLIDADA EN MAIN (`c8c7b32`)
        ↓ prompt consolidado en `a1cf0ff` + autorización recibida
D8 `estudio-ui` INTEGRADA Y ACEPTADA EN MODO SINTÉTICO
        ↓ C7 DOCUMENTAL ACEPTADO
        ↓ C3-A Sesión de Acción Gmail DOCUMENTAL ACEPTADA
          + C4-P Bóveda Privada Local DOCUMENTAL ACEPTADA
          + endurecimiento auditado de D2 real y su almacén de secretos
          + autorización para implementar e implementación auditada de esas puertas
          + autorización de Limpieza Controlada + `gmail.modify`
          + plan piloto
D9 y Limpieza Controlada continúan bloqueados
```

Las puertas de producto son secuenciales:

```text
Base Segura
    ↓ autorización independiente
Mapa Total
    ↓ autorización independiente
Estudio de Limpieza
    ↓ autorización independiente
Limpieza Controlada
```

Las dependencias propuestas de `docs/PLAN_DEPENDENCIAS.md` no son contratos ni
una orden automática de creación. No paralelizar consumidores de interfaces
inestables.

---

# 12. WORKTREES Y RAMAS

- La raíz sobre `main` es el worktree de MAIN.
- Sincronizar `docs/WORKTREE_REGISTRY.md` con `git worktree list`.
- No crear worktree sin base limpia, contrato, prompt y frontera estable.
- Usar aislamiento cuando reduzca conflicto; no para tareas mecánicas mínimas.
- Un especialista no integra su entrega.
- MAIN revisa alcance, contratos, secretos, datos privados y conflictos
  semánticos antes de integrar y luego repite la batería.

El único remoto autorizado es `origin`, repositorio privado
`https://github.com/blackat-systems/mailcleanup.git`. No afirmar que un commit
fue publicado sin comprobar `origin/main`. No publicar ramas especialistas,
datos locales, secretos ni archivos ajenos al alcance.

Para commits destinados a GitHub, usar en este repositorio la identidad privada
`noreply` provista por GitHub; no incorporar una dirección personal nueva al
historial.

---

# 13. ESTADO DURABLE

Usar las fuentes actuales; no crear duplicados genéricos:

- `docs/ESTADO_BASE_SEGURA.md`: estado, verificaciones, riesgos y pendientes.
- `docs/DECISIONES.md`: decisiones materiales y autoridad.
- `docs/adr/0001-arquitectura-base-segura.md`: arquitectura aceptada.
- `docs/WORKTREE_REGISTRY.md`: bases, worktrees y dependencias.
- `docs/contracts/API_V1.md`: interfaz compartida.

Actualizar sólo cuando cambie la realidad. No crear archivos paralelos de estado,
decisiones o arquitectura mientras estas fuentes cumplan su función.

---

# 14. HANDOFF DE ESPECIALISTA

Debe incluir objetivo, cambios, archivos, decisiones, contratos preservados,
validaciones exactas, riesgos, pendientes, dependencias, próximo paso y estado
Git. Para worktrees también: ruta, rama, base y `HEAD`.

La información necesaria para integrar debe quedar en código, Git, contratos o
documentación, no depender de otro chat.

---

# 15. TESTING Y VALIDACIÓN

- Dominio, clasificación o protección: pruebas Python afectadas.
- Repositorio o migraciones: base temporal nueva y revalidación.
- API: pruebas de contrato y rutas activas.
- Frontend: Vitest, ESLint y build.
- Seguridad: `tests/test_base_segura_safety.py`.
- Cambio transversal o integración: `scripts/check.ps1`.
- Interfaz o cierre de Base Segura: recorrido visual en escritorio y 390 px.
- Servidor o composición: HTTP real en loopback cuando corresponda.

Antes de cerrar, ejecutar `git diff --check`, revisar el diff completo y buscar
secretos, datos privados y artefactos generados. Si una prueba no puede
ejecutarse, registrar el fallo y el riesgo restante.

---

# 16. DEFINITION OF DONE

Una tarea de MailCleanup está terminada sólo si:

- respeta el proceso autorizado y el contrato MVP;
- mantiene separados evidencia, clasificación, protección, plan y ejecución;
- no introduce Gmail, OAuth, datos reales o ejecución fuera de su puerta;
- conserva loopback y `canExecute: false` durante Base Segura y Estudio de
  Limpieza;
- pasan las pruebas específicas y, cuando corresponde, la batería global;
- un cambio visual fue recorrido o queda expresamente pendiente;
- API, código y documentación coinciden;
- el diff no contiene secretos, bases, cachés ni dependencias descargadas;
- Git y el registro de worktrees reflejan el estado real.

Base Segura no queda aceptada porque compile. Joa ya otorgó la aceptación
explícita y MAIN completó después la revisión visual instrumental en escritorio
y 390 px. D6 repitió su recorrido visual inicial, recibió una pasada posterior
de jerarquía minimalista con batería global verde y fue aceptada explícitamente
por Joa el 28 de agosto de 2026.

D8 fue auditada por MAIN, integrada y aceptada por Joa exclusivamente como
experiencia sintética de Estudio de Limpieza. Esto no demuestra comportamiento
sobre una bandeja Gmail real ni habilita Limpieza Controlada.

---

# 17. SEGURIDAD Y PRIVACIDAD

- No conectar Gmail ni abrir OAuth hasta una autorización específica posterior;
  C6, D7 y D8 integrada y aceptada son sintéticas, y C7 es sólo documental.
- No solicitar ni almacenar `credentials.json`, `token.json`, contraseñas o
  tokens.
- No usar mensajes, nombres ni direcciones reales en fixtures, pruebas, logs,
  capturas o commits.
- No renderizar HTML ni cargar imágenes o recursos remotos de correos.
- No enviar datos de correo a IA externa ni otros servicios.
- Mantener la aplicación en loopback.
- No introducir clientes Gmail o de red productivos durante C6, D7 o D8.
- Aplicar `SECURITY_PRIVACY_V1.md`: origen, métodos, endpoints, encabezados,
  tamaños y reintentos se deniegan por defecto salvo allowlist expresa.
- No usar el índice SQLite vigente con datos reales: todavía no implementa el
  cifrado autenticado, la ACL, la retención y el borrado consciente definidos
  documentalmente por C4-P.
- Tratar C3-A y C4-P como contratos documentales aceptados, no implementados: la
  sesión efímera, el proyecto OAuth separado, SQLCipher, Windows Hello y un
  broker nativo todavía no existen en el producto.
- Antes de OAuth real, corregir y auditar también D2: autorización no
  incremental, DPoP para refresh persistido, known folder, DACL y rechazo de
  reparse points. C3-A/C4-P no corrigen ese código por existir como documentos.
- Compatibilidad escalonada aceptada: Windows 10/11 como objetivo para la
  experiencia sintética; Windows 11 build 22000 como mínimo inicial para datos
  y acciones reales. Windows 10 permanece sin capacidades reales hasta aceptar
  una alternativa equivalente a `UserConsentVerifierInterop`.
- Mantener entornos, bases, cachés y dependencias descargadas fuera de Git.
- No implementar eliminación definitiva ni vaciado de Papelera.
- No interpretar C7 documental como permiso para solicitar `gmail.modify`,
  crear D9 o cambiar `canExecute: false` en las APIs vigentes.
- Toda futura acción real debe revalidarse, ser idempotente, registrable,
  reversible cuando corresponda y aprobada.

No desactivar la barrera automática de Base Segura para hacer pasar otro cambio.

---

# 18. RESTRICCIONES ESPECÍFICAS

## Obligatorias

- Usar sólo Base Segura, Mapa Total, Estudio de Limpieza y Limpieza Controlada
  como nombres activos de procesos.
- Trabajar sólo con datos sintéticos hasta nueva autorización.
- Mantener Fuente y Flujo separados.
- Mantener Suscripciones y Spam como vistas de Fuentes.
- Proteger Enviados, Borradores, Papelera, estrella, importancia, seguridad,
  documentación, decisiones manuales y evidencia contradictoria.
- Tratar Archivo, Papelera y desuscripción como acciones independientes.
- No presentar tamaño seleccionado como espacio liberado.

## Áreas de cuidado

- clasificación, confianza, protección y precedencia;
- migraciones SQLite y planes;
- fechas civiles de Córdoba;
- compatibilidad API v1 y tipos frontend;
- rutas HTTP y dependencias con red;
- fixtures y ausencia de datos privados.

## Requieren aprobación explícita de Joa

- aceptar Base Segura y habilitar Mapa Total;
- conectar Gmail, abrir OAuth o usar credenciales y datos reales;
- solicitar permisos de lectura o modificación;
- habilitar Limpieza Controlada;
- cambiar materialmente C7 o autorizar por separado su implementación;
- modificar mensajes reales o enviar desuscripciones;
- cambiar arquitectura, plataforma o persistencia central;
- agregar dependencias importantes o servicios externos;
- cambiar de forma incompatible la API;
- crear o publicar un remoto, hacer push o desplegar;
- incorporar cuerpos, IA externa, varias cuentas, Outlook, filtros persistentes,
  Guardián en segundo plano, pagos o eliminación definitiva.

---

# 19. NO HACER

- No confundir visión futura con alcance aprobado.
- No reintroducir el prototipo Gmail retirado.
- No fusionar fuentes de confianza baja ni automatizar contradicciones.
- No trasladar reglas de seguridad al frontend.
- No inventar ejecución detrás de una vista previa simulada.
- No crear worktrees por una lista tentativa de módulos.
- No versionar resultados de pruebas o builds.
- No afirmar aceptación visual, conexión o publicación sin evidencia.
- No dejar decisiones materiales sólo en el chat.

---

# 20. PRINCIPIO OPERATIVO DEL PROYECTO

```text
contrato y estado durable
          ↓
         MAIN
          ↓
dependencias y puertas de autorización
          ↓
especialistas con fronteras estables, cuando correspondan
          ↓
handoffs auditables
          ↓
integración de MAIN
          ↓
batería, seguridad y revisión visual aplicable
          ↓
Git y documentación actualizados
```

Los especialistas producen piezas acotadas. MAIN protege la coherencia. Git,
contratos, pruebas y estado durable conservan la memoria del proyecto.
