# Estado de Base Segura

Fecha del corte: 18 de agosto de 2026.

Estado: aceptada explícitamente por Joa el 18 de agosto de 2026. La aceptación
no convierte en verificada la revisión visual que la herramienta no pudo
completar; ese dato histórico se conserva. Está autorizada la preparación
sintética de Mapa Total mediante D2, D3 y D4. Las tres fueron auditadas e
integradas con dobles o registros sintéticos, sin abrir OAuth ni conectar datos
reales. D4 queda consolidada por el commit que contiene este estado.

## Qué existe

- una aplicación Python/FastAPI en `src/mailmap`;
- una interfaz React/TypeScript en `frontend`;
- SQLite local con una migración inicial;
- 22 mensajes sintéticos y 15 fuentes en el dataset actual;
- vistas de panorama, fuentes, detalle, plan simulado, historial y estado;
- un contrato de API v1 verificado para Base Segura;
- una barrera automática que inspecciona imports, marcadores de capacidad,
  empaquetado y rutas activas.

El prototipo `src/gmail_cleaner`, su configuración y sus dependencias opcionales
fueron retirados del árbol activo. Permanecen recuperables en el historial Git,
pero no se importan, prueban ni empaquetan como parte de Base Segura.

## Verificación repetida por MAIN

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
- recorrido visual: no verificado; durante la consolidación, el servicio de
  control del navegador de Codex volvió a rechazar su propia ruta interna de
  confianza antes de abrir la página.

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

La aplicación activa no contiene importaciones de Google, OAuth, clientes HTTP
externos ni sockets. Sólo se empaqueta `mailmap`; su API crea y revalida planes
locales y responde `canExecute: false`. El servidor se enlaza a `127.0.0.1`.

No hay rutas activas con `oauth`, `gmail`, `execute` o `disconnect`. Los únicos
`POST` son vista previa y revalidación. Los fixtures usan dominios reservados
`.example`; no se solicitaron credenciales ni se conectó una cuenta.

## Riesgos conocidos

- FastAPI/Starlette emite una advertencia de deprecación interna de `TestClient`;
  las pruebas y el recorrido HTTP real pasan. Debe revisarse al actualizar esas
  dependencias, sin agregar paquetes sólo para ocultar el aviso.
- La aplicación todavía no fue empaquetada como ejecutable de Windows; Base Segura
  se inicia como servidor web local.
- La experiencia responsive tiene reglas estructurales y pruebas funcionales,
  pero no se considera visualmente aprobada hasta completar el recorrido real.

## Cierre de Base Segura

- recorrer visualmente Panorama, Fuentes, detalle, Plan y Estado en escritorio;
- repetir el recorrido con un ancho móvil de 390 px;
- corregir cualquier defecto visual encontrado;
- aceptación explícita de Joa: recibida el 18 de agosto de 2026.

Las pruebas funcionales y estructurales están verificadas. La revisión visual
instrumental continúa pendiente como evidencia, aunque Joa aceptó el proceso.
La autorización posterior permitió integrar D2 y D3 con dobles sintéticos. MAIN
amplió la persistencia D1 para que altas, actualizaciones, bajas y checkpoint de
una página sean atómicos y para que un escaneo completo nuevo reemplace de forma
controlada el índice anterior. La integración D4 agrega clasificación pura y
explicable sobre registros normalizados sintéticos, sin consumidor productivo.
MAIN corrigió agrupación entre dominios, validación de baja y confianza de
identidades aisladas. La ampliación pública D4 conservó la proyección semántica
y la batería global pasó con 168 pruebas Python aprobadas;
el roundtrip DPAPI real pudo ejecutarse bajo el perfil de usuario actual. También
aprobaron Ruff, mypy, ESLint, 4 pruebas Vitest y el build Vite. Este estado no
autoriza abrir OAuth, usar credenciales, conectar Gmail real, persistir
metadatos privados ni comenzar D5. MAIN redactó
`LOCAL_POLICY_MEMORY_V1.md`, Joa aprobó el contrato y autorizó la columna
vertebral de descriptores públicos D4. Esa ampliación conserva la semántica de
clasificación y no modifica el estado de privacidad de Base Segura. D5 no tiene
worktree ni implementación y permanece bloqueada hasta una autorización
específica posterior de Joa.
