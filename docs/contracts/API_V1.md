# Contrato de API local v1

Estado: contrato estable y verificado de Base Segura, aceptada por Joa. Su
recorrido visual posterior también fue completado en escritorio y 390 px.

Base: `http://127.0.0.1:8765/api/v1`.

La API candidata se enlaza únicamente a loopback y expone datos sintéticos. No
existen rutas de OAuth, Gmail, baja ni modificación de mensajes dentro de
`src/mailmap`. El prototipo legado con capacidades reales fue retirado del árbol
activo y permanece solamente en el historial Git.

## Lecturas

| Método | Ruta | Resultado |
|---|---|---|
| `GET` | `/health` | versión, modo y conexión bloqueada |
| `GET` | `/dashboard` | totales, rubros, cobertura y mayores fuentes |
| `GET` | `/analysis` | fases e incidencias sintéticas de ingesta |
| `GET` | `/sources` | fuentes; acepta `view`, `query` y `rubro` |
| `GET` | `/sources/{source_id}` | identidad, flujos, evidencias y muestra de metadatos |
| `GET` | `/history` | planes simulados guardados localmente |
| `GET` | `/configuration` | plataforma, zona civil y capacidades bloqueadas |

`view` acepta `all`, `subscriptions`, `spam` y `protected`. Suscripciones y Spam son filtros sobre las mismas fuentes, no inventarios paralelos.

## Plan simulado

`POST /plans/preview` recibe:

```json
{
  "sourceIds": ["src-diario-horizonte"],
  "beforeDate": "2026-07-31",
  "keepLatest": 1,
  "operations": ["archive", "unsubscribe"]
}
```

La fecha se interpreta como fecha civil inclusiva en `America/Argentina/Cordoba`. Las operaciones permitidas son `trash`, `archive` y `unsubscribe`, siempre como intenciones independientes y simuladas. La respuesta tiene `canExecute: false` incondicional.

`POST /plans/{plan_id}/revalidate` compara IDs y revisiones actuales con la vista previa. Un cambio de etiqueta vuelve obsoleto el elemento afectado. La ruta tampoco ejecuta efectos.

No existe una ruta de ejecución. Los únicos `POST` habilitados durante Base Segura
son la creación de la vista previa y su revalidación.

## Reglas para dependencias futuras

- No duplicar en el frontend las reglas de identidad, clasificación, precedencia o protección.
- No ampliar este contrato con datos privados durante Base Segura.
- Un cambio incompatible requiere una nueva versión y auditoría de MAIN.
- Mapa Total usa el contrato separado `MAPA_TOTAL_API_V1.md` bajo `/api/v2`;
  no reinterpreta estas respuestas.
- C6 fue aceptado y D7 implementó Estudio de Limpieza bajo el prefijo separado
  `/api/v3/study`; no amplía la tabla ni las rutas de planes v1 y mantiene
  `canExecute: false`.
- Las futuras acciones reales deben usar rutas y modelos separados, con revalidación, idempotencia y registro durable.
- C7 está aceptado sólo como contrato documental en
  `CONTROLLED_EXECUTION_V1.md`. No existe una ruta `/api/v4/control` ni
  autorización para implementarla.
