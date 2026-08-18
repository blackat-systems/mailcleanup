# Control y limpieza de Gmail

Proyecto en etapa de diseño y fundamento. La visión es construir una aplicación local que transforme una casilla de Gmail en un mapa explicable de fuentes y flujos, y permita preparar limpiezas seguras sin revisar mensajes uno por uno.

## Estado actual

- El desarrollo del producto todavía no comenzó.
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

## Próximo paso

Confirmar la arquitectura del Hito 0 y desarrollar únicamente una experiencia navegable con datos sintéticos. Gmail real permanece fuera de alcance hasta una puerta de aprobación posterior.
