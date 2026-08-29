# Estado de Base Segura

Fecha del corte: 29 de agosto de 2026.

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
`c8c7b32`. Joa autorizó luego preparar, consolidar y despachar un único worktree
D8 `estudio-ui`. El prompt autosuficiente queda en
`docs/prompts/D8_ESTUDIO_UI.md`; hasta verificar la instancia real, el registro
continúa mostrando únicamente MAIN y D1-D7.

## Qué existe

- una aplicación Python/FastAPI en `src/mailmap`;
- una interfaz React/TypeScript en `frontend`;
- SQLite local con migraciones acumulativas v1-v5;
- un corpus legado de Base Segura y un fixture canónico C5, ambos sintéticos;
- vistas D6 de panorama, fuentes, detalle, correcciones y estado;
- contratos verificados de API v1 para Base Segura y `/api/v2` para Mapa Total;
- un motor sintético D7 de planes congelados, revalidables y cancelables, con
  nueve rutas `/api/v3/study` y `canExecute: false`;
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

La batería global actual pasó con 391 pruebas Python, Ruff, mypy estricto sobre
27 archivos, ESLint, 98 pruebas Vitest y build Vite. El recorrido HTTP local
responde sobre loopback. El recorrido visual inicial de D6 pasó en escritorio y
390 px, sin desborde horizontal ni errores de consola; la pasada minimalista
posterior fue revisada y aceptada por Joa. El roundtrip DPAPI real pudo
ejecutarse bajo el perfil de usuario actual en una verificación anterior. Este
estado y la integración D6 no permiten abrir OAuth, usar credenciales, conectar
Gmail real, persistir metadatos privados ni ejecutar acciones. La autorización
posterior permitió preparar y aceptar C6 sintética, consolidar el prompt D7 e
iniciar su único worktree. D7 fue entregada, auditada e integrada con
correcciones en el árbol de MAIN. Joa autorizó su consolidación y publicación.
El próximo paso autorizado es crear D8 desde el SHA limpio que contiene su
prompt y verificar su Puerta 0. D8 continúa limitada al frontend sintético;
Gmail real, OAuth, credenciales, datos privados, acciones y Limpieza Controlada
permanecen bloqueados.
