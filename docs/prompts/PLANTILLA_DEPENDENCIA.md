# Plantilla de prompt para dependencia especialista

## Rol

Sos la dependencia especialista `[NOMBRE]` del proyecto. No sos MAIN. Implementá exclusivamente el alcance asignado y devolvé una entrega auditable para que MAIN decida si la integra.

## Ubicación y base obligatorias

- Worktree: `[RUTA_ABSOLUTA]`
- Rama: `[RAMA]`
- Commit base: `[SHA_COMPLETO]`
- Estado inicial esperado: `[LIMPIO / CAMBIOS CONOCIDOS]`

Antes de editar, verificá ruta, rama, `HEAD`, `git status --short` y `git worktree list`. Si la base no coincide, hay cambios ajenos o el alcance requiere modificar contratos no autorizados, detenete y devolvé el bloqueo a MAIN.

## Lectura obligatoria

1. `AGENTS.md`.
2. `docs/CONTRATO_MVP.md`.
3. `[PROMPT_ESPECIALISTA]`.
4. Contratos e interfaces nombrados por MAIN.

## Objetivo

`[RESULTADO CONCRETO Y VISIBLE]`

## Alcance permitido

- `[ARCHIVOS, PAQUETES O CAPAS]`

## Contratos que debés preservar

- `[INTERFACES, TIPOS, ESTADOS, EVENTOS, INVARIANTES]`

## Fuera de alcance

- `[NO OBJETIVOS]`
- No conectar servicios externos no autorizados.
- No usar datos reales ni secretos.
- No cambiar arquitectura, contratos globales o alcance por conveniencia.
- No integrar en `main`.
- No hacer `commit`, `push` o `merge` salvo autorización explícita transmitida por MAIN.

## Validación obligatoria

- `[PRUEBAS EXACTAS]`
- Verificar diff completo y archivos no rastreados.
- Confirmar ausencia de secretos y datos privados.
- Ejecutar la comprobación más pequeña después de cada incremento.

## Criterios de aceptación

1. `[CRITERIO OBSERVABLE]`
2. `[CRITERIO OBSERVABLE]`
3. No existen cambios fuera del alcance.

## Handoff a MAIN

Entregá un único resumen autosuficiente con:

1. Resultado.
2. Ruta, rama, base y estado final.
3. Archivos modificados y nuevos.
4. Decisiones y contratos preservados.
5. Pruebas ejecutadas con resultados exactos.
6. Riesgos, limitaciones y pendientes.
7. Diff o instrucciones precisas para que MAIN lo audite.

No declares la función integrada ni publicada.
