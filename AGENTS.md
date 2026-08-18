## Metodología global de proyectos con MAIN y worktrees

Para proyectos de software no triviales, trabajar por defecto con esta organización:

### PLANIFICACIÓN

- PLANIFICACIÓN define el producto, resuelve decisiones teóricas, delimita hitos y prepara instrucciones para MAIN.
- PLANIFICACIÓN no implementa módulos funcionales ni integra código.
- Las decisiones acordadas deben transferirse a fuentes durables del repositorio.

### MAIN

- MAIN es el director integral del proyecto.
- Conserva visión, contratos compartidos, arquitectura, seguridad, documentación, batería global y estado de integración.
- MAIN construye únicamente la columna vertebral y los cambios transversales que no puedan delegarse de forma segura.
- MAIN no debe absorber personalmente todos los módulos funcionales.
- Antes de delegar, MAIN debe tener contratos estables, un commit base limpio y un prompt especialista autosuficiente.
- MAIN define el orden de dependencias y evita abrir trabajos paralelos que dependan de contratos todavía inestables.

### Dependencias especialistas

- Cada módulo funcional cohesivo e independientemente verificable debe desarrollarse en un chat especialista y un worktree separado.
- Cada chat especialista recibe una sola responsabilidad acotada.
- Antes de editar, verifica ruta, rama, HEAD y estado de Git.
- No modifica arquitectura, contratos compartidos ni alcance sin devolver la decisión a MAIN.
- No integra en `main`.
- No hace commit, push, merge, rebase ni publicación salvo autorización explícita transmitida por MAIN.
- Entrega un handoff con objetivo, cambios, pruebas, riesgos, archivos no rastreados y estado exacto de Git.

### Integración

- Una entrega especialista es evidencia parcial, no integración.
- MAIN inspecciona el diff completo y los archivos no rastreados.
- MAIN comprueba que la entrega respete su contrato.
- MAIN ejecuta las pruebas específicas.
- MAIN integra de forma controlada.
- MAIN repite la batería global desde su propio worktree.
- MAIN actualiza documentación, decisiones y registro de worktrees.
- Ninguna entrega se declara terminada solamente porque el especialista informó que sus pruebas pasaron.

### Continuidad

- El repositorio, Git, los contratos y las pruebas son la fuente de verdad durable.
- No reconstruir decisiones importantes exclusivamente desde conversaciones.
- Cada cierre debe dejar objetivo, cambios, verificaciones, riesgos, pendientes y próximo paso.
- No crear worktrees por tareas mínimas o mecánicas: la separación se aplica a módulos cohesivos cuyo aislamiento reduzca confusión, riesgo o carga de contexto.
----------------------------------------------------------
# Reglas del proyecto

## Idioma y colaboración

- Trabajar y reportar en español claro.
- Liderar con el resultado, la evidencia y el próximo paso.
- Avanzar con autonomía dentro del hito activo y pedir confirmación sólo cuando cambie alcance, arquitectura, permisos externos o riesgo.

## Fuentes de verdad

Leer antes de desarrollar, en este orden:

1. `docs/CONTRATO_MVP.md`.
2. `docs/AUDITORIA_PRE_DESARROLLO.md`.
3. `docs/ESPECIFICACION_FUNCIONAL.md` como visión futura.

El contrato MVP prevalece ante cualquier diferencia. Implementar únicamente el hito autorizado por Joa.

MAIN debe leer además `docs/PROMPT_MAESTRO_MAIN.md` y
`docs/WORKTREE_REGISTRY.md` antes de planificar integraciones o crear una
dependencia.

## MAIN y worktrees especialistas

- La carpeta raíz del proyecto sobre la rama `main` es el worktree de MAIN.
- MAIN conserva visión integral, contratos compartidos, arquitectura, columna vertebral, batería global e integración.
- Un worktree especialista recibe una responsabilidad acotada desde un commit base confirmado.
- Antes de editar, todo especialista debe verificar ruta, rama, `HEAD` y estado de Git.
- Un especialista no cambia contratos compartidos, alcance o arquitectura sin devolver el problema a MAIN.
- Un especialista no integra en `main` ni hace `commit`, `push` o `merge` salvo autorización explícita de Joa transmitida por MAIN.
- Una entrega especialista es evidencia parcial. MAIN inspecciona el diff completo, archivos no rastreados, pruebas y contratos antes de integrar.
- MAIN repite la validación relevante después de integrar; no hereda como prueba suficiente el resultado informado por la dependencia.
- Ningún worktree nuevo se crea hasta que MAIN tenga un commit base limpio y un prompt autosuficiente para esa dependencia.

## Seguridad y privacidad

- No conectar Gmail ni abrir OAuth antes de la puerta de aprobación correspondiente.
- No modificar, archivar, mover, desuscribir ni marcar correos durante Base
  Segura, Mapa Total y Estudio de Limpieza.
- No usar correos reales, nombres privados, credenciales ni tokens en fixtures, pruebas, logs, capturas o commits.
- No renderizar cuerpos HTML ni cargar imágenes o recursos remotos de mensajes.
- No enviar datos de correo a servicios externos de IA durante el MVP.
- No implementar eliminación definitiva.
- Toda futura acción real debe ser revalidada, idempotente, registrable y aprobada.

## Desarrollo

- El prototipo `gmail_cleaner` sólo existe en el historial Git. No reintroducir,
  importar, empaquetar ni instalar código o dependencias de Gmail durante el
  Base Segura.
- Separar evidencia, inferencia, decisión del usuario, plan y ejecución.
- Mantener reglas de precedencia y clasificación en una única fuente lógica.
- Trabajar con datos sintéticos hasta que el contrato habilite expresamente una cuenta real.
- No ampliar el alcance con Outlook, pagos, múltiples cuentas, filtros persistentes ni Guardián en segundo plano.
- Mantener `docs/WORKTREE_REGISTRY.md` actualizado cuando se cree, entregue, integre o descarte un worktree.

## Verificación

- Cada cambio funcional necesita la prueba más pequeña que demuestre su comportamiento.
- Antes de cerrar un hito, ejecutar pruebas, lint, chequeo de tipos, build y recorrido visual aplicables.
- Diferenciar lo verificado, lo inferido y lo pendiente.
- No declarar terminado un hito si falta un criterio de aceptación del contrato.
