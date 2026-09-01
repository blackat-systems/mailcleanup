# Mapa y limpieza segura de Gmail

Proyecto local para transformar una casilla de Gmail en un mapa explicable de
fuentes y flujos antes de preparar cualquier limpieza.

## Estado actual

Este repositorio nuevo heredó el historial y un candidato adelantado de Base
Segura, anteriormente denominada Hito 0.
MAIN auditó esa herencia y Joa confirmó el portado selectivo. El resultado
actual es Base Segura aceptada, con Mapa Total y Estudio de Limpieza aceptados
exclusivamente en modo sintético:

- el dominio, la API, SQLite y el frontend sintéticos pasan la batería local;
- el servidor real fue comprobado en `127.0.0.1:8765`;
- todo plan responde `canExecute: false` y no existe una ruta de ejecución;
- Joa aceptó Base Segura y MAIN completó después su revisión visual instrumental
  en escritorio y 390 px, sin defectos bloqueantes;
- D1 de persistencia sintética y D2 de sesión segura fueron auditadas y
  consolidadas;
- D3 de inventario de sólo metadatos fue auditada e integrada con dobles
  sintéticos; la integración queda consolidada por el commit que contiene este
  estado;
- abrir OAuth, conectar Gmail, solicitar credenciales y usar datos reales siguen
  prohibidos;
- D4 de clasificación sobre registros normalizados fue auditada e integrada en
  MAIN con corpus sintético y sin consumidores productivos; queda consolidada
  en `0fe5111`;
- D5 de memoria local fue auditada e integrada en el árbol de MAIN con comandos
  tipados, historial, undo, reconciliación conservadora, protección acumulativa
  y SQLite v3. MAIN corrigió una regresión para que particionar un flujo nunca
  mejore la confianza automática de D4; queda consolidada por el commit que
  contiene este estado;
- C5 de backend para Mapa Total está auditada, consolidada en `67b00c7` y verde:
  compone D1+D4+D5 desde una fotografía SQLite coherente y expone `/api/v2`
  sólo con el fixture `.example`;
- D6 presenta ese mapa mediante una interfaz sintética, responsive y de jerarquía
  progresiva. Fue auditada, integrada y aceptada por Joa el 28 de agosto de 2026;
- Joa autorizó comenzar Estudio de Limpieza y aceptó C6 después de la auditoría
  de MAIN. El contrato
  define planes congelados, revalidables, cancelables y todavía incapaces de
  ejecutar;
- MAIN preparó, auditó y consolidó `docs/prompts/D7_REAL_PLAN_ENGINE.md` en
  `e92a77a`. Joa autorizó después crear e iniciar D7; el especialista la entregó
  y MAIN la auditó e integró con correcciones. Joa autorizó su commit y
  publicación; quedó consolidada en `c8c7b32`;
- D8 `estudio-ui` fue entregada, auditada, integrada y aceptada por Joa
  exclusivamente en modo sintético. Sus 22 cambios bajo `frontend/src/**`
  consumen la API cerrada `/api/v3/study`, mantienen `canExecute: false` y
  superaron la batería integrada —391 pruebas Python y 335 de frontend—, el
  recorrido HTTP local y la revisión visual en escritorio y 390 px;
- Joa autorizó preparar C7 únicamente como contrato documental, lo aceptó y
  autorizó consolidar esa documentación. `CONTROLLED_EXECUTION_V1.md` define
  confirmación, revalidación por mensaje, Archivo, Papelera, ledger y
  reconciliación, pero no habilita ninguna acción. Quedó publicado en
  `49e2e58`;
- MAIN preparó después C3-A `GMAIL_ACTION_SESSION_V1.md` y C4-P
  `PRIVATE_LOCAL_VAULT_V1.md`. Joa aceptó ambas exclusivamente como contratos
  documentales, con compatibilidad escalonada: Windows 10/11 para la experiencia
  sintética y Windows 11 build 22000 como mínimo inicial para datos y acciones
  reales. La primera define autorización de acción efímera y separada; la
  segunda, una bóveda cifrada por cuenta con verificación local. Quedan
  consolidadas por el commit que contiene este estado y ninguna está
  implementada;
- MAIN preparó el estudio técnico sintético de C4-P en
  `docs/ESTUDIO_TECNICO_C4P.md`. Joa autorizó después sólo la Fase A sin
  dependencias. El inventario y el control negativo confirmaron que SQLite
  estándar deja plaintext sintético en DB, WAL y journal; la comparación de
  cuatro opciones, el harness y el IPC quedaron cerrados documentalmente. MAIN
  auditó la candidata final y Joa aceptó su integración documental. Ningún
  proveedor fue seleccionado. Las Fases B-D no fueron ejecutadas y no se agregó
  ninguna dependencia o capacidad;

El dictamen y la evidencia están en
[`docs/AUDITORIA_HERENCIA_PROYECTO_ANTERIOR.md`](docs/AUDITORIA_HERENCIA_PROYECTO_ANTERIOR.md).

## Fuentes de verdad

Leer en este orden:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/CONTRATO_MVP.md`](docs/CONTRATO_MVP.md)
3. [`docs/AUDITORIA_PRE_DESARROLLO.md`](docs/AUDITORIA_PRE_DESARROLLO.md)
4. [`docs/ESPECIFICACION_FUNCIONAL.md`](docs/ESPECIFICACION_FUNCIONAL.md), sólo como visión futura
5. [`docs/PROMPT_MAESTRO_MAIN.md`](docs/PROMPT_MAESTRO_MAIN.md)
6. [`docs/WORKTREE_REGISTRY.md`](docs/WORKTREE_REGISTRY.md)
7. [`docs/DECISIONES.md`](docs/DECISIONES.md)
8. [`docs/contracts/MAPA_TOTAL_API_V1.md`](docs/contracts/MAPA_TOTAL_API_V1.md), para C5 y D6
9. [`docs/contracts/CLEANUP_PLAN_V1.md`](docs/contracts/CLEANUP_PLAN_V1.md), contrato C6 aceptado
10. [`docs/prompts/D7_REAL_PLAN_ENGINE.md`](docs/prompts/D7_REAL_PLAN_ENGINE.md), delegación D7 consolidada; el worktree fuente se conserva como evidencia
11. [`docs/prompts/D8_ESTUDIO_UI.md`](docs/prompts/D8_ESTUDIO_UI.md), frontera frontend sintética entregada e integrada como D8
12. [`docs/contracts/CONTROLLED_EXECUTION_V1.md`](docs/contracts/CONTROLLED_EXECUTION_V1.md), contrato C7 aceptado sólo documentalmente
13. [`docs/contracts/GMAIL_ACTION_SESSION_V1.md`](docs/contracts/GMAIL_ACTION_SESSION_V1.md), C3-A aceptada sólo documentalmente
14. [`docs/contracts/PRIVATE_LOCAL_VAULT_V1.md`](docs/contracts/PRIVATE_LOCAL_VAULT_V1.md), C4-P aceptada sólo documentalmente
15. [`docs/ESTUDIO_TECNICO_C4P.md`](docs/ESTUDIO_TECNICO_C4P.md), Fase A C4-P ejecutada sin dependencias y Fases B-D bloqueadas

## Organización y arquitectura candidata

La carpeta raíz sobre `main` es el worktree de MAIN. Joa confirmó para Base Segura
la arquitectura Python/FastAPI, React/TypeScript y SQLite local.

`src/mailmap` contiene el producto sintético. El prototipo `gmail_cleaner`, que
incluía capacidades reales de OAuth y modificación, fue retirado del árbol
activo y permanece recuperable únicamente desde el historial Git.

## Preparación y uso local

Requisitos: Windows, Python 3.11 o posterior, Node.js y pnpm 11.

```powershell
.\scripts\setup.ps1
.\scripts\check.ps1
.\scripts\run.ps1
```

El último comando sirve la aplicación en
`http://127.0.0.1:8765`. La base sintética se crea dentro de `data/`, que Git
ignora. Detener el servidor con `Ctrl+C`.

## Próximo paso

C7, C3-A y C4-P están aceptados exclusivamente como documentación. La Fase A
del estudio C4-P está ejecutada, auditada y aceptada, y demuestra que SQLite
estándar no sirve para datos privados; no aprueba un reemplazo. El próximo paso
todavía debe acordarse con Joa. Cualquier B0 o Fase B que seleccione o evalúe un
candidato exacto requiere una autorización nueva. No descargar, incorporar ni
compilar SQLCipher/SEE, implementar, endurecer D2 ni crear D9 sin nuevas autorizaciones.
Gmail real, OAuth, `gmail.modify`, credenciales, datos privados, modificaciones
de mensajes y Limpieza Controlada siguen fuera de alcance. La aceptación
sintética no prueba todavía el comportamiento frente a una bandeja Gmail real.
