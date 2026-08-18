# Plan de dependencias y worktrees

Estado del plan: ejecución controlada; D1 está `INTEGRADA` localmente y las
demás dependencias conservan sus bloqueos.

Fecha de inspección: 18 de agosto de 2026.

Este documento define fronteras, dependencias, puertas y orden de integración.
No autoriza capacidades, no crea worktrees y no reemplaza contratos funcionales
ni de API. `docs/WORKTREE_REGISTRY.md` registra solamente worktrees reales.

## 1. Base verificada de la planificación

| Campo | Evidencia observada |
|---|---|
| Ruta | `C:\Users\Joaquin\Desktop\chatgptprojects\mailcleanup` |
| Rama | `main` |
| HEAD de MAIN al integrar D1 | `7720ad4c57c984c7ba6fc2e6bc9c5e02119756a2` |
| Estado actual | D1 integrada y consolidada en el commit que contiene este estado |
| Worktrees | Dos: MAIN y D1 `real-index-persistence` |
| Remotos | Ninguno configurado |
| AGENTS.md | Inicializado, sin campos de plantilla pendientes |
| Base Segura | Consolidada técnicamente; revisión visual en escritorio y 390 px y aceptación de Joa pendientes |
| Capacidades autorizadas | Base Segura sintética y preparación/implementación sintética de D1; ningún acceso real ni proceso operativo posterior |

El SHA anterior es la base de MAIN sobre la que se integró D1, no un commit de
integración. Cada dependencia posterior requiere un SHA limpio nuevo que
contenga sus contratos estabilizados y las autorizaciones necesarias.

## 2. Inventario de lo que ya existe

Base Segura ya contiene y prueba:

- modelo sintético versionado, fixtures canónicos y normalización local;
- clasificación determinista de fuente, flujo, intención, suscripción,
  confianza y evidencia;
- protecciones automáticas, precedencia conservadora y revisión por
  contradicción;
- SQLite local con migración inicial, siembra sintética y planes simulados;
- agregación de panorama, fuentes, flujos, muestras e historial;
- API local v1 de lectura y vista previa con `canExecute: false`;
- interfaz React para panorama, vistas de Fuentes, detalle, selección, plan
  simulado, historial y estado de seguridad;
- barrera automática contra Gmail, OAuth, clientes de red, credenciales y rutas
  de ejecución;
- scripts oficiales de preparación, ejecución y batería global.

No existen todavía:

- un modelo normalizado apto para datos reales y estable entre procesos;
- sesión OAuth, almacén seguro de credenciales ni revocación;
- inventario paginado o reanudable de Gmail;
- índice privado real, checkpoints ni ciclo de borrado de datos locales;
- clasificación calibrada sin ayudas de fixtures sintéticos;
- memoria persistente de correcciones y protecciones decididas por Joa;
- planes reales con conjunto congelado de identificadores;
- rutas de modificación, lotes, reintentos o reversión;
- ejecución automática o manual integrada de desuscripciones.

## 3. Responsabilidades que permanecen en MAIN

MAIN conserva y no delega como módulo aislado:

- contrato del MVP y puertas entre Base Segura, Mapa Total, Estudio de Limpieza
  y Limpieza Controlada;
- modelo conceptual transversal: fuente, flujo, intención, suscripción,
  protección, confianza, evidencia, decisión, plan y ejecución;
- contrato normalizado independiente del proveedor y estabilidad de
  identificadores;
- versionado de la API y composición entre backend, persistencia y frontend;
- taxonomías compartidas, fixtures canónicos y reglas globales de precedencia;
- selección y justificación de permisos, política de credenciales, privacidad
  del índice y eliminación local;
- invariantes de seguridad, batería global y barreras negativas;
- preparación de prompts, registro de worktrees, auditoría, integración y
  actualización del estado durable.

Cuando una dependencia necesite cambiar uno de estos puntos, devuelve la
decisión a MAIN. No lo redefine dentro de su worktree.

## 4. Contratos que MAIN debe estabilizar primero

### C1. Modelo normalizado e identidad estable

Debe reemplazar la dependencia accidental del modelo actual respecto de ayudas
sintéticas como `source_hint` y `flow_hint`. Define campos, nulabilidad,
procedencia, evidencia, versión, identificadores de mensaje, conversación,
fuente y flujo, y cómo sobreviven las correcciones a una nueva sincronización.

Estado: estabilizada para la persistencia sintética de D1 por
`docs/contracts/INDEX_PERSISTENCE_V1.md`; `BLOQUEADA POR AUTORIZACIÓN` para
registros reales y consumidores posteriores.

### C2. Límite de lectura

Debe enumerar los campos y encabezados permitidos. Google permite pedir
`format=METADATA` y restringir encabezados mediante `metadataHeaders`; el
alcance `gmail.metadata` no permite usar el parámetro de búsqueda `q` en
`messages.list`. Por eso no se puede prometer a la vez "sólo metadatos" y una
estrategia basada en búsquedas de Gmail sin elegir explícitamente el alcance y
el algoritmo.

Debe decidir si quedan prohibidos o admitidos, con justificación separada:

- `snippet`;
- estructura MIME sin contenido;
- nombres y tipos de adjuntos;
- encabezados de autenticación completos;
- cualquier fragmento de cuerpo.

Estado: `BLOQUEADA POR AUTORIZACIÓN` y decisión de privacidad de Joa.

### C3. Sesión, credenciales y revocación

Debe fijar alcance OAuth mínimo, aplicación cliente, verificación de la cuenta,
almacén seguro del sistema operativo, renovación, cierre de sesión, revocación,
errores y garantía de no versionado. No se elige el mecanismo de Windows por
suposición.

Estado: `BLOQUEADA POR AUTORIZACIÓN` de Gmail y OAuth.

### C4. Índice privado y sincronización

Debe definir esquema, migraciones, checkpoints, estados de sincronización,
reanudación, retención, borrado local y protección en reposo. La sincronización
parcial de Gmail usa `historyId`; si el registro ya no está disponible, la API
responde 404 y obliga a una sincronización completa. Ese caso debe formar parte
del contrato antes de implementar.

Estado: estabilizada para migraciones, checkpoint y borrado sintéticos de D1;
`BLOQUEADA POR AUTORIZACIÓN` para ubicación, permisos y cifrado de datos reales.

### C5. API de Mapa Total

Debe separar conexión, sincronización, índice, mapa y correcciones; versionar
todo cambio incompatible con la API v1 sintética y conservar estados de carga,
reanudación, error y desconexión.

Estado: `BLOQUEADA POR CONTRATO`; consume C1 a C4.

### C6. Plan real

Debe definir conjunto congelado de IDs, filtros, exclusiones, muestras, tamaños,
caducidad, revalidación, cancelación e historial sin efectos. Debe distinguir
tamaño seleccionado de espacio efectivamente liberado.

Estado: `BLOQUEADA POR AUTORIZACIÓN` de Estudio de Limpieza.

### C7. Ejecución controlada

Debe definir plan aprobado, nueva autorización, permiso `gmail.modify`,
revalidación por mensaje, idempotencia, lotes, ledger, fallos parciales,
reintentos, Archivo, Papelera y reversión. Excluye eliminación definitiva y
vaciado de Papelera.

Estado: `BLOQUEADA POR AUTORIZACIÓN` de Limpieza Controlada.

### C8. Evidencia y acción de desuscripción

Debe separar presentación manual de ejecución automática. Un enlace GET o
`mailto:` sólo puede mostrarse para una acción consciente fuera del motor. La
automatización requiere RFC 8058: HTTPS, encabezado
`List-Unsubscribe-Post: List-Unsubscribe=One-Click`, firma DKIM válida que cubra
los encabezados, consentimiento específico, POST sin cookies ni credenciales y
sin aceptar redirecciones. El resultado es una solicitud aceptada, no una baja
garantizada.

Estado: `BLOQUEADA POR AUTORIZACIÓN` de Limpieza Controlada y por contrato.

## 5. Dependencias especialistas propuestas

### D1 — `real-index-persistence`

| Campo | Definición |
|---|---|
| ID | D1 |
| Proceso | Mapa Total |
| Responsabilidad única | Implementar persistencia y migraciones del índice normalizado, checkpoints, estados de sincronización y borrado local conforme a C1 y C4. |
| Razón para separarlo | Es una frontera local, sin red, con invariantes de migración y recuperación verificables en aislamiento. |
| Estado actual | `INTEGRADA` y consolidada en el commit que contiene este estado |
| Dependencias previas | Joa autorizó abrir D1 como infraestructura sintética; C1/C4 quedan estabilizados para ese alcance por `docs/contracts/INDEX_PERSISTENCE_V1.md`. |
| Contratos que consume | C1, C4, reglas SQLite vigentes. |
| Resultados que produce | Repositorios y migraciones versionadas para índice, checkpoints y ciclo de borrado. |
| Consumidores posteriores | D3, D5, D7 y composición de MAIN. |
| Permitido | Nuevos módulos de índice/persistencia, migraciones y pruebas; adaptador explícito en `repository.py` sólo si el prompt lo delimita. |
| Prohibido | OAuth, clientes Gmail, clasificación, API pública, frontend y datos reales en pruebas. |
| Rama propuesta | `codex/real-index-persistence` |
| Ruta real | `C:\Users\Joaquin\.codex\worktrees\ab1f\mailcleanup` |
| Commit base requerido | SHA limpio que incorpore `docs/contracts/INDEX_PERSISTENCE_V1.md` y la autorización D-017; el prompt autosuficiente debe registrar y comunicar ese SHA exacto. |
| Verificaciones específicas | Migración desde base nueva y versión anterior; transacciones; reanudación; borrado; pytest, Ruff y mypy afectados. |
| Criterios de aceptación | No pierde decisiones ni duplica registros; reanuda de forma determinista; elimina el índice solicitado; no almacena secretos. |
| Riesgos de integración | Cambios de esquema concurrentes, IDs inestables y acoplamiento con el repositorio sintético. |
| Paralelización real | Puede coexistir con D2 una vez congelados C1, C3 y C4; no con otro cambio de esquema. |
| Condición exacta de desbloqueo | Cumplida para creación sintética por D-017 y el contrato v1. Antes de crear: batería aplicable verde, SHA limpio y prompt exacto. Esto no acepta la revisión visual ni habilita Gmail o Mapa Total operativo. |

### D2 — `secure-gmail-session`

| Campo | Definición |
|---|---|
| ID | D2 |
| Proceso | Mapa Total |
| Responsabilidad única | Implementar autorización de una cuenta en modo de sólo lectura, identidad de cuenta, almacenamiento seguro, renovación, desconexión y revocación. |
| Razón para separarlo | Las credenciales forman una frontera de seguridad distinta del inventario y requieren pruebas negativas propias. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | Aceptación de Base Segura; autorización específica de Gmail/OAuth y Mapa Total; C2/C3 aprobados. |
| Contratos que consume | C2, C3 y puerto de sesión definido por MAIN. |
| Resultados que produce | Sesión de sólo lectura y estados de conexión sin exponer tokens. |
| Consumidores posteriores | D3 y composición de MAIN. |
| Permitido | Nuevos módulos de sesión Gmail, almacén de credenciales y pruebas sintéticas con dobles; configuración ignorada por Git. |
| Prohibido | Inventario completo, clasificación, SQLite del mapa, frontend, `gmail.modify`, credenciales reales en pruebas o commits. |
| Rama propuesta | `codex/secure-gmail-session` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-secure-gmail-session` |
| Commit base requerido | SHA futuro limpio que contenga C2/C3 y dependencias autorizadas. |
| Verificaciones específicas | Pruebas de scopes, cuenta esperada, renovación, revocación, errores, permisos de archivos, secretos y barrera de no escritura. |
| Criterios de aceptación | No usa contraseña, no registra tokens, no pide permisos de modificación y permite revocar y borrar el estado local. |
| Riesgos de integración | Alcance excesivo, almacenamiento inseguro, filtrado en logs y dependencia directa del SDK en el dominio. |
| Paralelización real | Puede coexistir con D1 si sus interfaces están congeladas y no modifica archivos compartidos. |
| Condición exacta de desbloqueo | Joa autoriza Gmail, OAuth y Mapa Total con el alcance explicado; MAIN aprueba C2/C3, dependencias y prompt, pasa la batería y fija un SHA limpio. |

### D3 — `gmail-readonly-inventory`

| Campo | Definición |
|---|---|
| ID | D3 |
| Proceso | Mapa Total |
| Responsabilidad única | Inventariar en sólo lectura IDs, etiquetas, fechas, tamaño y encabezados autorizados; paginar, reanudar y normalizar sin clasificar. |
| Razón para separarlo | Concentra interacción con Gmail, límites, lotes y recuperación, pero no debe decidir producto ni persistencia. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D1 y D2 integradas; C1 a C5 estables. |
| Contratos que consume | Sesión D2, repositorio D1, C1/C2/C4/C5. |
| Resultados que produce | Registros normalizados y eventos de progreso/reanudación; inventario de Spam separado y exclusión de Enviados, Borradores y Papelera. |
| Consumidores posteriores | D4, D5, D6 y composición de MAIN. |
| Permitido | Adaptador de inventario Gmail, paginación/sincronización y pruebas con API simulada. |
| Prohibido | Cuerpos no autorizados, acciones de escritura, clasificación, correcciones, UI y credenciales reales. |
| Rama propuesta | `codex/gmail-readonly-inventory` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-gmail-readonly-inventory` |
| Commit base requerido | SHA limpio posterior a la integración auditada de D1 y D2. |
| Verificaciones específicas | Paginación, límites, reintentos, cancelación, checkpoint, 404 de historial, duplicados, etiquetas protegidas, alcance y ausencia de escritura. |
| Criterios de aceptación | Una interrupción se reanuda sin duplicar; una historia vencida fuerza resincronización segura; sólo se persisten campos permitidos. |
| Riesgos de integración | Confundir conversación con mensaje, excluir datos antes de protegerlos, cuotas, cambios durante el escaneo y scope insuficiente. |
| Paralelización real | No con D1/D2 antes de integrarlas; luego puede coexistir sólo con UI basada en contrato y fixtures, no con cambios de C1/C5. |
| Condición exacta de desbloqueo | D1/D2 integradas y auditadas; C1-C5 congelados; batería global verde; MAIN fija SHA limpio y prompt; autorización de Mapa Total sigue vigente. |

### D4 — `real-classification-domain`

| Campo | Definición |
|---|---|
| ID | D4 |
| Proceso | Mapa Total |
| Responsabilidad única | Adaptar y ampliar la clasificación explicable para registros reales sin `source_hint` ni `flow_hint`, conservando desconocidos y evidencia. |
| Razón para separarlo | Es una ampliación concreta del dominio existente y puede probarse con corpus sintético normalizado sin red ni UI. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D3 integrada; C1/C2 y taxonomías confirmadas. |
| Contratos que consume | Registros normalizados D3, modelo C1, reglas de clasificación y protección vigentes. |
| Resultados que produce | Agrupación conservadora, identidad/fuentes/flujos reales, confianza, evidencia y desconocidos estables. |
| Consumidores posteriores | D5, D6 y D7. |
| Permitido | Módulos de clasificación/dominio y pruebas sintéticas específicas. |
| Prohibido | OAuth, API Gmail, persistencia, API pública, UI, mutaciones y servicios externos. |
| Rama propuesta | `codex/real-classification-domain` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-real-classification-domain` |
| Commit base requerido | SHA limpio posterior a D3 y al contrato de identidad estable. |
| Verificaciones específicas | Baja confianza separada, contradicción bloqueante, multi-remitente/multi-fuente, infraestructura compartida, varios flujos y ausencia de ayudas sintéticas. |
| Criterios de aceptación | No presenta inferencias como hechos; cada resultado conserva evidencia; no fusiona confianza baja; las reglas actuales siguen cubiertas. |
| Riesgos de integración | IDs cambiantes, sobreagrupación, taxonomías superpuestas y dependencia accidental de encabezados no autorizados. |
| Paralelización real | Puede prepararse con fixtures después de congelar C1/C2, pero no integrarse antes de D3; no en paralelo con cambios a taxonomías. |
| Condición exacta de desbloqueo | D3 integrada; MAIN confirma corpus sintético, identidad, evidencia y taxonomías; batería verde, SHA limpio y prompt aprobado. |

### D5 — `local-policy-memory`

| Campo | Definición |
|---|---|
| ID | D5 |
| Proceso | Mapa Total |
| Responsabilidad única | Persistir nombres, separaciones/uniones, categorías y protecciones decididas por Joa, con precedencia y trazabilidad. |
| Razón para separarlo | Une corrección y protección manual porque ambas son políticas del usuario sobre la misma identidad estable; separarlas duplicaría precedencia y persistencia. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D1, D3 y D4 integradas; identidad y precedencia estables. |
| Contratos que consume | C1, resultados D4, repositorio D1 y reglas globales de protección. |
| Resultados que produce | Comandos y consultas de política local, auditoría de decisiones y reaplicación determinista. |
| Consumidores posteriores | D6, D7 y D9. |
| Permitido | Módulos de políticas, migración/adaptador delimitado y pruebas. |
| Prohibido | Gmail/OAuth, heurísticas nuevas, API pública no acordada, UI y acciones reales. |
| Rama propuesta | `codex/local-policy-memory` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-local-policy-memory` |
| Commit base requerido | SHA limpio posterior a D4 y al contrato de precedencia. |
| Verificaciones específicas | Persistencia, reaplicación, undo lógico, evidencia contradictoria, cambio de IDs, migraciones y no generalización silenciosa. |
| Criterios de aceptación | La decisión de Joa prevalece según contrato, queda explicada y no convierte una corrección puntual en regla global accidental. |
| Riesgos de integración | Conflicto con reglas automáticas, correcciones huérfanas y migraciones simultáneas. |
| Paralelización real | No con D1 ni D4; D6 puede empezar sólo sobre un API congelado y fixtures después de definir salidas. |
| Condición exacta de desbloqueo | D4 integrada; MAIN aprueba precedencia, comandos, migración y API; batería verde, base limpia y prompt completo. |

### D6 — `mapa-total-ui`

| Campo | Definición |
|---|---|
| ID | D6 |
| Proceso | Mapa Total |
| Responsabilidad única | Presentar conexión, progreso, reanudación, errores, mapa real, evidencia y correcciones mediante el API estable. |
| Razón para separarlo | Es una frontera de presentación TypeScript que puede consumir fixtures contractuales sin incorporar reglas de dominio. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D2-D5 integradas; C5 estable; revisión visual de Base Segura completada. |
| Contratos que consume | C5, sesión D2, progreso D3, mapa D4 y políticas D5. |
| Resultados que produce | Experiencia verificable de Mapa Total en escritorio y 390 px. |
| Consumidores posteriores | Aceptación de Mapa Total y D7. |
| Permitido | `frontend/src`, pruebas frontend y tipos generados/contractuales acordados. |
| Prohibido | Backend, clasificación, persistencia, OAuth interno, tokens, acciones reales y navegación externa automática. |
| Rama propuesta | `codex/mapa-total-ui` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-mapa-total-ui` |
| Commit base requerido | SHA limpio con C5 y backend de Mapa Total integrados. |
| Verificaciones específicas | ESLint, Vitest, build, estados vacíos/carga/error/reanudación, escritorio y 390 px, ausencia de secretos. |
| Criterios de aceptación | Distingue hechos e inferencias, no habilita procesos posteriores y permite entender/corregir sin ocultar protecciones. |
| Riesgos de integración | Duplicar reglas en frontend, mezclar estado sintético/real y prometer operaciones no autorizadas. |
| Paralelización real | Sólo puede construirse en paralelo tardío con backend si C5 está congelado y usa fixtures; integración después de D2-D5. |
| Condición exacta de desbloqueo | Backend y C5 integrados; MAIN entrega fixtures de contrato, SHA limpio, prompt y batería; Mapa Total continúa autorizado. |

La presentación de GET o `mailto:` de desuscripción, si C8 la habilita, es un
subalcance pequeño de esta interfaz o de la interfaz de Estudio de Limpieza. No
justifica un worktree independiente y nunca debe disparar una solicitud.

### D7 — `real-plan-engine`

| Campo | Definición |
|---|---|
| ID | D7 |
| Proceso | Estudio de Limpieza |
| Responsabilidad única | Crear, congelar, revalidar, invalidar y cancelar planes reales sin efectos. |
| Razón para separarlo | Es un agregado transaccional con invariantes propias y sigue siendo completamente incapaz de modificar Gmail. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | Mapa Total aceptado; Estudio de Limpieza autorizado; D1-D6 integradas; C6 aprobado. |
| Contratos que consume | Índice, políticas, protecciones, C6 y API que MAIN estabilice. |
| Resultados que produce | Snapshot de IDs, exclusiones, muestras, tamaños, advertencias, caducidad e historial. |
| Consumidores posteriores | D8, D9 y aceptación de Estudio de Limpieza. |
| Permitido | Nuevos módulos de planificación, persistencia/migraciones delimitadas y pruebas. |
| Prohibido | Cliente Gmail de escritura, ejecución, UI, desuscripción y reducción automática de protecciones. |
| Rama propuesta | `codex/real-plan-engine` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-real-plan-engine` |
| Commit base requerido | SHA limpio posterior a aceptación de Mapa Total y C6. |
| Verificaciones específicas | Snapshot inmutable, fechas de Córdoba, filtros, exclusiones, tamaños, cambio de protecciones, cancelación, migraciones y `canExecute: false`. |
| Criterios de aceptación | El plan enumera exactamente el alcance, nunca ejecuta y se reduce o invalida ante cambios relevantes. |
| Riesgos de integración | Confundir estimaciones, IDs obsoletos, carrera con sincronización y reutilizar un plan después de cambios. |
| Paralelización real | D8 puede empezar sólo con C6/API congelado y fixtures, pero se integra después de D7; no con otro cambio de planes o esquema. |
| Condición exacta de desbloqueo | Joa acepta Mapa Total y autoriza Estudio de Limpieza; MAIN aprueba C6/API, pasa batería, fija SHA limpio y prompt. |

### D8 — `estudio-ui`

| Campo | Definición |
|---|---|
| ID | D8 |
| Proceso | Estudio de Limpieza |
| Responsabilidad única | Presentar selección, alcance exacto, muestras, exclusiones, tamaños, advertencias, revalidación, cancelación e historial sin ejecución. |
| Razón para separarlo | Es una ampliación cohesiva de frontend que consume un plan estable y no debe implementar reglas de planificación. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D7 integrada o contrato C6/API completamente congelado para trabajo con fixtures. |
| Contratos que consume | C6 y API de planes reales. |
| Resultados que produce | Experiencia verificable de Estudio de Limpieza. |
| Consumidores posteriores | Aceptación de Estudio de Limpieza y D9. |
| Permitido | `frontend/src`, pruebas frontend y fixtures contractuales. |
| Prohibido | Backend, mutaciones Gmail, inferencias nuevas y representación engañosa del espacio liberado. |
| Rama propuesta | `codex/estudio-ui` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-estudio-ui` |
| Commit base requerido | Preferentemente SHA posterior a D7; excepcionalmente SHA con contrato/API congelados para trabajo paralelo autorizado por MAIN. |
| Verificaciones específicas | ESLint, Vitest, build, escritorio, 390 px, accesibilidad básica, planes vencidos y errores parciales simulados. |
| Criterios de aceptación | El usuario entiende qué ocurriría, qué queda protegido y que todavía no existen efectos. |
| Riesgos de integración | UI adelantada al contrato, acciones ambiguas y pérdida de exclusiones al revalidar. |
| Paralelización real | Posible con D7 sólo después de congelar API y fixtures; se audita e integra después de D7. |
| Condición exacta de desbloqueo | Estudio autorizado; C6/API y fixtures aprobados; SHA limpio, batería y prompt disponibles. |

### D9 — `controlled-action-engine`

| Campo | Definición |
|---|---|
| ID | D9 |
| Proceso | Limpieza Controlada |
| Responsabilidad única | Ejecutar Archivo o Papelera por lotes sobre un plan aprobado, con revalidación, idempotencia, ledger, fallos parciales, reintento y reversión disponible. |
| Razón para separarlo | Es la frontera destructiva y de mayor riesgo; necesita permisos, auditoría y pruebas de fallos independientes. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | Estudio de Limpieza aceptado; Limpieza Controlada y `gmail.modify` autorizados; D7/D8 integradas; C7 aprobado. |
| Contratos que consume | Plan congelado C6, C7, sesión ampliada en contexto, protecciones y ledger. |
| Resultados que produce | Ejecución auditable por mensaje/lote y estado de reversión; nunca borrado definitivo. |
| Consumidores posteriores | Interfaz de confirmación compuesta por MAIN, D10 e historial global. |
| Permitido | Puertos y adaptadores de acciones, ledger, reintentos y pruebas con dobles; migraciones expresamente delimitadas. |
| Prohibido | Eliminación definitiva, vaciado de Papelera, desuscripción, ejecución sin confirmación, UI y scope global `mail.google.com`. |
| Rama propuesta | `codex/controlled-action-engine` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-controlled-action-engine` |
| Commit base requerido | SHA limpio posterior a aceptación de Estudio y C7. |
| Verificaciones específicas | Revalidación por mensaje, doble ejecución, fallos parciales, reintento, lote pequeño, cambio de protección, Archivo/Papelera/restauración y scopes. |
| Criterios de aceptación | No repite éxitos, nunca actúa fuera del snapshot revalidado, registra cada resultado y detiene contradicciones. |
| Riesgos de integración | Daño real, permisos excesivos, diferencias entre etiquetas de sistema y falsa reversibilidad. |
| Paralelización real | No con cambios de C6/C7 ni con D10; integrar y auditar antes de cualquier consumidor. |
| Condición exacta de desbloqueo | Joa acepta Estudio y autoriza por separado Limpieza Controlada, plan de prueba y `gmail.modify`; MAIN aprueba C7, batería, SHA limpio y prompt. |

### D10 — `rfc8058-one-click`

| Campo | Definición |
|---|---|
| ID | D10 |
| Proceso | Limpieza Controlada |
| Responsabilidad única | Evaluar y enviar, con consentimiento específico, únicamente solicitudes HTTPS one-click compatibles con RFC 8058. |
| Razón para separarlo | Es salida de red hacia terceros, irreversible en algunos proveedores y distinta de modificar etiquetas Gmail. |
| Estado actual | `BLOQUEADA POR AUTORIZACIÓN` |
| Dependencias previas | D9 integrada y auditada; C8 aprobado; evidencia de encabezados y DKIM disponible conforme a C2. |
| Contratos que consume | C2, C8, consentimiento y ledger D9. |
| Resultados que produce | Decisión de elegibilidad explicada y registro de solicitud aceptada/rechazada, nunca garantía de baja. |
| Consumidores posteriores | Historial y presentación de Limpieza Controlada. |
| Permitido | Analizador RFC 8058, cliente HTTPS endurecido, registro y pruebas con servidores locales simulados. |
| Prohibido | GET automático, `mailto:` automático, cookies, autenticación HTTP, redirecciones, credenciales, cuerpos de correo y baja sin consentimiento. |
| Rama propuesta | `codex/rfc8058-one-click` |
| Ruta propuesta | `C:\Users\Joaquin\.codex\worktrees\mailcleanup-rfc8058-one-click` |
| Commit base requerido | SHA limpio posterior a D9 y C8. |
| Verificaciones específicas | HTTPS, cabeceras exactas, cobertura DKIM, consentimiento, no cookies, no redirección, timeout, DNS/host adverso, registro y ausencia de GET/mailto. |
| Criterios de aceptación | Sólo ofrece y ejecuta casos técnicamente elegibles, una vez confirmados, y describe el resultado sin prometer la baja. |
| Riesgos de integración | SSRF, redirecciones, enlaces maliciosos, falsas firmas, pérdida de consentimiento y tratamiento incorrecto del resultado. |
| Paralelización real | No; consume el ledger y la política de ejecución auditada de D9. |
| Condición exacta de desbloqueo | Joa autoriza esta capacidad separadamente; D9 está integrada; MAIN aprueba C2/C8, modelo de amenazas, SHA limpio, batería y prompt. |

## 6. Candidatos originales: decisión de MAIN

| Candidato | Decisión | Justificación |
|---|---|---|
| `classification-domain` | Mantener como D4 `real-classification-domain` | Base Segura ya clasifica; el nuevo alcance concreto es eliminar ayudas sintéticas y operar sobre evidencia real normalizada. |
| `correction-memory` | Fusionar en D5 `local-policy-memory` | Correcciones y protecciones manuales comparten identidad, precedencia, auditoría y persistencia. |
| `protection-engine` | Descartar como worktree autónomo | El motor base ya existe; la ampliación manual pertenece a D5 y las reglas globales quedan en MAIN. |
| `local-persistence` | Mantener como D1 `real-index-persistence` | SQLite base ya existe; el alcance nuevo son índice privado, checkpoints, reanudación y borrado. |
| `cleanup-plans` | Mantener como D7 `real-plan-engine` | El plan simulado ya existe; el alcance nuevo es snapshot real, revalidación y caducidad sin efectos. |
| `source-map-ui` | Mantener como D6 `mapa-total-ui` | La interfaz sintética ya existe; el alcance nuevo son sesión, progreso, mapa real y correcciones. |
| `gmail-readonly` | Dividir en D2 y D3 | Sesión/credenciales e inventario tienen amenazas, contratos y pruebas diferentes. |
| `action-engine` | Mantener como D9 `controlled-action-engine` | Se delimita a Archivo/Papelera; la desuscripción se separa por ser otra red y otra irreversibilidad. |
| `manual-unsubscribe` | Descartar como worktree autónomo | Mostrar GET o `mailto:` es una capacidad pequeña de interfaz; jamás es ejecución automática. D10 cubre sólo RFC 8058. |

## 7. Grafo de dependencias y puertas

```text
MAIN: revisión visual de Base Segura
             ↓
Joa: aceptación de Base Segura
             ↓
Joa: autorización independiente de Mapa Total, Gmail y OAuth
             ↓
MAIN: C1 + C2 + C3 + C4 + C5 para operación real
             ↓
             D2
             ↓
             D3  ←── D1 integrada
             ↓
             D4
             ↓
             D5
             ↓
             D6
             ↓
Joa: aceptación de Mapa Total y autorización de Estudio de Limpieza
             ↓
MAIN: C6, API, fixtures, batería y SHA limpio
             ↓
        D7 ─────→ D8          D8 sólo puede adelantarse con API congelada
             ↓ integración D7, luego D8
Joa: aceptación de Estudio y autorización de Limpieza Controlada
             ↓
MAIN: C7, permiso en contexto, batería y SHA limpio
             ↓
             D9
             ↓ auditoría e integración MAIN
Joa: autorización específica de one-click + MAIN: C8
             ↓
            D10
```

La apertura sintética excepcional de D1 sigue una rama previa y no salta las
puertas del recorrido operativo:

```text
Joa: autorización limitada D-017
             ↓
MAIN: contrato C1/C4 sintético + batería + SHA limpio
             ↓
             D1
             ↓ auditoría e integración MAIN
       espera D2 y autorización real antes de habilitar D3
```

Orden de apertura recomendado: D1, D2, D3, D4, D5, D6, D7, D8, D9 y D10.
El orden expresa consumo real. D1 ya fue integrada localmente. D2 permanece
bloqueada por autorización y no se habilita por esta integración. D8 puede adelantarse con fixtures
solamente si C6 y la API están congelados; su integración siempre espera D7.

## 8. Primer worktree creado e integrado

El primer worktree autorizado fue D1 `real-index-persistence`. Fue verificado
sin red ni credenciales y produce la base consumida por el inventario, pero no
habilita por sí solo ningún dato real.

Estado actual: `INTEGRADA` en el árbol de trabajo de MAIN, con alcance
exclusivamente sintético desde la base
`c3dc210e69e31eb252443d08558e78f756c719d2`. La integración queda fijada por el
commit que contiene este estado.

La condición original se acotó por instrucción explícita de Joa. Para crear D1
se cumplieron:

1. D1 permanece limitada a datos sintéticos por D-017;
2. MAIN aprueba el contrato `INDEX_PERSISTENCE_V1.md`;
3. MAIN ejecuta la batería aplicable;
4. `main` queda limpio en un SHA nuevo y se registra ese hash;
5. MAIN completa un prompt autosuficiente desde
   `docs/prompts/PLANTILLA_DEPENDENCIA.md`;
6. `docs/WORKTREE_REGISTRY.md` registró D1 después de su creación real.

La revisión visual y la autorización de Gmail, OAuth y datos reales siguen
pendientes y no forman parte de D1.

## 9. Protocolo obligatorio de creación e integración

Para cada dependencia:

1. MAIN estabiliza el contrato compartido.
2. MAIN ejecuta la batería correspondiente.
3. MAIN deja un commit limpio y registra su hash.
4. MAIN cambia la dependencia a `LISTA PARA CREAR`.
5. MAIN redacta un prompt autosuficiente con la plantilla vigente.
6. Se crea un único worktree desde el SHA exacto registrado.
7. MAIN registra ruta, rama, base, alcance y estado reales.
8. El especialista verifica ruta, rama, HEAD, base y limpieza antes de editar.
9. El especialista implementa solamente su contrato.
10. El especialista prueba y entrega un handoff verificable.
11. El especialista no integra en `main` ni publica cambios.
12. MAIN inspecciona diff completo y archivos no rastreados.
13. MAIN audita contratos, seguridad, privacidad y alcance.
14. MAIN integra de forma controlada.
15. MAIN repite la batería global.
16. MAIN actualiza plan, registro, decisiones y estado aplicables.
17. Sólo entonces habilita un consumidor.

No se crean por adelantado worktrees bloqueados. Dos dependencias pueden estar
en desarrollo simultáneo sólo cuando consumen contratos congelados, no dependen
entre sí, no compiten por archivos o migraciones y admiten pruebas aisladas.

## 10. Bloqueos materiales no resueltos

| Bloqueo | Afecta | Autoridad necesaria |
|---|---|---|
| Revisión visual y aceptación de Base Segura | D2-D10; permanece pendiente durante D1 sintético por excepción D-017 | Joa |
| Autorización de Mapa Total, Gmail y OAuth | D2-D6; D1 no la consume en su alcance sintético | Joa, por puertas separadas cuando corresponda |
| Metadatos exactos frente a fragmentos, MIME o adjuntos | C1, C2, D3, D4, D10 | MAIN propone; Joa decide privacidad |
| `gmail.metadata` frente a `gmail.readonly` y uso de `q` | C2, D2, D3 | MAIN demuestra necesidad; Joa autoriza el alcance |
| Almacén seguro de credenciales en Windows | C3, D2 | MAIN propone; Joa autoriza arquitectura/privacidad |
| Protección, retención y borrado del índice local | C4, D1 | MAIN propone; Joa decide si cambia el tratamiento de datos |
| Identidad estable de fuente/flujo y migración de correcciones | C1, D4, D5, D7 | MAIN |
| API posterior a v1 sintética | C5 y C6, D3-D8 | MAIN |
| Autorización de Estudio de Limpieza | D7-D8 | Joa |
| Autorización de Limpieza Controlada y `gmail.modify` | D9 | Joa |
| Consentimiento y contrato RFC 8058 | D10 | Joa y MAIN |

## 11. Referencias técnicas a revalidar antes de implementar

- Google, alcances Gmail API:
  `https://developers.google.com/workspace/gmail/api/auth/scopes`.
- Google, `users.messages.get` y `format=METADATA`:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get`.
- Google, `users.messages.list`, paginación, etiquetas y restricción de `q`:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list`.
- Google, sincronización completa/parcial e historial vencido:
  `https://developers.google.com/workspace/gmail/api/guides/sync`.
- IETF, RFC 8058:
  `https://www.rfc-editor.org/rfc/rfc8058.html`.

Estas referencias informan el plan; no constituyen autorización ni reemplazan
la revisión de la documentación vigente al abrir cada dependencia.
