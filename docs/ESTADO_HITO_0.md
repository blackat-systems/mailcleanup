# Estado del Hito 0

Fecha del corte: 18 de agosto de 2026.

Estado: candidato funcional implementado; puerta visual y revisión de Joa pendientes.

## Resultado construido

- aplicación web local para Windows servida sólo en `127.0.0.1`;
- backend Python con API versionada;
- frontend React/TypeScript navegable;
- SQLite con migración inicial y dataset versionado;
- 21 mensajes sintéticos agrupados en 15 fuentes sugeridas;
- panorama, fuentes, vistas de Suscripciones y Spam, detalle, plan simulado, historial y estado;
- clasificación multidimensional con evidencias y sin porcentajes inventados;
- protecciones por intención, confianza, hilo y etiquetas;
- vista previa de Papelera, Archivo y baja como decisiones independientes;
- `canExecute: false` incondicional en el Hito 0;
- contrato compartido en `docs/contracts/API_V1.md`.

No se solicitó ni utilizó una cuenta, credencial, token, correo real o servicio externo de IA. No se abrió OAuth y no se implementó ninguna llamada de Gmail.

## Evidencia verificada

La batería `scripts/check.ps1` pasó en el worktree de MAIN:

- 18 pruebas Python;
- Ruff sin hallazgos en la arquitectura del Hito 0;
- mypy estricto sin hallazgos en 8 archivos de `mailmap`;
- ESLint sin hallazgos;
- 4 pruebas Vitest;
- build TypeScript/Vite de producción;
- chequeo de dependencias frontend sin conflictos de pares.

La verificación HTTP local confirmó:

- `GET /api/v1/health`: 200, modo sintético y Gmail desconectado;
- `GET /api/v1/dashboard`: 15 fuentes y cobertura completa de fixtures;
- `GET /`: 200 con el punto de montaje de la interfaz;
- `POST /api/v1/plans/preview`: 201 y `canExecute: false`.

Las pruebas demuestran además:

- misma fuente con varios flujos;
- marcas diferentes en un mismo proveedor de envíos sin fusión incorrecta;
- cambio de dominio de una marca;
- precedencia de seguridad y documentos sobre Promociones;
- baja de un clic sólo como evidencia autenticada;
- newsletter manual;
- suplantación aislada;
- conversación personal protegida;
- hilo de protección mixta;
- estrella, importancia y etiquetas locales;
- frontera civil de Córdoba;
- fallos parciales y reintentos sin duplicación;
- invalidación de un plan por cambio posterior de etiqueta.

## Pendiente comprobable

La inspección visual automatizada en escritorio y móvil estrecho no pudo ejecutarse porque el controlador del navegador integrado rechazó su propia ruta local confiable antes de abrir la aplicación. El servidor, el HTML y los recorridos automatizados sí respondieron correctamente. No se atribuye ese bloqueo al producto y no se declara realizada una inspección que no ocurrió.

Para cerrar el criterio visual, abrir `http://127.0.0.1:8765` y revisar como mínimo:

1. Panorama en ancho de escritorio.
2. Fuentes y filtros de Suscripciones/Spam.
3. Detalle de Nube Clara, incluida la separación de flujos y evidencias.
4. Selección de una fuente y creación de vista previa en Plan.
5. Navegación con ancho móvil menor a 420 px.

## Riesgos conocidos

- FastAPI/Starlette emite una advertencia de deprecación interna sobre `TestClient`; las pruebas pasan y el recorrido HTTP real también. Debe revisarse al actualizar esas dependencias, sin incorporar paquetes experimentales sólo para ocultar el aviso.
- El prototipo `src/gmail_cleaner` sigue conservado como material legado, excluido del lint y sin comando instalado. No es parte del producto aprobado.
- El empaquetado como ejecutable de Windows todavía no fue decidido; el Hito 0 se ejecuta como aplicación web local.

## Puerta siguiente

El Hito 1 no está autorizado. Primero Joa debe revisar la interfaz sintética, pedir los ajustes que correspondan y confirmar expresamente si acepta el Hito 0. Incluso con esa aceptación, cualquier conexión real deberá respetar la puerta específica de OAuth y sólo lectura definida por el contrato.
