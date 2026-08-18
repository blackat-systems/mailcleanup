# Registro de worktrees

Este archivo es la fuente durable de coordinación. No reemplaza `git worktree list`; ambos deben coincidir.

## MAIN

| Campo | Estado |
|---|---|
| Rol | Dueño integral, columna vertebral, auditoría e integración |
| Ruta | `C:\Users\Joaquin\Desktop\chatgptprojects\limpiar_mails` |
| Rama | `main` |
| Commit base | Pendiente del primer commit |
| Hito autorizado | Preparación documental previa al Hito 0 |
| Gmail real | Prohibido |
| Estado | Preparando repositorio y arquitectura |

## Dependencias planificadas

Todavía no se creó ningún worktree especialista. Los nombres son orientativos y MAIN debe confirmar contratos antes de crearlos.

| Orden | Dependencia posible | Responsabilidad acotada | Estado |
|---:|---|---|---|
| 1 | `classification-domain` | Evidencias, taxonomía, precedencia y fixtures | Espera columna vertebral |
| 2 | `source-map-ui` | Explorador y detalle sobre contratos estables | Espera columna vertebral |
| 3 | `local-persistence` | SQLite, migraciones y reanudación local | Espera arquitectura |
| 4 | `gmail-readonly` | Adaptador OAuth y metadatos del Hito 1 | Fuera del Hito 0 |
| 5 | `action-engine` | Planes, revalidación, Papelera y Archivo | Fuera del Hito 0 |
| 6 | `unsubscribe-security` | Baja RFC 8058 e idempotencia | Fuera del Hito 0 |
| 7 | `qa-security` | Auditoría transversal y pruebas de aceptación | Se define por hito |

## Reglas de actualización

Al crear un worktree, registrar:

- nombre canónico;
- ruta absoluta;
- rama;
- commit base;
- prompt asignado;
- alcance;
- estado de Git inicial.

Al recibir una entrega, registrar pruebas, riesgos y ubicación del diff. Al integrar, registrar commit de MAIN y repetir validación. Un worktree retirado debe marcarse como retirado; no se reutiliza silenciosamente para otro alcance.
