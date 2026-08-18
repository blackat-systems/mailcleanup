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
- Joa aceptó Base Segura; la revisión visual instrumental continúa registrada
  como no verificada;
- D1 de persistencia sintética fue auditada e integrada;
- D2 está en desarrollo en un worktree aislado, con dobles sintéticos y bajo un
  contrato específico;
- abrir OAuth, conectar Gmail, solicitar credenciales y usar datos reales siguen
  prohibidos;
- esta consolidación queda registrada en el commit que contiene este documento.

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

Crear y auditar D2 `secure-gmail-session` con dobles sintéticos. La conexión de
una cuenta real seguirá requiriendo confirmación específica después de integrar
el módulo y revisar su seguridad.
