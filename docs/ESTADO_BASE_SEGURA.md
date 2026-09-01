# Estado de Base Segura

Fecha del corte: 1 de septiembre de 2026.

Estado: aceptada explícitamente por Joa el 18 de agosto de 2026. MAIN completó
el 27 de agosto de 2026 la revisión visual que había quedado pendiente; el fallo
histórico de la herramienta se conserva como antecedente, no como estado actual.
La preparación sintética de Mapa Total mediante D2, D3, D4 y D5 fue auditada e
integrada con dobles o registros sintéticos, sin abrir OAuth ni conectar datos
reales. D5 está consolidada. D6 fue auditada, integrada y aceptada explícitamente
por Joa el 28 de agosto de 2026; quedó consolidada y publicada en `963af89`.
Joa autorizó después comenzar Estudio de Limpieza y preparar C6;
MAIN auditó su contrato, Joa lo aceptó el 29 de agosto de 2026 y quedó
consolidado en `5c913f2`. Joa autorizó después preparar el prompt autosuficiente
D7; quedó auditado y consolidado en `e92a77a`. Joa autorizó después crear e
iniciar el único worktree D7 desde esa base. El especialista entregó el motor
sintético y MAIN lo auditó e integró con correcciones en el árbol de trabajo.
Joa autorizó después su commit y publicación; D7 quedó consolidada en
`c8c7b32`. Joa autorizó luego preparar, consolidar y despachar D8 `estudio-ui`
desde `a1cf0ff`. El especialista entregó sus 22 cambios exclusivamente
frontend; MAIN los auditó, integró y volvió a verificar. Joa aceptó D8 dentro de
su alcance exclusivamente sintético y autorizó su consolidación y publicación
en `main` mediante `3ff29bd`. Estudio de Limpieza queda aceptado en modo
sintético. Joa autorizó después preparar C7 exclusivamente como contrato
documental. MAIN redactó
`CONTROLLED_EXECUTION_V1.md`; Joa lo aceptó y autorizó consolidar únicamente su
documentación. C7 quedó publicado en `49e2e58`. Joa autorizó luego preparar C3-A
`GMAIL_ACTION_SESSION_V1.md` y C4-P `PRIVATE_LOCAL_VAULT_V1.md`. Joa aceptó
ambas exclusivamente como contratos documentales con compatibilidad escalonada
y autorizó consolidarlas y publicarlas. Quedan consolidadas por el commit que
contiene este estado y no son controles implementados. Joa autorizó después
preparar el estudio técnico sintético C4-P y después autorizó sólo su Fase A sin
dependencias. La ejecución aislada en `a0ea` confirmó con canarios sintéticos que
SQLite estándar expone plaintext en DB, WAL y rollback journal, inventarió el
host y completó documentalmente la matriz de distribución, el harness futuro y
el modelo IPC. MAIN auditó la candidata aislada final y Joa aceptó su
integración documental.
B0 y las Fases B-D no fueron ejecutados, no se seleccionó proveedor, no se
agregaron dependencias y no se habilitaron capacidades. D9, Gmail real, OAuth,
`gmail.modify`, credenciales, datos privados y Limpieza Controlada continúan
bloqueados.

## Qué existe

- una aplicación Python/FastAPI en `src/mailmap`;
- una interfaz React/TypeScript en `frontend`;
- SQLite local con migraciones acumulativas v1-v5;
- un corpus legado de Base Segura y un fixture canónico C5, ambos sintéticos;
- vistas D6 de panorama, fuentes, detalle, correcciones y estado;
- contratos verificados de API v1 para Base Segura y `/api/v2` para Mapa Total;
- un motor sintético D7 de planes congelados, revalidables y cancelables, con
  nueve rutas `/api/v3/study` y `canExecute: false`;
- una interfaz D8 de Estudio de Limpieza con historia, constructor, detalle,
  miembros, eventos, revalidación y cancelación sobre `/api/v3/study`, siempre
  sin ejecución y con `canExecute: false`;
- un contrato documental C7 aceptado que define la futura frontera de
  confirmación, ejecución y reversión sin agregar código ni rutas;
- dos contratos documentales C3-A/C4-P aceptados para sesión de acción efímera y
  bóveda privada local; no están implementados;
- un estudio técnico sintético C4-P con Fase A ejecutada sin dependencias: SQLite
  estándar quedó descartada para datos privados y no hay proveedor seleccionado;
- una barrera automática que inspecciona imports, marcadores de capacidad,
  empaquetado y rutas activas.

El prototipo `src/gmail_cleaner`, su configuración y sus dependencias opcionales
fueron retirados del árbol activo. Permanecen recuperables en el historial Git,
pero no se importan, prueban ni empaquetan como parte de Base Segura.

## Verificación histórica de Base Segura

Este bloque conserva la evidencia del corte inicial; la batería vigente, con sus
conteos actuales, se registra al final del documento.

- entorno Python reconstruido desde el proyecto nuevo y paquete editable
  limitado a `mailmap`;
- dependencias frontend reconstruidas desde el lockfile existente;
- 17 pruebas Python: pasaron;
- Ruff sobre `src/mailmap` y `tests`: pasó;
- mypy estricto sobre los ocho archivos de `mailmap`: pasó.
- ESLint: pasó;
- 4 pruebas Vitest: pasaron;
- TypeScript y build de producción Vite: pasaron;
- dataset: 22 mensajes, 15 fuentes y cero casos sintéticos faltantes.
- base local ignorada: modo `synthetic`, 22 remitentes terminados en `.example`
  y cero remitentes fuera de ese dominio de prueba.
- `scripts/check.ps1`: detuvo correctamente cada fase por código de salida y
  terminó con `Batería completa aprobada` y código 0.
- servidor HTTP real en `127.0.0.1:8765`: salud, panorama, configuración,
  frontend, creación y revalidación del plan respondieron correctamente.
- plan HTTP comprobado: 1 mensaje, estado `simulated`, revalidación `valid` y
  `canExecute: false` en ambas respuestas.
- recorrido visual verificado el 27 de agosto de 2026: Panorama, Fuentes,
  detalle de fuente, Estudio de Limpieza y Estado en escritorio y a 390 px;
  navegación, jerarquía, contenido y adaptación responsive sin defectos
  bloqueantes ni errores de consola observados.

## Correcciones de la herencia

- `scripts/check.ps1` y `scripts/setup.ps1` ahora comprueban explícitamente cada
  código de salida nativo;
- `.venv` y `frontend/node_modules` trasladados fueron eliminados y regenerados;
- el cache `.pnpm-store` creado durante una instalación fallida fue eliminado;
- después de verificar la batería, se retiraron del árbol de trabajo los
  entornos, cachés, bases sintéticas y resultados de build regenerables;
- `SENT`, `DRAFT` y `TRASH` ahora aparecen junto con las etiquetas configuradas
  en la explicación visible de protecciones;
- se deshabilitó la redirección OAuth auxiliar de Swagger;
- se agregó una prueba de seguridad que impide reintroducir silenciosamente las
  capacidades retiradas y fija el servidor a loopback.

## Seguridad observada

El paquete contiene modelos y orquestadores D2/D3 ejercitados únicamente con
dobles sintéticos, pero no contiene un cliente productivo de Google/Gmail ni una
ruta activa para abrir OAuth o red externa. La API local responde
`canExecute: false` y el servidor se enlaza a `127.0.0.1`.

No hay rutas activas para conectar, sincronizar una cuenta real, ejecutar o
desconectar Gmail. Los `POST` existentes son la vista previa y revalidación
legadas de Base Segura, más decisiones locales D5 y su undo bajo `/api/v2`; no
modifican mensajes. Los fixtures usan dominios reservados `.example`; no se
solicitaron credenciales ni se conectó una cuenta.

## Riesgos conocidos

- FastAPI/Starlette emite una advertencia de deprecación interna de `TestClient`;
  las pruebas y el recorrido HTTP real pasan. Debe revisarse al actualizar esas
  dependencias, sin agregar paquetes sólo para ocultar el aviso.
- En la validación C6 del 28 de agosto de 2026 pytest no pudo actualizar su caché
  ignorada `.pytest_cache` por permisos del directorio. Las 296 pruebas pasaron;
  MAIN no cambió permisos ni trató la caché como evidencia funcional.
- La aplicación todavía no fue empaquetada como ejecutable de Windows; Base Segura
  se inicia como servidor web local.
- D6 completó su recorrido visual inicial, recibió una pasada minimalista y fue
  aceptada explícitamente por Joa el 28 de agosto de 2026.
- D7 valida la integridad global del ledger mediante agregados SQL en cada página.
  No hidrata filas fuera de la página y los miembros están acotados a 100.000,
  pero un recorrido completo repite ese costo. Es una optimización futura, no un
  defecto contractual ni una razón para debilitar la detección de corrupción.
- D8 y la batería sintética no demuestran todavía el comportamiento frente a
  una bandeja Gmail real, sus volúmenes, latencias, cuotas o mensajes anómalos.
  Esa validación requiere otra autorización y una prueba controlada de sólo
  lectura; no forma parte de esta aceptación.
- La sesión y la línea base vigentes admiten sólo `gmail.metadata`. C7 reserva
  `gmail.modify` para una futura capacidad separada, pero exige una ampliación
  versionada antes de D9; no puede reutilizarse D2 cambiando su constante o
  relajando sus barreras.
- Google no admite autorización incremental para clientes instalados y una
  revocación afecta los grants del proyecto OAuth, no sólo un archivo o cliente
  local. C3-A define autorización contextual, proyecto de acción separado y
  token de acción efímero; está aceptada documentalmente y no implementada.
- Índice, planes y futuro ledger todavía carecen de la implementación auditada
  de ubicación privada, ACL, cifrado autenticado, retención y autenticación
  local definidas por C4-P. Loopback por sí solo no resuelve ese riesgo.
- C4-P define base cifrada separada, DEK por cuenta protegida con DPAPI, ACL y
  Windows Hello mediante un futuro broker nativo. La Fase A descartó SQLite
  estándar, comparó cuatro opciones y no seleccionó ninguna. El contrato C4-P
  sólo recomienda evaluar primero la familia SQLCipher 4 Community; versión,
  artefacto y proveedor permanecen pendientes. No hubo build, binding, cifrado,
  DPAPI, Windows Hello ni broker real.
- La sesión real de lectura D2 también necesita endurecimiento antes de OAuth:
  retirar `include_granted_scopes`, ligar su refresh token mediante DPoP y
  verificar known folder, DACL y reparse points del almacén. C4-P no almacena
  credenciales ni resuelve ese trabajo por sí sola.
- La compatibilidad escalonada aceptada mantiene Windows 10/11 como objetivo
  sintético y exige Windows 11 build 22000 para datos y acciones reales hasta
  que Joa acepte una alternativa equivalente.

## Cierre de Base Segura

- recorrido visual de Panorama, Fuentes, detalle, Plan y Estado en escritorio:
  completado el 27 de agosto de 2026;
- recorrido con un ancho móvil de 390 px: completado el 27 de agosto de 2026;
- defectos visuales bloqueantes encontrados: ninguno;
- aceptación explícita de Joa: recibida el 18 de agosto de 2026.

Las pruebas funcionales, estructurales y la revisión visual instrumental de
Base Segura están verificadas. Joa aceptó el proceso previamente.
La autorización posterior permitió integrar D2 y D3 con dobles sintéticos. MAIN
amplió la persistencia D1 para que altas, actualizaciones, bajas y checkpoint de
una página sean atómicos y para que un escaneo completo nuevo reemplace de forma
controlada el índice anterior. La integración D4 agrega clasificación pura y
explicable sobre registros normalizados sintéticos, sin consumidor productivo.
MAIN corrigió agrupación entre dominios, validación de baja y confianza de
identidades aisladas. D5 agrega memoria local tipada, historial append-only,
undo lógico, reconciliación conservadora, protección acumulativa y migración
SQLite v3 sin crear cuentas ni consumidores productivos. Durante la auditoría,
MAIN corrigió que una partición pudiera mejorar la confianza automática de un
flujo D4 y agregó la regresión correspondiente.

MAIN implementó después C5 para Mapa Total: una fotografía SQLite
coherente que incluye índice y políticas, composición determinista D4+D5, un
fixture canónico `.example`, una puerta sintética revalidada dentro de cada
escritura y nueve rutas cerradas bajo `/api/v2`. `/api/v1` permanece compatible,
el frontend D6 consume C5 y no existe acceso real. C5 fue auditada y quedó
consolidada en `67b00c7`. MAIN consolidó el prompt D6 en `75764c9`, creó el único
worktree autorizado y auditó su entrega. La integración en el árbol de MAIN fue
aprobada con siete correcciones comprobadas de seguridad, contrato, privacidad y
accesibilidad. A pedido de Joa, MAIN aplicó luego una pasada minimalista que
reduce la navegación primaria y pliega filtros, evidencia y diagnósticos
secundarios, preservando advertencias y correcciones. D6 fue aceptada por Joa y
quedó consolidada y publicada en `963af89`.

La batería global integrada pasó con 391 pruebas Python, Ruff, mypy estricto
sobre 27 archivos, ESLint, 335 pruebas Vitest en 11 archivos y build Vite de 43
módulos. El recorrido HTTP local confirmó salud sintética, Gmail desconectado,
`cleanupPlan: false` en v2, `canExecute: false` y `Cache-Control: no-store` en
v3, sin CORS y con Host y Origin ajenos rechazados. MAIN recorrió D8 en
escritorio y 390 px: historia, constructor de cinco etapas y detalle; no hubo
desborde horizontal, el menú móvil midió 44 por 44 px, aisló el contenido al
abrirse, cerró con Escape y devolvió el foco. La consola no registró warnings ni
errores y los únicos recursos declarados fueron JS y CSS relativos del build
local. El roundtrip DPAPI real pudo ejecutarse bajo el perfil de usuario actual
en una verificación anterior.

D8 fue auditada, integrada y aceptada por Joa exclusivamente en modo sintético.
C7 fue preparado, aceptado, consolidado y publicado exclusivamente como contrato
documental. C3-A y C4-P fueron aceptadas después con compatibilidad escalonada y
autorización de consolidación/publicación. La Fase A del estudio C4-P quedó
ejecutada, auditada y aceptada sin dependencias; las Fases B-D siguen sin
ejecutar. Ninguna de esas
decisiones autoriza crear D9, ampliar sesión o seguridad en código, agregar
dependencias, solicitar `gmail.modify` ni comenzar Limpieza Controlada. Gmail
real, OAuth, credenciales, datos privados y acciones continúan bloqueados.
