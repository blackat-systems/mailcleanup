# Control y limpieza de Gmail

Aplicación local en desarrollo que transforma una casilla de Gmail en un mapa explicable de fuentes y flujos, y permite preparar limpiezas seguras sin revisar mensajes uno por uno. El Hito 0 funciona únicamente con datos sintéticos.

## Estado actual

- La arquitectura del Hito 0 fue confirmada: backend Python, frontend React/TypeScript y SQLite local.
- MAIN implementó una columna vertebral navegable con datos sintéticos; falta la revisión visual de Joa para cerrar la puerta del Hito 0.
- `src/gmail_cleaner` es un prototipo CLI no auditado y no representa la arquitectura aprobada.
- No debe conectarse a una cuenta real ni utilizarse para modificar Gmail.
- No hay credenciales, OAuth ni datos reales autorizados en esta etapa.

## Fuentes de verdad

Leer en este orden:

1. [`AGENTS.md`](AGENTS.md)
2. [`docs/PROMPT_MAESTRO_MAIN.md`](docs/PROMPT_MAESTRO_MAIN.md)
3. [`docs/CONTRATO_MVP.md`](docs/CONTRATO_MVP.md)
4. [`docs/AUDITORIA_PRE_DESARROLLO.md`](docs/AUDITORIA_PRE_DESARROLLO.md)
5. [`docs/ESPECIFICACION_FUNCIONAL.md`](docs/ESPECIFICACION_FUNCIONAL.md), como visión futura

## Organización

La carpeta principal sobre la rama `main` pertenece a MAIN. MAIN construye la columna vertebral del programa, define contratos y audita toda integración.

Los módulos especialistas se desarrollarán más adelante en worktrees separados, cada uno desde un commit base confirmado, con alcance, pruebas y límites propios. Ninguna dependencia se integra por sí misma.

## Arquitectura del Hito 0

- API local Python con FastAPI.
- Dominio y reglas de seguridad en `src/mailmap`.
- SQLite versionado en `data/` (ignorado por Git).
- Frontend React/TypeScript en `frontend/`.
- Fixtures completamente sintéticos; no se renderizan cuerpos ni recursos remotos.

La decisión y sus límites están en [`docs/adr/0001-arquitectura-hito-0.md`](docs/adr/0001-arquitectura-hito-0.md). El contrato compartido de la API está en [`docs/contracts/API_V1.md`](docs/contracts/API_V1.md).

## Uso local

En PowerShell, con Python 3.11+ y pnpm 11 disponibles:

```powershell
.\scripts\setup.ps1
.\scripts\check.ps1
.\scripts\run.ps1
```

Después, abrir `http://127.0.0.1:8765`. El servidor sólo escucha en loopback.

El prototipo anterior sigue conservado en `src/gmail_cleaner` y usa `config.legacy.example.toml`, pero no forma parte del producto aprobado ni debe conectarse a una cuenta real.

## Próximo paso

Completar y verificar el Hito 0 con datos sintéticos. Gmail real permanece fuera de alcance hasta una puerta de aprobación posterior.
