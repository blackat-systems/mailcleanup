# Contrato de Limpieza Controlada v1

Estado: `ACEPTADO POR JOA` el 31 de agosto de 2026. La autorización vigente
permite consolidar únicamente esta documentación.

Autoridad: `CONTRATO_MVP.md`, `SECURITY_PRIVACY_V1.md`,
`GMAIL_SESSION_V1.md`, `GMAIL_READONLY_INVENTORY_V1.md`,
`INDEX_PERSISTENCE_V1.md`, `CLEANUP_PLAN_V1.md` y las autorizaciones de Joa del
31 de agosto de 2026 para preparar, aceptar y consolidar C7 exclusivamente como
contrato documental.

La aceptación estabiliza las decisiones documentales de C7. No autoriza
implementación, D9, un worktree, OAuth, `gmail.modify`, Gmail real, credenciales,
datos privados, red externa, modificación de mensajes, push, publicación ni
despliegue. Todas las capacidades activas continúan con `canExecute: false`.

## 1. Objetivo y frontera

C7 define cómo una futura Limpieza Controlada podría consumir un plan C6 exacto
y producir únicamente Archivo o Papelera con confirmación, revalidación por
mensaje, registro durable e idempotencia local.

```text
plan C6 vigente y revalidado
             ↓
 manifiesto exacto sin IDs futuros
             ↓
 aprobación única y contextual de Joa
             ↓
 intención local durable por mensaje
             ↓
 mutación Gmail individual y acotada
             ↓
 verificación, ledger y reconciliación
```

C7 no cambia `CLEANUP_PLAN_V1.md` ni agrega estados de ejecución a C6. El plan,
la aprobación, la ejecución, los intentos y la reversión son agregados separados.
`/api/v3/study` permanece incapaz de ejecutar.

Quedan fuera de C7:

- desuscripción manual o automática, que pertenece a C8/D10;
- acciones por hilo, búsquedas Gmail o selectores abiertos;
- spam, bloqueo, filtros persistentes y reglas automáticas;
- envío, borradores, composición y configuración de Gmail;
- eliminación definitiva y vaciado de Papelera;
- procesos en segundo plano con la aplicación cerrada;
- ejecución sobre más de una cuenta;
- cuerpos, HTML, `snippet`, MIME, adjuntos y destinatarios.

## 2. Estado contractual y puertas independientes

La aceptación de este documento estabiliza C7. No autoriza por sí sola D9 ni una
ejecución real.

La primera condición ya está cumplida: C7 fue aceptado por Joa. Antes de crear
siquiera un worktree D9 todavía deben cumplirse:

1. autorización separada para preparar D9, inicialmente sólo con dobles
   sintéticos;
2. ampliación versionada de sesión y seguridad para `gmail.modify`;
3. contrato y prompt autosuficiente de D9;
4. batería global verde y SHA limpio de MAIN.

Antes de cualquier adaptador o prueba con Gmail real se agregan, conjuntamente:

1. autorización específica de Joa para abrir OAuth y conectar una cuenta;
2. credencial de aplicación de escritorio fuera de Git;
3. verificación de identidad y cuenta exactas;
4. almacenamiento privado por usuario, ACL restrictiva y cifrado autenticado
   del índice, planes y ledger, con clave protegida por DPAPI;
5. retención, respaldo y borrado verificable aprobados;
6. autenticación local más fuerte que confiar sólo en loopback;
7. adaptadores productivos de OAuth, lectura y escritura auditados;
8. requisitos aplicables de verificación de Google resueltos;
9. autorización separada de Limpieza Controlada;
10. plan real creado y revisado sobre un inventario completo;
11. lote piloto exacto aprobado por Joa.

Una puerta satisfecha no reemplaza ninguna de las demás.

## 3. Relación con seguridad y sesión vigentes

`GMAIL_SESSION_V1.md` y `SECURITY_PRIVACY_V1.md` permiten hoy únicamente
`gmail.metadata` y lectura. D2 rechaza otros permisos. C7 no modifica esa verdad.

Antes de D9 debe existir una extensión versionada y aceptada que:

- modele una credencial de acción separada de la credencial de sólo metadatos;
- solicite consentimiento incremental y contextual;
- preserve PKCE S256, `state` de un solo uso, callback exacto en
  `127.0.0.1` y DPAPI de usuario;
- verifique que la identidad y `account_key` coinciden con el plan;
- valide el conjunto exacto de permisos al restaurar y renovar;
- permita retirar u olvidar la capacidad de modificación conscientemente;
- no promueva ni reescriba en silencio una sesión D2 existente;
- explique que la revocación remota de Google puede no aislarse de otras
  credenciales concedidas al mismo cliente.

La futura implementación no puede hacer pasar C7 cambiando la constante actual
de D2 ni relajando sus pruebas negativas.

## 4. Permiso mínimo y allowlist Gmail

La única capacidad OAuth definida para una futura ejecución C7 es:

```text
https://www.googleapis.com/auth/gmail.modify
```

Es un scope restringido y más poderoso que las acciones del producto. Por eso el
scope no constituye una allowlist de operaciones. El adaptador futuro debe
negar por defecto todo salvo:

| Propósito | Método Gmail admitido |
|---|---|
| comprobar cuenta | `users.getProfile(userId="me", fields="emailAddress")` |
| revalidar o reconciliar | `users.messages.get(userId="me", format="minimal", fields="id,labelIds,historyId")` o la frontera `METADATA` cerrada de D3 |
| archivar | `users.messages.modify`, quitando sólo `INBOX`, con `fields="id,labelIds,historyId"` |
| revertir Archivo | `users.messages.modify`, agregando sólo `INBOX`, con la misma máscara |
| mover a Papelera | `users.messages.trash`, con `fields="id,labelIds,historyId"` |
| retirar de Papelera | `users.messages.untrash`, con la misma máscara |

Quedan prohibidos `https://mail.google.com/`, `gmail.compose`, `gmail.send`,
`gmail.insert`, `gmail.settings.*`, cuentas de servicio, delegación de dominio,
`messages.delete`, `messages.batchDelete`, mutaciones por hilo y toda URL,
método, query, cuerpo o etiqueta que el consumidor pueda ampliar.

Las máscaras `fields` anteriores son parte de la allowlist de transporte, no
sólo un filtro del decoder. Una respuesta con campos adicionales se descarta y
se trata como violación controlada; nunca se copia al ledger o a un error.

C7 v1 tampoco admite `messages.batchModify`: acepta hasta 1.000 IDs pero devuelve
un cuerpo vacío y Google no documenta atomicidad, rollback ni resultado por ID.
La primera implementación prioriza atribución y reconciliación por mensaje.

El adaptador no acepta IDs de etiquetas arbitrarios. Para Archivo sólo puede
construir `removeLabelIds=["INBOX"]`; para su reversión sólo
`addLabelIds=["INBOX"]`. Los campos de Classification Labels quedan fuera.

## 5. Condiciones de un plan ejecutable

Una preparación C7 operativa o real falla de manera cerrada salvo que:

- el plan C6 exista y pertenezca a la cuenta autenticada;
- su estado efectivo sea `frozen` o `reduced`;
- no esté vencido, cancelado ni invalidado;
- `currentEligibleCount` sea mayor que cero;
- su disposición sea exactamente `archive` o `trash`;
- el checkpoint sea `completed` y el mapa no sea parcial;
- plan, mapa y políticas coincidan con las revisiones esperadas;
- la fotografía use datos reales protegidos bajo las puertas de la sección 2;
- no exista sincronización o ejecución incompatible para esa cuenta;
- ese plan no haya originado ya otra ejecución.

La preparación ordena una revalidación C6 nueva dentro de la misma coordinación
serializada. No puede basarse solamente en la revisión vista por el navegador.

Una futura implementación D9 con dobles tiene una puerta distinta y explícita:
usa exclusivamente cuenta, fixtures y transportes sintéticos, no abre OAuth ni
red y no expone `canExecute: true` en la aplicación activa. Puede ejercitar las
invariantes anteriores sustituyendo sólo las puertas de cuenta y almacenamiento
real por equivalentes sintéticos declarados. Nunca presenta ese modo como una
preparación ejecutable sobre Gmail.

## 6. Manifiesto aprobado

C7 materializa un manifiesto inmutable separado de la selección original. Debe
contener como mínimo:

```text
contractVersion
executionId local opaco
accountKey interna
planId
planRevision
mapRevision
policyRevision
disposition
createdAt
approvalExpiresAt
eligibleCount
estimatedBytes
manifestDigest
miembros exactos en orden canónico
```

Cada miembro conserva internamente su `provider_message_id`, el ID local público,
las precondiciones de elegibilidad y una huella canónica de los metadatos
permitidos. El navegador nunca envía, reconstruye ni recibe IDs remotos.

El conjunto del manifiesto sólo puede ser igual o menor que la selección C6
vigente. Nunca incorpora mensajes nuevos, inicialmente excluidos, retirados o
recibidos después de la creación del plan.

La huella SHA-256 cubre versión, cuenta, plan, revisiones, disposición, orden y
miembros. Cambiar cualquier elemento invalida la aprobación.

## 7. Aprobación y confirmación

La aprobación es un consentimiento de un solo uso ligado al manifiesto exacto.
No es una propiedad reutilizable del plan, una fuente ni una cuenta.

Antes de confirmar, la interfaz debe mostrar:

- acción exacta: Archivo o Papelera;
- cantidad exacta y tamaño estimado, sin llamarlo espacio liberado;
- período, fuentes, flujos, ejemplos y exclusiones;
- revisión y hora de la última revalidación;
- advertencia de que cambios posteriores pueden producir omisiones;
- para Papelera, reversibilidad temporal y no garantizada;
- alcance del lote piloto si corresponde.

La aprobación vence diez minutos después de preparada y nunca después del
`expiresAt` C6. Si no comenzó en ese intervalo, cambia una revisión, la cuenta,
la disposición o el manifiesto, debe prepararse y mostrarse otra vez.

El backend entrega un desafío aleatorio de un solo uso, ligado a la huella y
nunca incluido en una URL o log. El cliente devuelve sólo IDs locales, revisión,
desafío y confirmación. La prueba de presencia del desafío no reemplaza la futura
autenticación del proceso local.

## 8. Lote piloto y lotes ordinarios

La primera ejecución real por cuenta y versión de aplicación queda limitada a:

- una sola disposición;
- hasta 10 mensajes elegidos conscientemente por Joa dentro del manifiesto;
- operaciones remotas individuales y secuenciales;
- detención obligatoria al terminar el piloto;
- reconciliación del índice y revisión de resultados antes de continuar.

No existe un valor por defecto que amplíe el piloto. Joa puede elegir menos, no
más. Continuar con el resto requiere otra autorización específica posterior al
informe del piloto. Esa autorización continúa la misma `executionId`, el mismo
plan y el mismo manifiesto; habilita otro lote, no crea una segunda ejecución ni
amplía el conjunto aprobado.

Después de aceptar el piloto, un lote lógico ordinario contiene como máximo 50
mensajes. El límite organiza checkpoints y revisión; no habilita
`messages.batchModify` ni llamadas paralelas. La aplicación abierta procesa un
mensaje por vez y comprueba cancelación antes de cada lectura, intención y
mutación.

## 9. Revalidación en dos capas

La aprobación de avance exige una revalidación local C6 completa.
Inmediatamente antes de cada mutación, incluida una reversión, se repite además
una revalidación remota y local del mensaje.

Toda mutación debe comprobar:

1. sesión de acción vigente y cuenta exacta;
2. permiso exacto `gmail.modify`;
3. pertenencia al manifiesto de avance o reversión correspondiente;
4. existencia e identidad remota;
5. etiquetas actuales permitidas;
6. ausencia de otra operación concurrente sobre el mensaje;
7. que el delta propuesto todavía sea seguro y necesario.

Una mutación de avance exige además:

- plan todavía `frozen` o `reduced`, no vencido ni cancelado;
- ausencia de un éxito previo de avance;
- ausencia de `SENT`, `DRAFT`, `SPAM`, `STARRED` e `IMPORTANT`;
- filtros temporales, lectura y etiquetas excluidas originales;
- protección automática y manual actual;
- ausencia de contradicción o binding que requiera revisión;
- pertenencia conservadora a la misma fuente y flujo cuando sea necesaria.

Una reversión exige, en cambio:

- éxito original atribuido y verificado de MailCleanup;
- ausencia de una reversión exitosa previa;
- consentimiento separado y manifiesto de reversión vigente;
- ausencia de un cambio externo que volvería inseguro reponer el delta.

El plan original puede estar vencido o cancelado para reconciliar o revertir.
Eso nunca rehabilita acciones de avance.

La precondición `TRASH` depende de la acción:

- Archivo, Papelera y reversión de Archivo exigen `TRASH` ausente;
- reversión de Papelera mediante `untrash` exige `TRASH` presente;
- cualquier otra combinación se omite como estado cambiado o no reversible.

La lectura remota usa `minimal` cuando alcanzan ID y etiquetas; si necesita
cabeceras para reconstruir una protección, usa sólo la allowlist `METADATA` de
D3. Nunca escala a cuerpo o encabezados abiertos.

Si falta información para demostrar seguridad, el mensaje se omite. Una nueva
protección nunca se atraviesa y no existe override C7 v1.

Si cambia `policyRevision`, `mapRevision`, la semántica de un objetivo o el plan
durante una ejecución, se detienen nuevas mutaciones hasta revalidar y volver a
mostrar el alcance. Los éxitos anteriores no se revierten automáticamente.

## 10. Semántica de Archivo

Archivo significa exclusivamente remover la etiqueta de sistema `INBOX` de un
mensaje individual.

- No reemplaza el conjunto completo de etiquetas.
- No modifica lectura, estrella, importancia, Spam ni etiquetas del usuario.
- No opera sobre todo el hilo.
- Si `INBOX` ya estaba ausente antes del primer intento, se registra
  `already_desired_external`; MailCleanup no se atribuye ese cambio.
- Un éxito requiere respuesta válida y lectura posterior con `INBOX` ausente.

Revertir Archivo es otro comando confirmado que agrega únicamente `INBOX`, sólo
si la revalidación demuestra que MailCleanup la quitó, el mensaje existe y no
hubo un cambio posterior incompatible.

## 11. Semántica de Papelera

Papelera usa exclusivamente `users.messages.trash` sobre un mensaje individual.

- Nunca usa eliminación definitiva.
- Nunca vacía Papelera.
- Nunca simula que mover a Papelera libera espacio inmediatamente.
- Si `TRASH` ya estaba presente antes del primer intento, se registra
  `already_desired_external`; no se atribuye a MailCleanup.
- Un éxito requiere respuesta válida y lectura posterior con `TRASH` presente.

Restaurar usa `users.messages.untrash`, requiere consentimiento separado y
verificación posterior. Google sólo promete retirar el mensaje de Papelera: no
se afirma que restaure exactamente el estado anterior. C7 conserva si `INBOX`
estaba presente antes de la acción y puede proponer reponer únicamente esa
etiqueta después de `untrash`, pero debe volver a confirmar y no pisar cambios
posteriores.

La restauración puede quedar indisponible si Gmail eliminó el mensaje, cambió su
estado, se perdió el permiso o venció su retención. El historial nunca promete
reversibilidad garantizada.

## 12. Protocolo durable sin falsa atomicidad

SQLite y Gmail no comparten una transacción ACID. C7 prohíbe afirmar lo
contrario y prohíbe mantener una transacción SQLite abierta durante red externa.

Por cada mensaje la secuencia obligatoria es:

```text
1. revalidar
2. persistir intención y preestado permitido
3. confirmar la transacción local
4. realizar una única mutación remota
5. persistir respuesta controlada
6. releer el estado remoto
7. persistir resultado verificado
8. marcar el índice como pendiente de reconciliación
```

Una caída después del paso 4 y antes del 7 deja `outcome_unknown`. Nunca se
declara fracaso ni se repite la mutación hasta releer Gmail.

## 13. Estados cerrados

Estados de ejecución:

| Estado | Significado |
|---|---|
| `prepared` | manifiesto listo, todavía sin aprobación |
| `approved` | consentimiento válido, todavía sin efectos |
| `running` | procesa secuencialmente el lote autorizado |
| `attention_required` | una incertidumbre o cambio material detuvo nuevos efectos |
| `partially_completed` | terminó el alcance autorizado con omisiones o fallos explicados |
| `completed` | todos los miembros autorizados tienen resultado terminal explicado |
| `cancelled` | Joa detuvo miembros pendientes; no revierte éxitos |
| `blocked` | falló una puerta global antes de actuar o continuar |
| `failed` | no puede continuar y conserva el ledger |

Estados por mensaje:

```text
pending
intent_recorded
applied
applied_after_reconciliation
already_desired_external
skipped_protected
skipped_missing
skipped_changed
cancelled_before_attempt
retryable_failure
terminal_failure
outcome_unknown
```

Una proyección no borra ni reescribe intentos o resultados anteriores. Una
cancelación sólo afecta `pending`; `intent_recorded` debe reconciliarse.

## 14. Idempotencia y recibos

Cada preparación, aprobación, comienzo, continuación, cancelación,
reconciliación, retry y reversión usa un `commandId` UUID v4.

La huella canónica incluye versión, método lógico, operación, cuenta,
`executionId`, `planId`, `planRevision`, disposición, manifiesto y cuerpo
validado.

- misma ID y misma huella devuelve el recibo original;
- misma ID y otra huella produce `command_id_conflict`;
- un replay nunca vuelve a llamar Gmail;
- un plan sólo puede originar una ejecución;
- un mensaje no puede ejecutarse concurrentemente desde planes solapados;
- un éxito confirmado nunca se repite.

Gmail no ofrece una clave de idempotencia para estos métodos. C7 no promete
“exactly once” entre SQLite y Gmail. Garantiza que nunca repite una escritura a
ciegas y busca converger mediante intención, ledger y reconciliación cuando el
estado remoto puede clasificarse. Si no puede clasificarse, conserva
`outcome_unknown` y se detiene.

## 15. Errores, incertidumbre y reintentos

Los códigos externos se traducen a un catálogo local cerrado. No se persisten
payloads, URLs, tokens, direcciones, asuntos ni excepciones crudas.

- 400 de modelo, 403 de política o permiso, 404 confirmado, identidad incorrecta
  y scope incorrecto son terminales o bloqueantes según el caso;
- 401 intenta una única renovación controlada; si falla, detiene la ejecución;
- 403 normalizado como `rateLimitExceeded` o `userRateLimitExceeded`, cuota,
  429 y 5xx pueden usar backoff exponencial con jitter;
- un timeout o corte después de enviar una escritura produce
  `outcome_unknown`, no un retry automático.

Las lecturas de revalidación pueden repetir como D3: hasta cinco intentos y tope
de 32 segundos. Una escritura admite como máximo tres intentos totales y sólo se
reenvía cuando una lectura posterior demuestra que el efecto no ocurrió y todas
las precondiciones siguen vigentes. Si la lectura no puede clasificar el estado
como aplicado o no aplicado, se pausa toda la ejecución.

Cada intento es append-only. Los éxitos sobreviven a fallos posteriores y no
existe rollback global ficticio.

## 16. Concurrencia, pausa y vencimiento

Existe como máximo una sincronización o ejecución mutadora activa por cuenta.
La exclusión es durable y debe sobrevivir a reinicios; no puede ser sólo un lock
en memoria. C6, D3 y C7 deben coordinar esta frontera antes de integrar D9.

Antes de cada efecto se vuelven a comprobar plan, lease, cuenta y reloj. Si el
plan vence durante una llamada ya iniciada, se registra y verifica ese intento,
pero no se inicia ninguna mutación nueva. Reconciliación y reversión pueden
continuar; la ejecución hacia adelante requiere un plan nuevo.

No hay ejecución automática al arrancar ni con la aplicación cerrada. Reanudar
una interrupción requiere una acción consciente de Joa y empieza por reconciliar
todo `intent_recorded` u `outcome_unknown`.

## 17. Ledger y persistencia

El futuro esquema debe usar tablas normalizadas y claves foráneas para:

- ejecuciones y manifiestos;
- lotes lógicos;
- miembros;
- intenciones e intentos;
- resultados y verificaciones;
- comandos y recibos;
- eventos append-only;
- reversión y sus intentos.

No usa JSON o BLOB abiertos para transportar estado arbitrario. Las revisiones,
conteos y transiciones tienen restricciones verificables. Cada escritura local
relacionada se confirma atómicamente; la red siempre queda fuera.

`delete_account_index` no puede borrar silenciosamente el ledger C7 ni correr
durante una ejecución activa. Borrar índice, credenciales, ledger y capacidad de
reversión son decisiones distintas. La política exacta de retención y borrado
de datos reales continúa como bloqueo antes de D9 real.

## 18. Reconciliación del índice y del mapa

Una respuesta Gmail no edita optimistamente D1. Después de cada efecto
confirmado se registra que la fotografía local está desactualizada. El mensaje
siguiente del mismo lote puede continuar porque se revalida directamente contra
Gmail, el manifiesto permanece congelado y plan/políticas se vuelven a comprobar.
No pueden crearse otros planes ni comenzar otra ejecución con esa fotografía.

Al cerrar cada lote lógico, y siempre al cerrar el piloto:

1. se bloquea la continuación hacia el lote siguiente;
2. D3 relee los IDs afectados o ejecuta la sincronización requerida;
3. D1 persiste checkpoint y cambios mediante su operación atómica;
4. C5 recompone mapa y revisiones;
5. se revisan resultados y omisiones;
6. recién entonces puede autorizarse o continuar otro lote de la misma
   ejecución.

El lote piloto siempre termina en esta pausa. Un historial Gmail es evidencia
auxiliar, no un recibo exclusivo: puede contener cambios de Joa u otros clientes.

## 19. Reversión

La reversión:

- es un comando y manifiesto separados;
- requiere confirmación propia;
- opera por mensaje y conserva el ledger original;
- sólo intenta invertir el delta atribuido y verificado de MailCleanup;
- nunca reemplaza todas las etiquetas con una fotografía vieja;
- no elimina cambios posteriores de Joa o Gmail;
- queda `reversal_unavailable` si no puede demostrarse segura.

Estados cerrados:

```text
reversal_available
reversal_unavailable
reversal_pending
reverted
reversal_failed
reversal_unknown
```

Vencer el plan no impide reconciliar o revertir una ejecución ya realizada. La
reversión no revive el plan ni habilita nuevas mutaciones hacia adelante.

## 20. API local futura

C7 no agrega rutas ahora. Una futura composición debe usar un prefijo nuevo,
por ejemplo `/api/v4/control`, sin reinterpretar `/api/v2` ni
`/api/v3/study`.

Requisitos mínimos:

- Host, Origin, métodos, rutas, queries, JSON y tamaños en allowlists exactas;
- loopback, `Cache-Control: no-store`, sin CORS, cookies ni redirecciones;
- DTO cerrados y versiones exactas;
- IDs remotos, tokens y metadatos privados ausentes de URLs y respuestas;
- comandos POST idempotentes y consultas paginadas;
- `canExecute` sólo en la frontera C7 y sólo si todas las puertas están
  satisfechas;
- frontend incapaz de decidir protecciones, reintentos o reversibilidad.

El prefijo y sus rutas exactas se estabilizarán antes de un prompt D9; este
documento no autoriza implementarlas.

## 21. Presentación y lenguaje

La interfaz separa siempre:

- aprobado;
- aplicado y verificado;
- omitido por protección o cambio;
- fallido;
- incierto;
- reconciliado;
- reversible o no reversible.

No usa “éxito” para un request sin verificación, “espacio liberado” para tamaño
estimado, “restaurado” cuando sólo se pidió `untrash`, ni “sin cambios” cuando el
resultado es desconocido.

## 22. Errores públicos mínimos

El catálogo futuro debe distinguir al menos:

```text
control_unavailable
authorization_required
scope_mismatch
account_mismatch
plan_not_executable
plan_expired
plan_revision_conflict
manifest_changed
approval_expired
approval_replayed
command_id_conflict
execution_conflict
sync_in_progress
policy_changed
message_protected
message_missing
message_changed
rate_limited
remote_temporarily_unavailable
remote_rejected
outcome_unknown
reconciliation_required
reversal_unavailable
private_storage_unavailable
```

No contienen texto remoto ni valores privados.

## 23. Pruebas obligatorias de D9

Toda futura entrega debe demostrar con dobles sintéticos:

1. modelos cerrados, inmutables, versionados y redactados;
2. `gmail.modify` exacto y rechazo de scopes más amplios;
3. allowlist exacta de métodos y endpoints;
4. ausencia de borrar, enviar, componer, filtros, hilos y desuscripción;
5. plan `frozen` y `reduced` aceptados; terminales y vacío rechazados;
6. cuenta, plan, mapa, políticas y revisión exactos;
7. manifiesto canónico que nunca agrega ni reincorpora IDs;
8. desafío de aprobación de un solo uso y vencimiento;
9. disposición distinta del plan rechazada;
10. lote piloto de 1 a 10 y lote ordinario máximo de 50;
11. nueva estrella, importancia, Spam o protección que omite;
12. mensaje nuevo, faltante o cambiado que nunca se incorpora;
13. Archivo que sólo quita `INBOX` y reversión que sólo la agrega;
14. Papelera mediante `trash`, restauración mediante `untrash` y ausencia de
    eliminación definitiva;
15. intención confirmada antes de cada llamada externa;
16. caída antes y después de la llamada remota;
17. resultado incierto reconciliado como aplicado, no aplicado y divergente;
18. replay que no repite red y conflicto de `commandId`;
19. éxito anterior no repetido y fallo en cada posición del lote;
20. cancelación con efectos parciales explicados;
21. reinicio del proceso y recuperación del ledger;
22. cuota, timeout, 401, 403, 404, 429 y 5xx;
23. plan vencido durante el lote;
24. concurrencia con D3, C6 y otro plan solapado;
25. reconciliación obligatoria antes del siguiente lote;
26. reversión disponible, insegura, fallida e incierta;
27. cambio externo posterior que no se pisa;
28. borrado de cuenta bloqueado durante ejecución;
29. API local cerrada, no-store, sin CORS ni IDs remotos;
30. secretos, datos reales y payloads externos ausentes de fixtures, logs y
    excepciones;
31. `canExecute: false` intacto en v1, v2 y v3;
32. batería global y barrera negativa completas.

Las pruebas reales, si alguna vez se autorizan, comienzan con una cuenta y un
lote piloto elegido por Joa. Ninguna prueba automática usa una bandeja real.

## 24. Stop points

La implementación o ejecución se detiene ante:

- falta de una autorización enumerada;
- scope, cuenta o identidad no exactos;
- almacenamiento privado o autenticación local incompletos;
- plan, manifiesto, mapa o política divergentes;
- ejecución o sincronización concurrente;
- protección nueva o evidencia contradictoria;
- respuesta externa no clasificable;
- resultado incierto sin reconciliación;
- necesidad de ampliar endpoint, método, dato, permiso o dependencia;
- aparición de datos reales en Git, logs, fixtures o errores;
- cualquier camino hacia borrado definitivo o vaciado de Papelera.

## 25. Decisiones aceptadas por Joa

Joa aceptó estas decisiones como contrato C7 documental:

| Decisión | Contrato v1 aceptado |
|---|---|
| permiso | sólo `gmail.modify`, solicitado en contexto |
| transporte de escritura | una operación por mensaje; no `batchModify` |
| Archivo | quitar únicamente `INBOX` |
| Papelera | endpoint `trash`; nunca delete |
| Spam | no ejecutable en C7 v1 |
| aprobación | manifiesto exacto, desafío único, vigencia de 10 minutos |
| piloto | máximo 10 mensajes elegidos por Joa y pausa obligatoria |
| lote ordinario | máximo 50, secuencial |
| retry de escritura | nunca a ciegas; máximo tres tras reconciliar |
| mapa | reconciliación D3/D1 obligatoria antes del lote siguiente |
| reversión | comando separado, condicional y por delta |
| desuscripción | fuera de C7 |

La retención exacta del ledger privado, su borrado y el modelo de autenticación
local siguen siendo decisiones bloqueantes que deben cerrarse antes de D9 real,
no supuestos que el especialista pueda inventar.

## 26. Aceptación registrada y siguiente puerta

C7 fue aceptado después de comprobar que:

- sus decisiones no contradicen el MVP ni C6;
- la ampliación de sesión/seguridad queda explícita y versionada;
- ninguna frase presenta la preparación como permiso operativo;
- D9, OAuth, Gmail real y datos privados continúan bloqueados;
- las fuentes durables coinciden con este estado.

Después de consolidar esta documentación, MAIN todavía necesita otra
autorización para preparar la ampliación de sesión/seguridad o el prompt D9
desde un commit limpio. Ninguno de esos pasos se deduce automáticamente de este
documento.

## 27. Referencias oficiales verificadas

Consultadas por MAIN el 31 de agosto de 2026:

- scopes Gmail:
  `https://developers.google.com/workspace/gmail/api/auth/scopes`;
- `users.messages.modify`:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/modify`;
- `users.messages.batchModify`:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/batchModify`;
- `users.messages.get` y formatos de respuesta:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get`;
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/Format`;
- `users.messages.trash` y `untrash`:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/trash`;
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/untrash`;
- errores y reintentos:
  `https://developers.google.com/workspace/gmail/api/guides/handle-errors`;
- batch HTTP:
  `https://developers.google.com/workspace/gmail/api/guides/batch`;
- historial y sincronización:
  `https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list`;
  `https://developers.google.com/workspace/gmail/api/guides/sync`.

La documentación oficial describe capacidades del proveedor, no autoriza a
MailCleanup a usarlas.
