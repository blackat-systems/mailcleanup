# Auditoría de herencia del proyecto anterior

Fecha: 18 de agosto de 2026.

Responsable: MAIN.

Estado: auditoría histórica consolidada. Sus hallazgos describen el estado
anterior al portado selectivo.

Confirmación posterior: Joa aceptó la recomendación de portado selectivo y la
arquitectura Python + React/TypeScript + SQLite. Este documento conserva el
estado observado antes de comenzar esa implementación.

Resultado posterior: la implementación y las verificaciones actuales se
registran en `ESTADO_BASE_SEGURA.md`. Los defectos heredados descriptos aquí no deben
interpretarse como estado vigente después del portado.

## 1. Resultado ejecutivo

El proyecto nuevo está en
`C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup`, sobre la rama `main` y
con `HEAD` inicial
`fecdef43745a7b145641394651b364378cf6257a`. No coincide con la ruta histórica,
pero heredó su historial Git completo y su candidato funcional.

La ruta histórica esperada,
`C:\Users\Joaquin\Desktop\chatgptprojects\limpiar_mails`, no estaba disponible.
Por eso no se tocó ni se leyó como carpeta independiente. La comparación se
realizó usando los commits históricos presentes en el repositorio nuevo.

Dictamen: la planificación, los contratos de seguridad, la arquitectura general
y varias piezas de `src/mailmap` son rescatables. El candidato completo no debe
aceptarse porque conserva un prototipo capaz de modificar Gmail, tiene una
batería que informa éxito aun cuando falla, arrastra entornos locales rotos por
el traslado y carece de verificación visual actual.

Recomendación única: **portar selectivamente componentes auditados**.

## 2. Identidad del proyecto nuevo

| Dato | Evidencia directa |
|---|---|
| Ruta | `C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup` |
| Proyecto histórico esperado | `C:\Users\Joaquin\Desktop\chatgptprojects\limpiar_mails` |
| ¿Coinciden? | No |
| ¿Existe la ruta histórica? | No durante esta auditoría |
| Repositorio Git | Sí |
| Rama inicial | `main` |
| HEAD inicial | `fecdef43745a7b145641394651b364378cf6257a` |
| Estado inicial | Limpio |
| Remotos | Ninguno configurado |
| Worktrees | Uno: MAIN en `mailcleanup` |

La carpeta es nueva por ruta, pero no por historia: `HEAD` es exactamente el
commit histórico que agregó el prompt anterior de inicialización de MAIN.

## 3. Estado Git e historia heredada

Los commits forman una única secuencia; `3209f04` es ancestro de `0a90b71`:

1. `28bfaf3`: base inicial de MAIN.
2. `3209f044d12107511aaf9f973b1cc6baf89e9405`: planificación previa al
   desarrollo adelantado.
3. `0a90b71403bb176c6fd2457213bcb8b347428a92`: candidato funcional sintético.
4. `d4a2d5efa1577b727db2dd6373b60661deee7034`: documentación posterior.
5. `fecdef43745a7b145641394651b364378cf6257a`: prompt de inicialización anterior.

Entre `3209f04` y `0a90b71` se modificaron o agregaron 53 archivos, con 6.278
líneas agregadas y 41 eliminadas. El cambio introdujo `src/mailmap`, el frontend,
SQLite, scripts, pruebas y documentación de estado. El prototipo
`src/gmail_cleaner` ya existía antes de ese candidato.

No se creó, movió, fusionó, rebasó ni eliminó ninguna rama o worktree. No se
hizo commit ni push durante esta intervención.

## 4. Inventario de la herencia

### Planificación y gobernanza

- `AGENTS.md`: reglas de autoridad, seguridad, MAIN y especialistas.
- `docs/CONTRATO_MVP.md`: cuatro hitos, invariantes y criterios de aceptación.
- `docs/AUDITORIA_PRE_DESARROLLO.md`: reducción de alcance y riesgos del
  prototipo.
- `docs/ESPECIFICACION_FUNCIONAL.md`: visión de producto amplia.
- `docs/PROMPT_MAESTRO_MAIN.md`: responsabilidades y método de integración.
- `docs/WORKTREE_REGISTRY.md`: registro de coordinación, con la ruta anterior
  desactualizada antes de esta auditoría.

### Candidato sintético

- `src/mailmap`: modelo, fixtures, clasificación, persistencia, servicio y API.
- `frontend`: interfaz React/TypeScript.
- `docs/contracts/API_V1.md`: contrato de la API local.
- `docs/adr/0001-arquitectura-hito-0.md`: decisión arquitectónica heredada.
- `tests/test_hito0_domain.py` y `tests/test_hito0_api.py`: pruebas de dominio y
  API.
- `scripts`: preparación, verificación y arranque local.

### Prototipo legado

- `src/gmail_cleaner`: CLI previa con OAuth, lectura de metadatos, generación de
  planes, desuscripción HTTP y movimiento a Papelera mediante `batchModify`.
- `config.legacy.example.toml`: rutas de credenciales y opciones del prototipo.
- `tests/test_core.py`: pruebas parciales de sus funciones puras.

## 5. Cómo funciona el candidato adelantado

El recorrido sintético es:

```text
fixtures inventados
        ↓
Repository los migra y guarda en SQLite
        ↓
classifier normaliza, identifica y clasifica con evidencias
        ↓
MailmapService agrupa fuentes y flujos, aplica protecciones y crea planes
        ↓
FastAPI expone la API local v1
        ↓
React/TypeScript presenta panorama, fuentes, detalle y vista previa
```

### Python

Python implementa las reglas delicadas. El modelo define rubro, intención,
suscripción, protección, confianza y evidencia. El clasificador empieza
separando remitentes y sólo fusiona por señales positivas presentes en los
fixtures. El servicio agrupa por fuente, separa flujos por intención y excluye
mensajes protegidos del plan simulado.

### SQLite

SQLite es un archivo de base local. La migración v1 guarda los metadatos
sintéticos y los planes simulados; no guarda cuerpos HTML, imágenes, tokens ni
credenciales. El dataset se vuelve a sembrar cuando cambia su versión. Ese
comportamiento es razonable para un laboratorio sintético, pero deberá revisarse
antes de conservar datos reales o decisiones del usuario.

### React y TypeScript

React construye las pantallas y mantiene el estado de selección. TypeScript
describe el contrato esperado de la API. La interfaz no reimplementa las reglas
de clasificación: consume resultados del backend y muestra evidencias,
protecciones y advertencias.

### Plan simulado

El usuario elige fuentes, fecha, cantidad a conservar y operaciones. El backend
congela IDs y revisiones de mensajes elegibles, guarda una vista previa local y
responde siempre `canExecute: false`. Revalidar detecta mensajes ausentes,
cambios de revisión o protecciones nuevas. No existe una ruta de ejecución en
`src/mailmap`.

## 6. Qué impide que la aplicación candidata toque Gmail

En `src/mailmap` se verificó:

- no hay importaciones de Google, OAuth, `requests`, `httpx` ni sockets;
- la API no expone conexión, baja ni modificación;
- el único `POST` funcional crea o revalida planes locales;
- `canExecute` es falso en creación y revalidación;
- el comando normal de Uvicorn usa `127.0.0.1`;
- los fixtures usan dominios `.example`;
- la configuración informa Gmail y OAuth bloqueados.

Esto demuestra que **la aplicación candidata `mailmap`** está desconectada. No
demuestra lo mismo del repositorio completo: `src/gmail_cleaner` sí contiene
`gmail.modify`, `InstalledAppFlow`, `batchModify` y `requests.post`. No fue
ejecutado. Mientras siga importable y empaquetable, la frase “imposibilidad
técnica del repositorio” sería falsa.

## 7. Seguridad, datos locales y archivos inesperados

No se encontraron archivos rastreados con nombres de credenciales, tokens,
claves, bases ni secretos. En la raíz tampoco existen `credentials.json`,
`token.json`, `config.toml`, `planes/` ni `resultados/`.

La lista de ignorados contiene:

- `.venv` y cachés Python;
- `frontend/node_modules` y `frontend/dist`;
- `data/mailmap-hito0.db`;
- metadatos locales de instalación editable.

La base ignorada tenía 22 mensajes, todos con remitentes `.example`, modo
`synthetic` y un plan simulado. No se inspeccionaron ni solicitaron correos,
credenciales o tokens reales.

Los entornos locales fueron trasladados junto con el proyecto y no son
portables: el entorno Python editable todavía apunta a `limpiar_mails` y los
enlaces de `node_modules` ya no resuelven sus ejecutables.

## 8. Verificaciones repetidas por MAIN

| Estado | Comprobación | Evidencia / resultado |
|---|---|---|
| Verificado | Identidad Git | `main`, HEAD `fecdef…`, un worktree, sin remoto |
| Verificado | Relación histórica | `3209f04` es ancestro de `0a90b71` |
| Verificado | Estado inicial | árbol rastreado limpio |
| Verificado | Archivos sensibles por nombre | ninguno rastreado; ninguno en ubicaciones raíz previstas |
| Verificado | Dataset local | 22 mensajes, 15 fuentes, 0 fixtures faltantes, 0 remitentes fuera de `.example` |
| Verificado | Pruebas Python | 18 pasaron usando `src` como raíz de importación |
| Verificado | Ruff | sin hallazgos en `mailmap` y sus pruebas |
| Verificado | mypy estricto | sin hallazgos en 8 archivos de `mailmap` |
| Falló | `scripts/check.ps1` como orquestador | mostró errores, imprimió éxito y devolvió código 0 |
| Falló | Entorno Python trasladado | la instalación editable apunta a la ruta histórica |
| Falló | Frontend reproducible | faltan módulos resolubles de ESLint y Vitest en `node_modules` trasladado |
| Pendiente | Build frontend actual | requiere reconstruir el entorno local después de la decisión de Joa |
| Pendiente | Recorrido visual | no fue abierto ni inspeccionado |
| Pendiente | Prueba HTTP local repetida | no se inició servidor durante esta auditoría documental |
| Pendiente | Exactitud de RFC 8058 real | el Hito 0 sólo usa una señal sintética; no valida cabeceras reales |
| Inferido | Arquitectura apropiada | la interacción y separación de capas justifican Python + React + SQLite |

## 9. Hallazgos críticos y contradicciones

### Alta: el repositorio conserva acciones reales

El prototipo legado puede solicitar `gmail.modify`, abrir OAuth, mover mensajes a
Papelera y enviar una baja HTTP. Está separado del recorrido `mailmap`, pero no
aislado de forma técnica suficiente para sostener una garantía sobre el
repositorio completo.

### Alta: la batería puede producir falsos positivos

`scripts/check.ps1` no detiene el flujo por códigos de salida nativos. En esta
auditoría, pytest y Node fallaron; el script siguió, imprimió “Batería completa
aprobada” y finalizó con código 0. Las afirmaciones históricas basadas sólo en
ese orquestador no son evidencia suficiente.

### Media: estado documental no autorizado

El contrato, ADR, README y registro heredados afirmaban que Joa había aprobado
la arquitectura y el Hito 0. La instrucción actual niega que esos commits sean
aceptación. MAIN corrigió esas afirmaciones en la documentación nueva.

### Media: entorno no reproducible después del traslado

La lógica Python pasa sus pruebas con una ruta de importación corregida, pero el
entorno instalado apunta al proyecto anterior. El frontend no encuentra sus
ejecutables aunque `node_modules` exista físicamente. Esto es un problema de
entorno trasladado; todavía no prueba un defecto del código frontend.

### Media: evidencia visual ausente

No existe una inspección actual de escritorio ni de móvil estrecho. Por lo tanto
no pueden aceptarse accesibilidad, responsive ni terminación visual.

### Baja: documentación y dataset divergieron

El estado heredado informaba 21 mensajes; el fixture y la base actuales tienen
22. Esta auditoría actualizó el estado a la evidencia real.

### Baja: transparencia incompleta de protecciones

El clasificador protege también `SENT`, `DRAFT` y `TRASH`, pero la configuración
expuesta a la interfaz enumera sólo cinco etiquetas. La protección existe en el
backend; la explicación visible no refleja todo el conjunto.

### Baja: RFC 8058 sólo está representado de forma sintética

`mailmap` decide “un clic autenticado” mediante marcadores sintéticos de DKIM y
DMARC; no modela todavía la cobertura exacta de cabeceras. Esto sirve para el
Hito 0 como escenario, pero no es código reusable sin auditoría para una baja
real.

## 10. Qué se puede rescatar

### Planificación y contratos

- comprensión antes de actuar;
- fuente y flujo como unidades separadas;
- taxonomía multidimensional;
- evidencia y confianza explícitas;
- agrupación conservadora;
- protección por defecto y contradicción bloqueante;
- separación entre baja y disposición del historial;
- hitos y puertas de autorización;
- prohibición de eliminación definitiva y de IA externa en el MVP.

### Arquitectura

Python + FastAPI, React/TypeScript y SQLite siguen siendo una combinación
coherente para una aplicación local interactiva. Separan reglas, persistencia,
contrato y presentación sin requerir infraestructura externa.

### Código potencialmente reusable, sujeto a auditoría por pieza

- enums y estructuras de `src/mailmap/model.py`;
- fixtures sintéticos y sus etiquetas de cobertura;
- normalización y precedencia conservadora del clasificador;
- migración inicial y repositorio sintético;
- contrato y rutas de lectura de la API;
- shell, navegación y presentación de evidencias del frontend;
- pruebas de dominio y API como base de regresión.

Que una pieza figure aquí no significa que ya esté aceptada. Significa que
existe evidencia suficiente para auditarla y corregirla en vez de reescribirla
sin mirar.

## 11. Qué no debe trasladarse automáticamente

- `src/gmail_cleaner` y `config.legacy.example.toml` como parte ejecutable;
- la dependencia opcional `gmail-future` sin una futura puerta de Hito 1;
- `scripts/check.ps1` sin corregir su manejo de fallos;
- `.venv`, `node_modules`, `dist`, cachés, bases y metadatos de instalación;
- afirmaciones de que Joa aprobó el candidato o de que el Hito 0 terminó;
- resultados de pruebas históricas sin repetición reproducible;
- la detección de baja del prototipo como implementación de producción;
- el esquema de SQLite como diseño ya aprobado para datos reales;
- la interfaz como visualmente aceptada.

## 12. Recomendación única de MAIN

**Portar selectivamente componentes auditados.**

No conviene reconstruir todo desde cero porque los contratos, la separación de
capas, el dataset sintético y 18 pruebas Python ya aportan evidencia útil. No
conviene conservar el candidato completo porque incluye capacidad real de
modificación, una batería con falsos positivos y entornos no reproducibles.

Si Joa confirma esta ruta, el próximo paso será exclusivamente sintético:

1. establecer una base local reproducible sin copiar entornos;
2. aislar o retirar del producto Hito 0 el prototipo `gmail_cleaner`;
3. corregir el orquestador para que cualquier fallo detenga la batería;
4. auditar y aceptar por capas `mailmap`, SQLite, API y frontend;
5. repetir pruebas, lint, tipos, build y recorrido visual;
6. recién entonces decidir si el Hito 0 cumple su contrato.

La evidencia que cambiaría esta recomendación sería un defecto arquitectónico
transversal o una divergencia masiva entre UI, API y dominio. No se encontró esa
evidencia en esta auditoría.

## 13. Decisión resuelta

Joa confirmó el portado selectivo sobre Python + React/TypeScript + SQLite y
autorizó Base Segura con datos exclusivamente sintéticos. La implementación
retiró el prototipo capaz de modificar Gmail, reconstruyó los entornos y corrigió
la batería. El estado vigente y sus pendientes están en
`docs/ESTADO_BASE_SEGURA.md`.

La nomenclatura activa posterior a esta auditoría es:

- Base Segura: antiguo Hito 0;
- Mapa Total: antiguo Hito 1;
- Estudio de Limpieza: antiguo Hito 2;
- Limpieza Controlada: antiguo Hito 3.
