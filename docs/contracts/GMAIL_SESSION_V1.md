# Contrato de sesión Gmail v1

Estado: aprobado por MAIN para implementar D2 con dobles sintéticos y sin abrir
una sesión real.

Nota de revisión: el contrato D2 sintético sigue aprobado. Joa aceptó junto con
C3-A la corrección factual del 31 de agosto de 2026 sobre autorización
incremental. Esto no autoriza modificar D2 ni abrir OAuth en este trabajo
documental.

Autoridad: aceptación explícita de Base Segura y autorización de Joa del 18 de
agosto de 2026 para preparar y crear la siguiente dependencia especialista.

Este contrato estabiliza C2 y C3 para D2. Autoriza construir la capacidad, no
conectar una cuenta, abrir OAuth, solicitar credenciales ni leer Gmail durante
el desarrollo o las pruebas.

## 1. Responsabilidad

D2 implementa la frontera de sesión de una sola cuenta Gmail:

- preparar una autorización de escritorio;
- validar el permiso concedido;
- comprobar la identidad mediante el perfil Gmail de `me`;
- guardar, recuperar y renovar credenciales en almacenamiento protegido;
- distinguir desconexión local de revocación remota;
- exponer estados y errores controlados sin filtrar secretos.

D2 no lista mensajes, no construye el mapa, no clasifica y no modifica Gmail.

## 2. Permiso único

El único permiso Gmail admitido en D2 es:

```text
https://www.googleapis.com/auth/gmail.metadata
```

Quedan prohibidos `gmail.readonly`, `gmail.modify`, `gmail.compose`,
`gmail.settings.*`, `https://mail.google.com/` y cualquier permiso de escritura.

`gmail.metadata` permite ver etiquetas y encabezados, no el cuerpo. Es un
permiso restringido de Google y por eso una conexión real requerirá una nueva
confirmación en contexto. El parámetro `q` de `users.messages.list` no está
disponible con este permiso; D3 deberá paginar el inventario autorizado y
aplicar filtros localmente. D2 no implementa ese inventario.

## 3. Flujo OAuth de escritorio

La implementación futura real debe usar:

- aplicación OAuth de escritorio;
- navegador externo del sistema, nunca webview embebida;
- redirección a `http://127.0.0.1:<puerto-aleatorio>`;
- PKCE con `S256` y verificador nuevo por intento;
- `state` impredecible, de un solo uso y comparado en tiempo constante;
- código de autorización intercambiado una sola vez;
- tiempo máximo y cancelación explícitos;
- autorización contextual limitada al permiso exacto anterior, sin
  `include_granted_scopes`.

Actualización factual verificada por MAIN el 31 de agosto de 2026: Google no
admite autorización incremental para aplicaciones instaladas. El orquestador D2
sintético integrado todavía emite ese parámetro, aunque no existe un transporte
real; debe retirarlo y agregar una regresión antes de cualquier adaptador OAuth
real. Esta corrección documental no autoriza ese adaptador ni una conexión.

No se admite `localhost`, puerto fijo, servidor enlazado a interfaces externas,
flujo out-of-band, copiar códigos manualmente ni registrar URL, código, `state`
o tokens completos.

Durante D2 las pruebas usan un transporte, navegador y callback falsos. Ninguna
prueba puede acceder a Internet ni abrir una ventana real.

## 4. Identidad de cuenta

Después del intercambio, el único acceso Gmail permitido a D2 es
`users.getProfile(userId="me")` para obtener la identidad autenticada.

- La dirección se normaliza sólo para comparar y mostrar conscientemente.
- Nunca se usa como `account_key`.
- `account_key` es un UUID local aleatorio y opaco.
- La dirección no se guarda en SQLite, logs, excepciones ni nombres de archivo.
- Si existe una cuenta esperada y no coincide, no se crea la sesión y se
  descartan las credenciales recibidas de acuerdo con el flujo seguro.

Los totales y `historyId` devueltos por el perfil no pertenecen a D2 y no deben
persistirse como parte de la sesión.

## 5. Modelo cerrado

El dominio debe representar como mínimo:

- `SessionState`: `disconnected`, `authorizing`, `connected`,
  `refresh_required`, `revoked`, `scope_mismatch`, `account_mismatch` y
  `failed`;
- `SessionIdentity`: `account_key` opaco y dirección privada marcada para no
  aparecer en `repr`;
- `CredentialBundle`: tokens, vencimiento y permisos, siempre con `repr`
  redactado;
- `SessionErrorCode`: códigos cerrados sin texto remoto.

No se aceptan diccionarios `extra`, respuestas OAuth crudas ni excepciones que
puedan transportar tokens, códigos o direcciones.

## 6. Almacenamiento protegido en Windows

El contrato fija para V1:

- directorio: `%LOCALAPPDATA%\MailCleanup\credentials`;
- archivo por `account_key`, nunca por dirección;
- contenido cifrado mediante DPAPI en ámbito del usuario actual;
- prohibido `CRYPTPROTECT_LOCAL_MACHINE`;
- escritura atómica mediante temporal y reemplazo;
- formato versionado y validado antes de descifrar o usar;
- ninguna copia plaintext, archivo de respaldo automático o volcado en logs;
- cliente OAuth y tokens fuera del repositorio.

El adaptador depende de un puerto de almacenamiento para poder probarse con una
memoria falsa. Las pruebas de DPAPI usan secretos inventados y deben omitir con
razón explícita cualquier caso no ejecutable fuera de Windows.

El índice D1 continúa separado. Borrar credenciales no borra el índice y borrar
el índice no revoca credenciales.

## 7. Operaciones públicas

La capa de aplicación debe ofrecer operaciones tipadas equivalentes a:

```python
prepare_authorization(expected_account: str | None) -> PendingAuthorization
complete_authorization(callback: AuthorizationCallback) -> SessionIdentity
restore_session(account_key: str) -> SessionSnapshot
refresh_session(account_key: str) -> SessionSnapshot
disconnect_local(account_key: str) -> None
revoke_remote(account_key: str) -> RevocationResult
forget_local(account_key: str) -> None
```

`prepare_authorization` construye el intento, pero el navegador real queda
deshabilitado durante D2. `complete_authorization` valida primero `state`,
permiso exacto e identidad y recién entonces persiste.

`disconnect_local` deja de usar la sesión sin afirmar revocación. La revocación
remota y el borrado local son pasos observables separados. Un fallo remoto no
puede declararse éxito ni borrar silenciosamente la única credencial necesaria
para reintentar; `forget_local` requiere una acción explícita independiente.

## 8. Puertos y dependencias

OAuth, perfil Gmail, reloj, generación aleatoria, navegador, callback y almacén
de secretos deben depender de puertos inyectables. El dominio no importa SDKs
de Google, HTTP ni APIs de Windows.

D2 puede agregar únicamente las dependencias oficiales indispensables para
OAuth de Google. No puede agregar el cliente completo de Gmail para inventario
ni una biblioteca general de almacenamiento de secretos si DPAPI puede
encapsularse con la biblioteca estándar. Toda dependencia agregada debe quedar
acotada en `pyproject.toml`, justificada en el handoff y cubierta por la barrera
de seguridad.

## 9. Red permitida en una futura ejecución real

La implementación debe permitir únicamente:

- autorización en `https://accounts.google.com/`;
- intercambio y revocación en `https://oauth2.googleapis.com/`;
- perfil en `https://gmail.googleapis.com/gmail/v1/users/me/profile`.

No se permiten redirecciones arbitrarias, hosts configurables por datos remotos,
proxies incluidos en credenciales, endpoints de mensajes ni métodos de escritura.
En D2 todo transporte real permanece deshabilitado por configuración y pruebas.

## 10. Logs y errores

Nunca registrar:

- tokens o hashes de tokens;
- código de autorización, PKCE verifier o `state`;
- dirección completa;
- contenido de respuestas remotas;
- configuración OAuth completa;
- rutas que revelen una cuenta.

Los errores públicos son códigos controlados. El detalle técnico puede conservar
tipo de operación y estado HTTP, pero no cuerpo remoto ni datos privados.

## 11. Barrera de seguridad

La barrera de Base Segura debe evolucionar sin debilitarse:

- permitir OAuth solamente dentro del adaptador D2 delimitado;
- seguir prohibiendo clientes externos en dominio, API, servicios y frontend;
- prohibir globalmente permisos de escritura y `https://mail.google.com/`;
- comprobar que no aparezcan `credentials.json`, `token.json`, secretos o datos
  reales;
- demostrar con dobles que ningún test usa red o navegador reales.

D2 no agrega rutas HTTP públicas. `oauthAvailable` permanece `false` hasta que
MAIN integre, audite y autorice por separado la composición real.

## 12. Definición de terminado

D2 queda entregada cuando:

1. sólo solicita `gmail.metadata`;
2. PKCE, `state`, loopback y vencimiento tienen pruebas negativas;
3. permiso o cuenta incorrectos impiden persistir;
4. secretos y dirección quedan redactados;
5. DPAPI usa ámbito de usuario y escritura atómica;
6. restauración, renovación, desconexión, revocación y borrado local tienen
   estados diferenciados;
7. no cambia índice, clasificación, API ni frontend;
8. no hay red, navegador, credenciales ni cuenta reales en pruebas;
9. pasan pruebas específicas, pytest, Ruff, mypy, batería global y revisión de
   secretos;
10. el especialista entrega cambios sin commit para auditoría de MAIN.

## 13. Fuentes técnicas

- Gmail scopes: https://developers.google.com/workspace/gmail/api/auth/scopes
- OAuth de escritorio: https://developers.google.com/identity/protocols/oauth2/native-app
- Perfil Gmail: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/getProfile
- Recomendaciones OAuth: https://developers.google.com/identity/protocols/oauth2/resources/best-practices
- DPAPI: https://learn.microsoft.com/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
