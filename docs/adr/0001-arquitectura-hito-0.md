# ADR 0001: arquitectura del Hito 0

- Estado: aceptada.
- Fecha: 18 de agosto de 2026.
- Decisor: Joa.
- Alcance: Hito 0, exclusivamente con datos sintéticos.

## Contexto

La experiencia central necesita explorar fuentes, combinar filtros, abrir detalles, seleccionar operaciones y revisar un plan simulado sin perder contexto. El proyecto también debe conservar una separación clara entre evidencia, inferencia, decisión del usuario, plan y futura ejecución.

Se compararon dos alternativas:

1. backend Python con frontend React/TypeScript;
2. backend Python con interfaz renderizada en el servidor.

## Decisión

Adoptar una aplicación web local para Windows con:

- backend Python y API local versionada;
- frontend React con TypeScript;
- SQLite local con migraciones desde la primera versión;
- comunicación únicamente por loopback durante el uso local;
- datos sintéticos en el Hito 0;
- separación explícita entre dominio, persistencia, API y presentación.

## Razones

React/TypeScript agrega un costo inicial de herramientas, pero encaja mejor con la interacción prevista: filtros combinables, selección masiva, vistas previas, estados parciales y navegación de detalle. TypeScript permite verificar el contrato consumido por la interfaz y deja un camino razonable hacia un empaquetado de escritorio futuro.

Una interfaz renderizada en el servidor habría reducido el andamiaje inicial, pero trasladaría complejidad a actualizaciones parciales y estado de selección justamente en el núcleo del producto. No se elige para este hito.

Python conserva el conocimiento aprovechable del prototipo sin convertirlo en arquitectura aprobada. SQLite evita infraestructura externa, permite migraciones auditables y mantiene los datos bajo control local.

## Consecuencias

- MAIN es dueño de los contratos compartidos, la navegación principal, el esquema base y la batería global.
- El frontend no contiene reglas de clasificación ni de seguridad: sólo presenta resultados y decisiones.
- La API expone información sintética en el Hito 0 y no incluye endpoints de OAuth ni Gmail.
- Las futuras acciones reales deberán entrar por una puerta de aprobación nueva y una capa separada, revalidable, idempotente y registrable.
- Ningún worktree especialista se crea hasta que MAIN deje una base limpia, contratos estables y un prompt autosuficiente.

## Límites de esta aceptación

La decisión no autoriza conectar una cuenta, solicitar credenciales, abrir OAuth, enviar desuscripciones, modificar mensajes ni incorporar datos reales. Tampoco decide todavía el mecanismo de empaquetado de escritorio.
