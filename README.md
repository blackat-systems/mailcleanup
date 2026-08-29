# Mapa y limpieza segura de Gmail

Proyecto local para transformar una casilla de Gmail en un mapa explicable de
fuentes y flujos antes de preparar cualquier limpieza.

## Estado actual

Este repositorio nuevo heredó el historial y un candidato adelantado de Base
Segura, anteriormente denominada Hito 0.
MAIN auditó esa herencia y Joa confirmó el portado selectivo. El resultado
actual es una Base Segura aceptada y un Mapa Total sintético también aceptado:

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
  publicación; queda consolidada por el commit que contiene este estado;

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

El próximo paso requiere una autorización independiente de Joa para preparar
D8. D8 continúa bloqueada y no se crea automáticamente por haber consolidado
D7. Conectar una cuenta real sigue fuera de alcance: exige otra autorización y
resolver antes la protección del índice local.
