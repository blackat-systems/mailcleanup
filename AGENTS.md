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
OAuth, conectar Gmail, solicitar credenciales ni usar datos reales. Existen siete
worktrees: MAIN y las fuentes D1-D6 conservadas como evidencia; no existe D7. D6
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
Queda consolidado por el commit que contiene este estado. D7 todavía no existe.
Esta aceptación cubre solamente planificación sintética sin efectos y no
habilita capacidades externas.

## Objetivo actual

Preparar el prompt autosuficiente D7 desde el SHA limpio que consolida C6. No
crear el worktree sin autorización explícita. La interfaz
aceptada consume solamente `/api/v2`; `/api/v3/study` todavía no está
implementada. No abrir OAuth, conectar una cuenta real, persistir metadatos
privados ni usar credenciales.

---

# 2. PRIORIDAD

Conservar verdes y auditables D3 y D4 sintéticas consolidadas. Todo cambio debe
respetar el permiso mínimo, la allowlist de lectura,
la atomicidad del índice, la clasificación conservadora, la separación de
secretos y la barrera de no escritura.

Mapa Total está aceptado con alcance sintético. Joa autorizó preparar Estudio de
Limpieza mediante C6, todavía sin implementación. Limpieza Controlada permanece
detrás de otra puerta independiente. Las ideas futuras se registran sin
incorporarlas al alcance activo.

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
5. `docs/contracts/CLEANUP_PLAN_V1.md` para C6 y la futura D7;
6. `docs/adr/0001-arquitectura-base-segura.md`;
7. `pyproject.toml`, `frontend/package.json`, lockfile y scripts;
8. `docs/ESTADO_BASE_SEGURA.md`;
9. `docs/DECISIONES.md`.

Para coordinación de MAIN y dependencias:

1. `docs/PROMPT_MAESTRO_MAIN.md`;
2. `docs/PLAN_DEPENDENCIAS.md`;
3. `docs/WORKTREE_REGISTRY.md`;
4. `docs/prompts/PLANTILLA_DEPENDENCIA.md`.

Para D2 prevalece `docs/contracts/GMAIL_SESSION_V1.md`. Para D3 prevalecen
`docs/contracts/SECURITY_PRIVACY_V1.md` y
`docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`. Para D4 prevalece
`docs/contracts/CLASSIFICATION_DOMAIN_V1.md`. Para D5 prevalece el contrato
aprobado `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`. Su integración sintética no
habilita Gmail, OAuth ni datos reales. Para C5 y D6 prevalece
`docs/contracts/MAPA_TOTAL_API_V1.md`; su API `/api/v2` es exclusivamente local
y sintética. Para C6 prevalece el contrato aceptado
`docs/contracts/CLEANUP_PLAN_V1.md`. Es base para redactar D7, pero no autoriza
crear su worktree ni habilita datos reales o ejecución.

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

Windows es la plataforma objetivo inicial. No reemplazar tecnologías centrales
ni agregar dependencias importantes sin necesidad demostrada y, cuando afecte
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
- `frontend/src`: presentación, navegación, selección y consumo tipado de la API;
  no duplica reglas de clasificación o seguridad.
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
el commit que contiene este estado.

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
C6 aceptada → SHA limpio → prompt D7 → autorización de worktree
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

---

# 17. SEGURIDAD Y PRIVACIDAD

- No conectar Gmail ni abrir OAuth hasta una autorización específica posterior;
  C6 y la futura D7 son sintéticas.
- No solicitar ni almacenar `credentials.json`, `token.json`, contraseñas o
  tokens.
- No usar mensajes, nombres ni direcciones reales en fixtures, pruebas, logs,
  capturas o commits.
- No renderizar HTML ni cargar imágenes o recursos remotos de correos.
- No enviar datos de correo a IA externa ni otros servicios.
- Mantener la aplicación en loopback.
- No introducir clientes Gmail o de red productivos durante C6 o D7.
- Aplicar `SECURITY_PRIVACY_V1.md`: origen, métodos, endpoints, encabezados,
  tamaños y reintentos se deniegan por defecto salvo allowlist expresa.
- No usar el índice SQLite vigente con datos reales: todavía no tiene cifrado
  autenticado, ACL, retención y borrado verificable definidos.
- Mantener entornos, bases, cachés y dependencias descargadas fuera de Git.
- No implementar eliminación definitiva ni vaciado de Papelera.
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
- aceptar C6, crear D7 o habilitar Limpieza Controlada;
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
