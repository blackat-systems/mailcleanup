# Mapa y limpieza segura de Gmail

Proyecto local para transformar una casilla de Gmail en un mapa explicable de
fuentes y flujos antes de preparar cualquier limpieza.

## Estado actual

Este repositorio nuevo heredó el historial y un candidato adelantado de Base
Segura, anteriormente denominada Hito 0.
MAIN auditó esa herencia y Joa confirmó el portado selectivo. El resultado
actual es una Base Segura aceptada y una preparación controlada de Mapa Total:

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
  sólo con el fixture `.example`; Joa autorizó preparar un único worktree D6
  para construir su interfaz sintética;

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

El próximo paso autorizado es crear D6 `mapa-total-ui` desde un SHA limpio que
contenga C5 y su prompt durable, para migrar la interfaz activa a `/api/v2` con
datos de demostración. Conectar una cuenta real continúa fuera de alcance y
requiere otra autorización más resolver la protección del índice local.
