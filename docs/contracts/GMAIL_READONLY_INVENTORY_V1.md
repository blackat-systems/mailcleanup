# Contrato de inventario Gmail de sólo lectura v1

Estado: aprobado por MAIN para implementar D3 con transportes y datos sintéticos.

Autoridad: Joa autorizó el 18 de agosto de 2026 preparar D3 después de reforzar
la seguridad. La autorización no alcanza a OAuth real, Gmail real, credenciales,
datos privados ni persistencia real.

Prevalecen también `SECURITY_PRIVACY_V1.md`, `GMAIL_SESSION_V1.md` e
`INDEX_PERSISTENCE_V1.md`. Una contradicción material vuelve a MAIN.

## Responsabilidad única

D3 implementa la orquestación de inventario de una cuenta:

- listar IDs de mensajes con paginación;
- obtener únicamente metadatos autorizados;
- normalizar a `IndexedMessageRecord`;
- persistir cada página junto con su `SyncCheckpoint`;
- reanudar, cancelar y representar errores controlados;
- admitir sincronización completa y parcial mediante `historyId`;
- separar Spam y excluir Enviados, Borradores y Papelera.

D3 no clasifica fuentes o flujos, no modifica Gmail, no expone API o UI y no
implementa un transporte real.

## C1 — registro normalizado

La salida exacta es `IndexedMessageRecord` v1. No se agregan columnas ni campos.
La identidad es `(account_key, provider_message_id)`; `account_key` es opaca y
debe coincidir con la sesión. La fecha se normaliza a UTC y las etiquetas se
canonizan mediante el modelo D1.

## C2 — lectura mínima

Scope único: `gmail.metadata` importado desde `session_model.py`.

Operaciones futuras permitidas, todas `GET`, bajo el origen exacto validado por
`gmail_readonly_policy.py`:

- perfil de `me` para vincular identidad;
- lista de etiquetas;
- lista de mensajes;
- detalle de un mensaje;
- historial desde un `historyId` conocido.

`messages.list` usa `maxResults <= 500`, `pageToken`, `labelIds` e
`includeSpamTrash` cuando corresponda. El parámetro `q` está prohibido.

Cada detalle usa `format=METADATA` y exactamente:

- `From`;
- `Subject`;
- `List-ID`;
- `List-Unsubscribe`;
- `List-Unsubscribe-Post`;
- `Authentication-Results`.

Quedan prohibidos `snippet`, cuerpos, HTML, `raw`, partes MIME, nombres/tipos de
adjuntos, `To`, `Cc`, `Bcc`, `Reply-To`, `Message-ID` y encabezados genéricos.
Si la respuesta simulada contiene campos adicionales, el parser los descarta sin
copiarlos, registrarlos ni exponerlos. Los encabezados autorizados se acotan a
16 KiB cada uno y 64 KiB en conjunto; un exceso produce error controlado.

## C3 — sesión

D3 consume un puerto de sesión ya autenticada e inyectada. No recibe ni
serializa refresh tokens, client secrets, códigos OAuth o verificadores PKCE.
No puede iniciar, refrescar, revocar ni olvidar la sesión.

El transporte es un protocolo inyectable. En D3 sólo existen dobles sintéticos:
no hay `requests`, `httpx`, `urllib.request`, sockets, SDK Google ni navegador.

## C4 — inventario y sincronización

Escaneo completo:

1. listar el conjunto normal sin Spam ni Papelera;
2. inventariar Spam mediante `labelIds=SPAM` e `includeSpamTrash=true`;
3. obtener el detalle `METADATA` antes de persistir;
4. descartar cualquier mensaje con `SENT`, `DRAFT` o `TRASH`;
5. conservar estrella, importancia y demás etiquetas para protección posterior;
6. guardar registros y checkpoint atómicamente con D1.

La presencia simultánea de una etiqueta excluida prevalece aunque el mensaje
también tenga `SPAM` u otra etiqueta.

Escaneo parcial:

- parte del `history_id` consolidado;
- normaliza agregados y cambios de etiquetas;
- elimina del índice IDs borrados o que pasen a una etiqueta excluida;
- si Gmail responde 404 por historia vencida, guarda
  `requires_full_resync` sin mezclar resultados parciales;
- un reintento no duplica registros ni avanza el checkpoint antes de tiempo.

La persistencia real continúa bloqueada porque D1 no cifra metadatos. Las pruebas
usan bases temporales y valores `.example`.

## C5 — interfaz interna

D3 produce modelos cerrados de progreso y resultado para futura composición:

- modo, estado, IDs procesados y checkpoint;
- finalización, cancelación, pausa o necesidad de resincronización completa;
- códigos cerrados de error, nunca texto remoto crudo.

No modifica `API_V1.md`, rutas FastAPI, `oauthAvailable`, `canExecute` ni el
frontend. C5 pública se definirá cuando MAIN componga Mapa Total.

## Reintentos y cancelación

Sólo son transitorios HTTP 429, 500, 502, 503 y 504, además de los códigos
controlados de cuota que el doble represente explícitamente. Máximo cinco
intentos, backoff exponencial truncado con jitter inyectable y tope de 32
segundos. No se reintentan permisos, identidad, validación ni contenido inválido.

La cancelación se consulta antes de cada operación remota simulada y antes de
persistir. Una cancelación deja un checkpoint reanudable y no borra datos ya
consolidados.

## Seguridad observable

- Ningún `repr`, log o excepción contiene tokens, direcciones, asuntos, IDs,
  encabezados, URLs de baja o payloads externos.
- No hay transporte productivo ni ruta pública.
- Sólo se usan fixtures `.example` y IDs obviamente sintéticos.
- Las pruebas bloquean sockets, `urlopen` y navegador.
- `oauthAvailable` y `canExecute` permanecen falsos.
- D4 no queda habilitada por una entrega no auditada.

## Archivos autorizados de D3

- `src/mailmap/gmail_inventory_model.py`;
- `src/mailmap/gmail_inventory.py`;
- `tests/test_gmail_readonly_inventory.py`;
- `tests/test_base_segura_safety.py`, sólo para ampliar barreras.

No modificar repositorio D1, sesión D2, API, frontend, configuración,
dependencias, fixtures canónicos ni documentación. Un defecto contractual en
esas áreas se devuelve a MAIN.

## Definición de terminado

D3 está entregada cuando:

- cumple los recorridos completo, parcial, reanudación, cancelación y 404;
- valida y minimiza cada respuesta antes de persistir;
- excluye Enviados, Borradores y Papelera con precedencia segura;
- inventaría Spam separadamente;
- usa la transacción de D1 sin duplicar;
- no contiene adaptadores de red, OAuth, credenciales ni datos reales;
- pasan pruebas específicas, seguridad, pytest, Ruff, mypy y batería global;
- el diff contiene sólo los cuatro archivos autorizados.

## Referencias oficiales consultadas el 18 de agosto de 2026

- Google OAuth: `https://developers.google.com/identity/protocols/oauth2/resources/best-practices`.
- Google OAuth para apps nativas: `https://developers.google.com/identity/protocols/oauth2/native-app`.
- Scopes Gmail: `https://developers.google.com/workspace/gmail/api/auth/scopes`.
- `messages.list`: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/messages/list`.
- `messages.get`: `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/messages/get`.
- Sincronización: `https://developers.google.com/workspace/gmail/api/guides/sync`.
- Errores y reintentos: `https://developers.google.com/workspace/gmail/api/guides/handle-errors`.
- OAuth Security BCP: `https://www.rfc-editor.org/info/rfc9700`.
- DPAPI: `https://learn.microsoft.com/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata`.
