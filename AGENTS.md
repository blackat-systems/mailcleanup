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

`DEVELOPMENT` — Joa aceptó Base Segura el 18 de agosto de 2026. La revisión
visual con herramienta no llegó a verificarse y permanece registrada como tal;
la aceptación es una decisión de producto, no evidencia visual retroactiva.

La preparación sintética de Mapa Total mediante D2 fue auditada e integrada en
MAIN. D3 `gmail-readonly-inventory` fue auditada e integrada en el árbol de
trabajo de MAIN después de ampliar D1 para aplicar altas, actualizaciones,
bajas y checkpoint en una transacción e iniciar un escaneo completo reemplazando
de forma controlada el índice anterior. La integración queda consolidada por el
commit que contiene este estado. D3 usa solamente dobles sintéticos: no están autorizados abrir
OAuth, conectar Gmail, solicitar credenciales ni usar datos reales. Existen
cuatro worktrees: MAIN sobre `main` y las fuentes D1, D2 y D3 conservadas como
evidencia. No hay remoto Git configurado.

## Objetivo actual

Mantener verde la integración sintética auditada de D3 y resolver con Joa la
próxima puerta del producto. No iniciar D4, abrir OAuth, conectar una cuenta
real, persistir metadatos privados ni usar credenciales sin autorización.

---

# 2. PRIORIDAD

Conservar verde y auditable la integración D3 consolidada. Todo cambio
debe respetar el permiso mínimo, la allowlist de lectura, la atomicidad del
índice, la separación de secretos, la barrera de no escritura y los contratos
de seguridad e inventario.

Mapa Total, Estudio de Limpieza y Limpieza Controlada permanecen detrás de
puertas de autorización independientes. Las ideas futuras se registran sin
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
4. `docs/adr/0001-arquitectura-base-segura.md`;
5. `pyproject.toml`, `frontend/package.json`, lockfile y scripts;
6. `docs/ESTADO_BASE_SEGURA.md`;
7. `docs/DECISIONES.md`.

Para coordinación de MAIN y dependencias:

1. `docs/PROMPT_MAESTRO_MAIN.md`;
2. `docs/PLAN_DEPENDENCIAS.md`;
3. `docs/WORKTREE_REGISTRY.md`;
4. `docs/prompts/PLANTILLA_DEPENDENCIA.md`.

Para D2 prevalece `docs/contracts/GMAIL_SESSION_V1.md`. Para D3 prevalecen
`docs/contracts/SECURITY_PRIVACY_V1.md` y
`docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`.

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
- Navegación local por hash y consumo de `/api/v1`.

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

## Componentes

- `model.py`, `fixtures.py`, `classifier.py`: modelo versionado, dataset canónico
  y reglas de identidad, intención, confianza y protección.
- `repository.py`: migraciones, siembra sintética y persistencia de mensajes y
  planes simulados; no almacena credenciales.
- `service.py`, `api.py`, `main.py`: agregación, planes incapaces de ejecutarse,
  API y servidor fijado a `127.0.0.1:8765`.
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
- Mantener `canExecute: false` incondicional durante Base Segura.
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
`secure-gmail-session` y D3 `gmail-readonly-inventory` se conservan como
evidencia de entregas integradas. D4 no está autorizada y no debe crearse.

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

No hay remoto configurado. No inventarlo ni afirmar que un commit local fue
publicado.

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
- conserva loopback y `canExecute: false` durante Base Segura;
- pasan las pruebas específicas y, cuando corresponde, la batería global;
- un cambio visual fue recorrido o queda expresamente pendiente;
- API, código y documentación coinciden;
- el diff no contiene secretos, bases, cachés ni dependencias descargadas;
- Git y el registro de worktrees reflejan el estado real.

Base Segura no queda aceptada porque compile. Joa ya otorgó la aceptación
explícita; la revisión visual instrumental continúa registrada como evidencia
no verificada y deberá completarse antes de cerrar la experiencia de Mapa Total.

---

# 17. SEGURIDAD Y PRIVACIDAD

- No conectar Gmail ni abrir OAuth durante D3 sintética.
- No solicitar ni almacenar `credentials.json`, `token.json`, contraseñas o
  tokens.
- No usar mensajes, nombres ni direcciones reales en fixtures, pruebas, logs,
  capturas o commits.
- No renderizar HTML ni cargar imágenes o recursos remotos de correos.
- No enviar datos de correo a IA externa ni otros servicios.
- Mantener la aplicación en loopback.
- No introducir clientes Gmail o de red productivos durante D3.
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
- habilitar Estudio de Limpieza o Limpieza Controlada;
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
