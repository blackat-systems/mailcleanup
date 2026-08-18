# Contrato de persistencia del índice v1

Estado: aprobado por MAIN para implementar D1 con datos exclusivamente
sintéticos.

Autoridad: instrucción explícita de Joa del 18 de agosto de 2026 para crear y
trabajar D1 `real-index-persistence`.

Este contrato estabiliza la parte implementable de C1 y C4 necesaria para D1.
No autoriza Mapa Total operativo, Gmail, OAuth, credenciales ni datos reales.

## 1. Objetivo

Agregar una persistencia local, versionada e idempotente para un índice de
metadatos normalizados y para el checkpoint de una futura sincronización.

D1 debe demostrar el comportamiento usando solamente registros sintéticos con
dominios reservados `.example`. La conexión futura con un proveedor queda fuera
de su alcance.

## 2. Frontera con Base Segura

La migración nueva debe convivir con las tablas actuales `messages`, `plans`,
`app_meta` y `schema_migrations`.

- No renombra ni reinterpreta las tablas existentes.
- No cambia los tipos `SyntheticMessage` ni `MessageAssessment`.
- No cambia la API v1, los servicios ni el frontend.
- No altera la siembra ni los resultados canónicos de Base Segura.
- No reduce `canExecute: false` ni la barrera de seguridad.

La persistencia nueva usa tablas con prefijo `indexed_` o `sync_` para evitar
confundir el dataset demostrativo con un futuro índice privado.

## 3. Identidad estable

La clave de una cuenta indexada es `account_key`, un identificador local opaco.
No puede ser una dirección de correo, un token OAuth ni un hash presentado como
anonimización segura.

La identidad de una fila de mensaje es la clave compuesta:

```text
(account_key, provider_message_id)
```

`provider_message_id` y `provider_thread_id` son valores opacos. D1 no deduce de
ellos fuente, flujo, cuenta ni orden temporal.

Los identificadores de fuente y flujo no pertenecen a D1. Serán producidos por
la clasificación posterior y no deben almacenarse como verdad dentro del
registro normalizado.

## 4. Registro normalizado permitido

D1 debe definir un tipo inmutable `IndexedMessageRecord` con estos campos:

| Campo | Tipo | Regla |
|---|---|---|
| `account_key` | `str` | No vacío; opaco; nunca una dirección de correo |
| `provider_message_id` | `str` | No vacío; único dentro de `account_key` |
| `provider_thread_id` | `str` | No vacío |
| `received_at` | `datetime` | Debe incluir zona horaria; se persiste normalizado a UTC |
| `sender_name` | `str \| None` | Encabezado normalizado, puede faltar |
| `sender_address` | `str \| None` | Una dirección normalizada, puede faltar |
| `subject` | `str \| None` | Encabezado, puede faltar |
| `label_ids` | `tuple[str, ...]` | Sin duplicados; orden canónico al persistir |
| `category` | `str \| None` | Categoría normalizada, sin inferencia nueva |
| `size_estimate_bytes` | `int` | Mayor o igual que cero |
| `authenticated_domain` | `str \| None` | Evidencia normalizada, no una conclusión de fuente |
| `list_id` | `str \| None` | Valor normalizado del encabezado |
| `list_unsubscribe` | `str \| None` | Evidencia sintética; no debe ejecutarse ni abrirse |
| `list_unsubscribe_post` | `str \| None` | Evidencia sintética; no demuestra compatibilidad RFC 8058 |
| `dkim_result` | `str \| None` | Valor normalizado: `pass`, `fail`, `neutral` o `unknown` |
| `dmarc_result` | `str \| None` | Valor normalizado: `pass`, `fail`, `neutral` o `unknown` |
| `record_version` | `int` | En v1 debe valer `1` |

La existencia de una columna no autoriza a leerla de Gmail. C2 deberá decidir
por separado qué campos puede recolectar D3 antes de usar datos reales.

## 5. Datos prohibidos

D1 no acepta ni persiste:

- cuerpo de texto o HTML;
- `snippet`;
- estructura o partes MIME;
- contenido, nombre o tipo de adjuntos;
- destinatarios `To`, `Cc` o `Bcc`;
- encabezados arbitrarios fuera de la lista anterior;
- cookies, contraseñas, credenciales, tokens o secretos;
- errores crudos que puedan contener metadatos privados;
- inferencias de fuente, flujo, rubro, intención o protección.

El tipo debe ser cerrado: no se admite un diccionario `extra`, `headers_json` o
`payload_json` que permita eludir esta lista.

## 6. Checkpoint de sincronización

D1 debe definir un tipo inmutable `SyncCheckpoint` con:

| Campo | Tipo | Regla |
|---|---|---|
| `account_key` | `str` | Misma clave opaca del índice |
| `scan_id` | `str` | Identifica un intento lógico |
| `mode` | enum | `full` o `partial` |
| `state` | enum | `not_started`, `running`, `paused`, `completed`, `requires_full_resync` o `failed` |
| `page_token` | `str \| None` | Opaco; no se registra en logs |
| `history_id` | `str \| None` | Opaco; no implica éxito por sí solo |
| `processed_count` | `int` | Mayor o igual que cero |
| `started_at` | `datetime \| None` | Con zona horaria, normalizada a UTC |
| `updated_at` | `datetime` | Con zona horaria, normalizada a UTC |
| `error_code` | `str \| None` | Código controlado, nunca mensaje remoto crudo |

`completed` exige `page_token=None`. `requires_full_resync` descarta el token de
página y conserva solamente el `history_id` que permite explicar el incidente.
D1 no implementa el algoritmo que decide esos estados.

## 7. Esquema mínimo

La siguiente migración disponible debe crear como mínimo:

```text
indexed_accounts
indexed_messages
sync_checkpoints
```

Requisitos:

- claves foráneas activas;
- clave primaria compuesta para mensajes;
- una fila de checkpoint por `account_key`;
- borrado en cascada al eliminar `indexed_accounts`;
- etiquetas serializadas de manera determinista;
- índices para ordenar por fecha y localizar conversación/remitente;
- timestamps persistidos en ISO 8601 UTC;
- ninguna columna genérica capaz de almacenar cuerpos o encabezados extra.

Las migraciones son acumulativas. Una base creada por Base Segura debe avanzar
sin perder mensajes sintéticos ni planes simulados. Una base nueva debe terminar
en el mismo esquema efectivo.

## 8. Operaciones requeridas

El repositorio debe ofrecer operaciones tipadas equivalentes a:

```python
save_index_page(
    account_key: str,
    records: Iterable[IndexedMessageRecord],
    checkpoint: SyncCheckpoint,
) -> None

indexed_messages(account_key: str) -> tuple[IndexedMessageRecord, ...]
indexed_message(account_key: str, provider_message_id: str) -> IndexedMessageRecord | None
sync_checkpoint(account_key: str) -> SyncCheckpoint | None
delete_indexed_messages(account_key: str, provider_message_ids: Iterable[str]) -> int
delete_account_index(account_key: str) -> None
```

`save_index_page` debe ser una única transacción: o se guardan registros y
checkpoint, o no se guarda ninguno. Repetir la misma página no duplica filas.
Una actualización reemplaza los campos permitidos de esa identidad compuesta.

`indexed_messages` ordena por `received_at` descendente y, ante empate, por
`provider_message_id` ascendente.

`delete_account_index` elimina mensajes y checkpoint de esa clave sin afectar
Base Segura ni otras cuentas sintéticas.

Los nombres finales pueden variar sólo si conservan estas semánticas y el prompt
especialista lo explica en el handoff.

## 9. Transacciones y fallos

- Cada operación de escritura usa transacción explícita y rollback ante error.
- Un fallo al persistir el checkpoint revierte también la página de mensajes.
- Un registro inválido falla antes de escribir toda la página.
- Duplicados dentro de una misma entrada se resuelven de forma determinista o
  se rechazan de manera explícita; nunca producen dos filas.
- No se atrapan excepciones para continuar con estado parcial silencioso.

## 10. Privacidad y ubicación

Durante D1 todas las bases son temporales de prueba o se ubican bajo `data/`,
que está ignorado por Git. No se agregan bases al repositorio.

PENDIENTE antes de cualquier dato real: MAIN y Joa deben decidir directorio de
datos por usuario, permisos del sistema operativo, necesidad de cifrado en
reposo, respaldo, retención y borrado verificable. D1 no debe afirmar que el
archivo SQLite resultante ya protege metadatos privados en reposo.

## 11. Compatibilidad y definición de terminado

D1 está terminado para su alcance sintético cuando:

1. una base nueva y una base con migración v1 llegan al mismo esquema;
2. Base Segura conserva exactamente su dataset y sus planes;
3. una página se guarda junto con su checkpoint de forma atómica;
4. reintentar no duplica mensajes;
5. una interrupción puede continuar desde el checkpoint persistido;
6. eliminar una cuenta borra solamente su índice y checkpoint;
7. los tipos rechazan fechas ingenuas, estados inválidos y datos prohibidos;
8. no aparecen Gmail, OAuth, red, credenciales ni datos reales;
9. pasan pruebas específicas, pytest completo, Ruff, mypy y la barrera de
   Base Segura;
10. el especialista entrega diff y handoff sin commit ni integración.

La aceptación de D1 no habilita D2 ni D3 automáticamente. MAIN debe auditarlo,
integrarlo, repetir la batería y resolver los bloqueos de privacidad antes de
habilitar un consumidor.
