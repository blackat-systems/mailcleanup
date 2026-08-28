# Estado de Base Segura

Fecha del corte: 18 de agosto de 2026.

Estado: aceptada explícitamente por Joa el 18 de agosto de 2026. MAIN completó
el 27 de agosto de 2026 la revisión visual que había quedado pendiente; el fallo
histórico de la herramienta se conserva como antecedente, no como estado actual.
La preparación sintética de Mapa
Total mediante D2, D3, D4 y D5 fue auditada e integrada con dobles o registros
sintéticos, sin abrir OAuth ni conectar datos reales. D5 queda consolidada por
el commit que contiene este estado.

## Qué existe

- una aplicación Python/FastAPI en `src/mailmap`;
- una interfaz React/TypeScript en `frontend`;
- SQLite local con migraciones acumulativas v1-v3;
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
- Cada interfaz futura de Mapa Total deberá repetir su propio recorrido visual;
  la revisión cerrada corresponde únicamente a Base Segura vigente.

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
el frontend todavía no consume C5 y no existe acceso real. C5 fue auditada y
quedó consolidada en `67b00c7`. MAIN consolidó el prompt D6 en `75764c9`, creó
el único worktree autorizado y entregó la implementación de la superficie
frontend de Mapa Total sintético. D6 permanece sin integrar.

La batería global actual pasó con 296 pruebas Python, Ruff, mypy estricto sobre
24 archivos, ESLint, 4 pruebas Vitest y build Vite. El roundtrip DPAPI real pudo
ejecutarse bajo el perfil de usuario actual en una verificación anterior. Este
estado y la autorización D6 no permiten abrir OAuth, usar credenciales, conectar
Gmail real ni persistir metadatos privados.
