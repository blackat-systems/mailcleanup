# Contrato de Sesión de Acción Gmail v1

Estado: `ACEPTADO POR JOA — ALCANCE EXCLUSIVAMENTE DOCUMENTAL` el 31 de agosto
de 2026.

Fecha de preparación: 31 de agosto de 2026.

Autoridad: `CONTRATO_MVP.md`, `SECURITY_PRIVACY_V1.md`,
`GMAIL_SESSION_V1.md`, `CONTROLLED_EXECUTION_V1.md`, decisión D-051 de
`DECISIONES.md` y autorizaciones explícitas de Joa para preparar y aceptar esta
ampliación documental.

Este documento extiende C3 para una futura Limpieza Controlada. Su aceptación y
consolidación documental no significan implementación. No autoriza crear D9,
abrir OAuth, conectar Gmail, solicitar credenciales, usar datos reales, agregar
dependencias, crear un worktree ni modificar mensajes. D2 y D3 continúan
limitadas a `gmail.metadata`; `oauthAvailable: false` y `canExecute: false`
permanecen invariantes.

## 1. Objetivo y separación obligatoria

La Sesión de Acción es una capacidad de elevación temporal para ejecutar
únicamente Archivo o Papelera sobre un manifiesto C7 previamente aprobado. No
es una ampliación silenciosa de la sesión D2.

```text
sesión de lectura D2 (`gmail.metadata`)
                │ permanece separada
                │
manifiesto C7 exacto + presencia local verificada
                ↓
autorización contextual de acción (`gmail.modify`)
                ↓
capacidad efímera, ligada a cuenta y manifiesto
                ↓
adaptador D9 cerrado por allowlist
                ↓
revocación y descarte local observables
```

Se exigen dos dominios de sesión distintos:

- **sesión de lectura**: conserva el contrato D2 y su constante exacta
  `gmail.metadata`;
- **sesión de acción**: usa modelos, almacenamiento, estado, errores y ciclo de
  vida propios; nunca reemplaza, promueve ni reescribe una credencial D2.

Una credencial de acción no puede ser consumida por D3, clasificación, API,
frontend ni Estudio de Limpieza. Sólo un futuro adaptador D9 aceptado puede
recibir una capacidad opaca y acotada; nunca recibe el token crudo.

## 2. Decisión aceptada para v1

Joa aceptó para v1 una sesión de acción **efímera y online**:

- proyecto OAuth de Google separado del proyecto de lectura;
- cliente OAuth de tipo Desktop separado;
- solicitud contextual del scope exacto `gmail.modify`;
- `access_type=online` y ausencia de refresh token de acción;
- access token únicamente en memoria;
- revocación remota intentada al cerrar la sesión;
- descarte local incondicional al vencer, cancelar, cerrar la aplicación o
  terminar la ejecución;
- nueva autorización consciente para una ejecución posterior.

Este diseño agrega fricción antes de actuar, pero evita conservar una capacidad
de escritura de larga duración. Es la recomendación de MAIN para el primer
piloto real.

Persistir un refresh token de acción queda fuera de v1. Una versión futura sólo
podrá permitirlo mediante otra decisión de Joa, DPoP obligatorio, clave de
dispositivo protegida y una nueva auditoría del modelo de amenazas.

## 3. Permiso exacto y capacidad efectiva

El único scope de la Sesión de Acción es:

```text
https://www.googleapis.com/auth/gmail.modify
```

La respuesta OAuth debe contener exactamente ese conjunto. Falta, exceso,
alternativa, combinación con `gmail.metadata` o scope desconocido producen
`scope_mismatch` antes de activar la sesión.

Quedan prohibidos:

- `https://mail.google.com/`;
- `gmail.readonly`, `gmail.compose`, `gmail.send`, `gmail.insert` y
  `gmail.settings.*`;
- reutilizar la constante o el registro persistido de D2;
- aceptar un grant acumulado más amplio;
- enviar, componer, insertar, borrar definitivamente, cambiar configuración o
  actuar sobre hilos.

`gmail.modify` es un scope restringido y permite al proveedor más operaciones
que Archivo y Papelera. El permiso no constituye la frontera funcional. El
transporte D9 debe negar todo salvo la allowlist exacta de C7.

## 4. Autorización contextual, no incremental

Google no admite autorización incremental para aplicaciones instaladas. La
Sesión de Acción debe ser una autorización contextual separada y no debe enviar
`include_granted_scopes=true`.

Parámetros cerrados de autorización:

- endpoint exacto de Google para autorización instalada;
- `client_id` del cliente Desktop de acción;
- `redirect_uri` exacta de loopback IPv4;
- `response_type=code`;
- scope exacto de esta sección;
- PKCE `S256` con verifier nuevo por intento;
- `state` aleatorio, de un solo uso y comparado en tiempo constante;
- `access_type=online`;
- `prompt=consent` para hacer visible la elevación contextual;
- ausencia de `include_granted_scopes`, `login_hint`, hosts, URLs o parámetros
  configurables por datos externos.

La implementación sintética D2 conserva valor como modelo y barrera negativa,
pero su uso actual de `include_granted_scopes=true` no puede trasladarse a un
adaptador real. Esa diferencia debe corregirse y probarse antes de cualquier
OAuth real.

## 5. Proyecto OAuth y revocación

Google documenta que revocar un token elimina los scopes concedidos al proyecto
OAuth e invalida tokens de todos sus clientes. Dos archivos locales o dos
clientes dentro del mismo proyecto no aíslan la revocación remota.

Por eso v1 exige proyectos OAuth separados:

- un proyecto para lectura `gmail.metadata`;
- otro proyecto para acción `gmail.modify`.

El costo es duplicar configuración, ambientes y posiblemente la verificación
del proveedor. MAIN considera aceptable esa carga para evitar que retirar una
capacidad de escritura desconecte también la lectura.

Si Joa decidiera usar un único proyecto, debe existir otra versión contractual
que acepte expresamente que revocar la acción puede desconectar también Mapa
Total. MAIN no puede presentar esa configuración como sesiones remotamente
independientes.

Revocar y olvidar siguen siendo operaciones separadas:

1. se solicita la revocación al endpoint exacto;
2. se registra sólo `accepted`, `failed` u `outcome_unknown`;
3. se descarta siempre la capacidad local al cerrar;
4. no se afirma efecto remoto instantáneo;
5. no se borra evidencia necesaria para reconciliar una ejecución incierta.

## 6. Flujo OAuth de escritorio

La futura implementación real debe usar:

- navegador externo del sistema, nunca webview;
- callback exacto
  `http://127.0.0.1:<puerto-efímero>/oauth2/action/callback`;
- listener enlazado sólo a `127.0.0.1`;
- puerto asignado por el sistema, no fijo;
- PKCE S256;
- `state` impredecible, efímero y de un solo uso;
- callback de una sola aceptación, con replay rechazado;
- vencimiento del intento a los cinco minutos;
- intercambio del código una sola vez;
- límites de tamaño y parámetros exactos;
- cierre inmediato del listener después de completar, cancelar o vencer.

Quedan prohibidos `localhost`, IPv6, wildcard, OOB, pegar códigos manualmente,
redirecciones abiertas, proxies implícitos, navegador embebido y registrar URL,
código, verifier, `state`, token o respuesta completa.

## 7. Identidad y vínculo con C7

Antes de activar la capacidad se debe comprobar `users.getProfile("me")` con
la identidad obtenida por OAuth y vincularla al `account_key` opaco del
manifiesto C7.

La capacidad efímera queda ligada como mínimo a:

- `account_key` exacto;
- `plan_id`, `plan_revision` y digest del manifiesto;
- disposición exacta `archive` o `trash`;
- identidad del proyecto y cliente OAuth de acción;
- scope exacto;
- instante de creación y vencimiento;
- nonce local de un solo proceso.

Cuenta, scope o manifiesto distintos invalidan la sesión. La dirección sólo se
usa en memoria para comparar y mostrar conscientemente; no integra IDs, rutas,
logs, excepciones ni archivos.

## 8. Ciclo de vida cerrado

Estados mínimos:

```text
unavailable
awaiting_local_verification
authorizing
validating_identity
active
expired
cancelled
revocation_pending
revoked
scope_mismatch
account_mismatch
failed
```

Reglas:

- la verificación local C4-P precede a `authorizing`;
- el token puede existir únicamente en memoria durante `validating_identity`,
  `active` y `revocation_pending`; D9 sólo puede consumirlo en `active` después
  de validar scope, proyecto, cuenta e identidad;
- todo fallo durante intercambio o validación descarta inmediatamente el token
  local y nunca activa D9;
- no se restaura una Sesión de Acción después de reiniciar el proceso;
- el vencimiento local máximo es el menor entre diez minutos, el vencimiento
  del access token y la vigencia restante de la aprobación C7;
- pausa, cancelación, cambio de cuenta, cambio de manifiesto, bloqueo del
  equipo o cierre del proceso invalidan la capacidad;
- si el access token vence durante un lote, D9 se detiene antes de la siguiente
  llamada, conserva el ledger y reconcilia; v1 nunca renueva en silencio;
- reanudar exige nueva verificación local y nueva autorización;
- ningún error abre el navegador automáticamente;
- ninguna sesión activa convierte `canExecute` en una propiedad global.

D9 debe recibir una operación por vez mediante un puerto tipado. No recibe un
objeto que permita fabricar URLs, métodos, scopes, cuerpos o etiquetas.

La vigencia local de diez minutos limita a MailCleanup, no al proveedor. Un
Bearer copiado puede seguir siendo utilizable hasta su vencimiento remoto si la
revocación falla o demora. Esta es una limitación residual explícita de v1; el
producto minimiza la ventana y revoca, pero no promete invalidación remota
instantánea.

## 9. DPoP y tokens persistentes

Google permite ligar refresh tokens de clientes instalados mediante DPoP. El
access token que llama Gmail continúa siendo Bearer; DPoP no reemplaza la
allowlist ni evita el daño si se roba el access token en memoria.

V1 no conserva refresh tokens de acción y, por lo tanto, no necesita una clave
DPoP de acción persistida. Si una versión posterior admite refresh:

- DPoP es obligatorio, no opcional;
- clave P-256/ES256 nueva y no exportable por dispositivo;
- referencia de clave protegida; nunca PEM copiable;
- prueba DPoP nueva por intercambio y renovación;
- manejo cerrado de `DPoP-Nonce` y `use_dpop_nonce`;
- el mismo par de claves debe renovar el token ligado;
- JWT, nonce, clave y tokens quedan excluidos de logs y errores;
- pérdida de la clave obliga a reautorizar; nunca se degrada a Bearer refresh.

La sesión de lectura D2 deberá recibir su propia ampliación versionada antes de
persistir un refresh token real. Debe retirar `include_granted_scopes`, ligar el
refresh token mediante DPoP, resolver known folder, DACL y reparse points del
almacén de secretos y repetir la prueba DPAPI real. El hecho de que D2 sintética
esté integrada no constituye aceptación del riesgo para datos reales.

## 10. Almacenamiento y exposición

En v1:

- no se persiste refresh token de acción;
- el access token no se guarda en SQLite, DPAPI, archivos, logs, frontend,
  historial, crash dumps voluntarios ni respuestas API;
- buffers se mantienen el menor tiempo posible y se limpian al cerrar, sin
  prometer borrado perfecto de todas las copias administradas por Python;
- `client_id` y configuración de escritorio están fuera de Git;
- no existe `client_secret` confiable para un cliente instalado público;
- la Bóveda Privada guarda el ledger y el estado no secreto, no el access token.

El frontend sólo observa estados redactados y una capacidad local de un solo
uso. Nunca recibe la credencial OAuth ni una operación Gmail ampliable.

## 11. Red y transporte permitidos

Los únicos destinos de sesión futuros son los endpoints exactos oficiales para:

- autorización;
- intercambio de código;
- perfil `users/me/profile`;
- revocación.

El adaptador debe fijar esquema HTTPS, host, puerto, ruta, método, redirecciones,
tamaños, timeouts y campos. No hereda proxies del entorno, no acepta URLs desde
respuestas y no sigue redirecciones fuera de la política exacta.

Las llamadas de Archivo/Papelera pertenecen a D9 y a la allowlist C7; no forman
parte del transporte OAuth.

## 12. Errores y redacción

Códigos públicos mínimos:

```text
action_session_unavailable
local_verification_required
authorization_cancelled
authorization_expired
invalid_callback
callback_replayed
scope_mismatch
account_mismatch
token_exchange_failed
profile_verification_failed
revocation_failed
revocation_outcome_unknown
```

No contienen texto remoto, URLs, direcciones, IDs de mensaje, tokens, hashes de
tokens, códigos OAuth, verifier, `state`, nonce DPoP ni configuración completa.

## 13. Verificación de Google y ambientes

`gmail.modify` es un scope restringido. Antes de un piloto real, MAIN debe
verificar el estado vigente del proyecto Google, usuarios de prueba, pantalla de
consentimiento, política de privacidad, límites y requisitos de evaluación.

Desarrollo/pruebas y producción deben usar proyectos separados. Un proyecto
externo en estado Testing no puede tratarse como una sesión durable: los
refresh tokens pueden vencer a los siete días y sólo acceden usuarios de prueba.

Cross-Account Protection queda fuera de v1 porque exige un receptor de eventos
servidor y contradice la arquitectura local sin backend remoto. No se presenta
su ausencia como una protección implementada.

## 14. Pruebas obligatorias antes de aceptar implementación

Con dobles sintéticos:

1. scope exacto y rechazo de cualquier conjunto adicional;
2. ausencia de `include_granted_scopes`;
3. `access_type=online` y ausencia de refresh token persistido;
4. proyecto/cliente de acción separado;
5. PKCE S256, `state`, vencimiento, callback y replay;
6. listener sólo IPv4 loopback y puerto efímero;
7. identidad y `account_key` verificados antes de activar;
8. vínculo exacto con manifiesto y disposición C7;
9. expiración, cancelación, pausa, cierre y bloqueo invalidan;
10. revocación y olvido distinguidos;
11. fallo de revocación no conserva capacidad local;
12. token, código, verifier, dirección y respuesta remota redactados;
13. frontend, API y ledger nunca reciben el token;
14. no existe SDK, navegador o red real en pruebas sintéticas;
15. ninguna ruta activa cambia `oauthAvailable: false` o `canExecute: false`;
16. token no consumible por D9 durante validación o revocación;
17. vencimiento local no se presenta como invalidación remota del Bearer;
18. barrera negativa, suite específica y batería global verdes.

Una futura prueba real requiere autorización aparte, una cuenta exacta elegida
por Joa y stop points ante cualquier scope, cuenta, proyecto o respuesta no
esperados.

## 15. Stop points

Detener preparación o implementación ante:

- necesidad de ampliar permisos, destinos o métodos;
- imposibilidad de separar proyectos OAuth;
- grant devuelto con permisos adicionales;
- aparición de refresh token donde v1 no lo espera;
- identidad o cuenta no exactas;
- Bóveda Privada o verificación local incompletas;
- necesidad de exponer token al frontend;
- requisito de agregar dependencia sin autorización;
- cualquier dato privado, secreto, navegador o red real durante pruebas
  sintéticas.

## 16. Decisiones aceptadas por Joa

Joa aceptó conjuntamente:

1. proyecto OAuth de acción separado del de lectura;
2. sesión de acción efímera sin refresh token;
3. nueva autorización contextual para cada ejecución o reanudación;
4. revocación remota al cerrar, con resultado explícito y no instantáneo;
5. DPoP obligatorio si una versión futura persiste refresh tokens;
6. que la fricción adicional es preferible a conservar escritura durable.

Esta aceptación documental no autoriza OAuth real, D9 ni Limpieza Controlada.

## 17. Referencias oficiales verificadas

Consultadas por MAIN el 31 de agosto de 2026:

- OAuth para aplicaciones instaladas:
  `https://developers.google.com/identity/protocols/oauth2/native-app`;
- prácticas recomendadas OAuth:
  `https://developers.google.com/identity/protocols/oauth2/resources/best-practices`;
- adopción DPoP:
  `https://developers.google.com/identity/protocols/oauth2/resources/dpop-adoption`;
- políticas OAuth:
  `https://developers.google.com/identity/protocols/oauth2/policies`;
- scopes Gmail:
  `https://developers.google.com/workspace/gmail/api/auth/scopes`;
- política de datos de Workspace:
  `https://developers.google.com/workspace/workspace-api-user-data-developer-policy`.

Las fuentes describen capacidades y obligaciones del proveedor; no autorizan a
MailCleanup a conectarse ni actuar.
