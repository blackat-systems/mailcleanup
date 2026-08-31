# Contrato de Bóveda Privada Local v1

Estado: `ACEPTADO POR JOA — ALCANCE EXCLUSIVAMENTE DOCUMENTAL` el 31 de agosto
de 2026.

Fecha de preparación: 31 de agosto de 2026.

Autoridad: `CONTRATO_MVP.md`, `SECURITY_PRIVACY_V1.md`,
`INDEX_PERSISTENCE_V1.md`, `LOCAL_POLICY_MEMORY_V1.md`,
`CLEANUP_PLAN_V1.md`, `CONTROLLED_EXECUTION_V1.md`, decisión D-051 de
`DECISIONES.md` y autorizaciones explícitas de Joa para preparar y aceptar esta
ampliación documental.

Este documento extiende C4 para futuros datos privados. Su aceptación y
consolidación documental no significan implementación. No autoriza datos reales,
Gmail, OAuth, credenciales, D9, dependencias, un worktree ni cambios de
arquitectura. La SQLite actual sigue siendo sintética y no apta para datos
reales.

## 1. Objetivo

La Bóveda Privada Local debe proteger en reposo y gobernar el ciclo de vida de:

- índice D1 de metadatos reales;
- políticas y correcciones D5;
- fotografías C5 de Mapa Total;
- planes C6 de Estudio de Limpieza;
- futuro ledger C7, intenciones, recibos y reconciliaciones;
- manifiestos, generación activa, claves y backups autorizados.

La bóveda no almacena cuerpos, HTML, `snippet`, MIME, adjuntos ni destinatarios.
Las credenciales OAuth permanecen en un almacén de secretos separado y los
access tokens de acción definidos por C3-A nunca se persisten.

## 2. Frontera y modelo de amenazas

V1 protege frente a:

- lectura casual del disco o copia del archivo fuera del perfil;
- acceso de otro usuario local sin privilegios;
- pérdida o robo del archivo de base sin la clave;
- alteración, truncación y corrupción detectable;
- residuos en WAL, journal, temporales y backups gestionados por la aplicación;
- apertura bajo perfil, cuenta, versión o ACL incorrectos.

V1 no puede prometer protección frente a:

- malware que ya ejecuta como el mismo usuario;
- administrador, `SYSTEM`, kernel o firmware comprometidos;
- keylogger, captura de pantalla o lectura del proceso mientras la bóveda está
  abierta;
- vuelco de memoria o copias externas que MailCleanup desconoce;
- rollback coordinado de todos los archivos por un atacante local privilegiado;
- recuperación forense garantizada o saneamiento físico de SSD/flash.

BitLocker es una defensa recomendada contra robo y análisis offline del equipo,
pero no reemplaza la bóveda ni se declara implementado por MailCleanup.

## 3. Separación física

Los datos reales deben nacer cifrados en una ubicación distinta de
`data/mailmap-base-segura.db`.

Ruta conceptual:

```text
FOLDERID_LocalAppData\MailCleanup\private-vault\v1\
    accounts\<account_key-opaca>\
        generations\<generation_id-opaca>\
```

Reglas:

- resolver `FOLDERID_LocalAppData` mediante la API de carpetas conocidas de
  Windows; no confiar solamente en una variable de entorno;
- una bóveda por `account_key` UUID4 opaca;
- ninguna dirección, dominio, nombre o ID remoto en la ruta;
- una generación activa completa por cuenta;
- ningún dato real pasa primero por la base sintética ni por un temporal en
  claro;
- nunca mezclar dos cuentas en una bóveda;
- rechazar rutas de red, roaming, UNC, compartidas o fuera de la raíz aprobada;
- exigir un volumen local con ACL de Windows y semántica de archivos verificada;
- rechazar symlinks, junctions, mount points y demás reparse points en cada
  componente de la ruta.

La activación de datos reales debe crear una bóveda nueva. No se convierte en
sitio la base sintética ni se reutilizan sus archivos laterales.

## 4. Propietario y ACL

La raíz y todos sus descendientes son objetos protegidos por una DACL explícita.

Decisión v1 aceptada:

- propietario: SID del usuario interactivo que creó la bóveda;
- SID del mismo usuario: control total;
- herencia protegida;
- ninguna entrada para `Everyone`, `Users`, `Authenticated Users` o grupos de
  administradores;
- `SYSTEM` no se agrega por defecto porque MailCleanup no usa un servicio;
- cualquier ampliación exige una necesidad operativa demostrada y otra
  decisión de seguridad.

Antes de crear, abrir, migrar, respaldar, restaurar o borrar:

1. abrir por handle sin seguir reparse points;
2. resolver y comprobar el destino final;
3. verificar que permanece dentro de la raíz esperada;
4. comprobar propietario y DACL efectiva;
5. rechazar herencia o ACEs más amplias;
6. fallar cerrado sin reparar permisos silenciosamente.

Una ACL reduce exposición entre usuarios, pero un administrador puede tomar
posesión. Por eso no sustituye al cifrado.

## 5. Jerarquía de claves

Cada cuenta y generación usa una DEK aleatoria independiente:

- 256 bits generados por el CSPRNG de Windows (`BCryptGenRandom`);
- nunca derivada de correo, contraseña, token, `account_key` ni constante;
- nunca reutilizada entre cuentas, backups o generaciones;
- identificada por un `key_id` opaco;
- presente en memoria sólo mientras la bóveda esté abierta.

La DEK se protege mediante DPAPI:

- ámbito del usuario actual;
- `CRYPTPROTECT_UI_FORBIDDEN`;
- ausencia obligatoria de `CRYPTPROTECT_LOCAL_MACHINE`;
- sin `CRYPTPROTECT_PROMPTSTRUCT`, mecanismo deprecado que no sustituye la
  verificación local;
- sin descripción privada;
- sin “entropía opcional” constante embebida;
- envelope pequeño, cerrado, versionado y limitado en tamaño;
- binding autenticado a versión, `account_key`, `generation_id`, `key_id` y
  algoritmo;
- comprobación estructural adicional después de DPAPI.

DPAPI protege la DEK, no la base completa. La implementación no puede pasar
bytes de SQLite enteros por DPAPI ni afirmar que el esquema D1 ya está cifrado.

La DEK debe entregarse al proveedor mediante una API binaria o handle de clave
(`sqlite3_key` o equivalente). Queda prohibido interpolarla en `PRAGMA key`,
URI, línea de comandos, variable de entorno o string susceptible de log.

Los buffers nativos de clave deben bloquearse cuando sea viable y limpiarse con
`SecureZeroMemory`. Python no permite prometer que todas las copias administradas
desaparezcan inmediatamente; esa limitación se documenta y minimiza.

El almacén de credenciales D2 sigue siendo una frontera separada. Antes de una
sesión real de lectura debe dejar de resolver LocalAppData sólo desde el entorno,
crear y verificar DACL, rechazar reparse points, usar DPoP para el refresh token
y repetir DPAPI bajo el perfil normal. C4-P no guarda tokens ni vuelve apto ese
almacén por existir como documento.

## 6. Cifrado autenticado integral

La implementación debe usar un proveedor maduro de SQLite que ofrezca:

- clave efectiva de 256 bits;
- confidencialidad e integridad autenticada por página;
- base principal, WAL, rollback journal y backups cifrados, y `-shm` protegido
  por la misma DACL sin datos de aplicación en claro;
- temporales configurados para no escribir metadatos reales en claro;
- fallo cerrado ante clave, tag/HMAC, cabecera o versión inválidos;
- parámetros criptográficos explícitos, fijados y versionados;
- migraciones verificables sin fase plaintext;
- soporte mantenido para Windows, Python 3.11+ y SQLite vigente.

SQLite estándar no satisface estas propiedades por sí sola.

### Proveedor propuesto

MAIN recomienda evaluar primero **SQLCipher 4 Community** porque conserva el
modelo SQLite y agrega cifrado AES-256, HMAC por página y derivación endurecida.
No queda aprobado todavía: es una dependencia nativa nueva y requiere un spike
acotado de compilación, empaquetado, reproducibilidad, licencia, actualización y
rendimiento en Windows.

Alternativa: SQLite SEE con AES-256-GCM. Es mantenida por SQLite, pero requiere
licencia y compilación propias. Un cifrado de campos diseñado por el proyecto no
se recomienda: deja metadatos e índices expuestos y multiplica el riesgo
criptográfico.

El contrato fija propiedades, no una biblioteca. Elegir proveedor es una
decisión material pendiente de Joa después del spike de MAIN.

## 7. Base, WAL, journal y temporales

No basta con cifrar el archivo principal.

- todos los archivos laterales, incluido `-shm`, deben estar dentro de la
  generación protegida;
- WAL y journal usan el mismo proveedor cifrado y parámetros compatibles;
- `temp_store=MEMORY` o equivalente evita temporales de SQLite en disco;
- cualquier sort, índice o migración que fuerce plaintext a disco debe fallar;
- no se usa `ATTACH` a una base no cifrada;
- no se exporta mediante SQL en claro;
- no se copia una base abierta como backup;
- no quedan archivos temporales, dumps, diagnósticos o crash reports con datos.

La memoria del proceso puede contener plaintext mientras la bóveda está abierta.
El alcance v1 minimiza esa ventana, pero no promete cifrado en uso.

## 8. Apertura y capacidad local

Loopback, `Host`, `Origin`, ausencia de CORS y `Cache-Control: no-store` siguen
siendo barreras obligatorias, pero no autentican al usuario ni al proceso.

V1 requiere dos controles adicionales:

1. una capacidad local aleatoria de 256 bits por lanzamiento, sólo en memoria,
   nunca en URL, logs, `localStorage`, archivo o cookie persistente;
2. verificación de presencia de Windows para abrir datos privados y una
   verificación nueva de un solo uso para Archivo, Papelera, reversión,
   exportación, restauración o borrado.

La verificación de presencia debe usar Windows Hello/PIN/biometría mediante
`UserConsentVerifierInterop` y aceptar sólo `Verified`. MailCleanup nunca recibe
ni solicita el PIN, contraseña o dato biométrico.

La API de interop para escritorio indicada por Microsoft requiere Windows 11,
build 22000. Joa aceptó una compatibilidad escalonada:

- la experiencia local y sintética conserva como objetivo Windows 10 y 11;
- datos Gmail reales y Limpieza Controlada requieren inicialmente Windows 11
  build 22000 y todas las demás puertas;
- Windows 10 permanece sin datos ni acciones reales hasta que MAIN proponga y
  Joa acepte una verificación local con propiedades equivalentes;
- ninguna incompatibilidad habilita un fallback a contraseña propia o a confiar
  sólo en loopback.

La aplicación web local actual no posee por sí sola un HWND ni un canal seguro
para entregar la capacidad al navegador. Antes de datos reales, MAIN debe
definir y Joa aceptar un launcher o broker nativo mínimo que:

- sea dueño de la ventana usada por `RequestVerificationForWindowAsync`;
- arranque y supervise el backend loopback;
- entregue una capacidad efímera sin exponerla en URL o almacenamiento web;
- vincule la aprobación a cuenta, acción, manifiesto y comando;
- invalide la capacidad al bloquear, cerrar o perder el proceso;
- falle cerrado si Windows Hello no está disponible, configurado o verificable.

No existe fallback a una contraseña inventada por MailCleanup. Esta es una
puerta de arquitectura pendiente, no una tarea que D9 pueda resolver por su
cuenta.

## 9. Creación y activación atómicas

La creación usa una generación completa y nunca marca activa una bóveda parcial:

1. verificar raíz, propietario, DACL y ausencia de reparse points;
2. crear un directorio de generación opaco con ACL final;
3. generar DEK;
4. crear desde cero la base cifrada y su esquema;
5. escribir envelope DPAPI y manifiesto autenticado;
6. forzar datos relevantes al almacenamiento;
7. cerrar todas las conexiones;
8. reabrir y verificar clave, cifrado, esquema, invariantes e integridad;
9. marcar la generación `complete`;
10. cambiar el puntero pequeño a la generación activa;
11. reabrir desde el puntero y verificar nuevamente.

La generación anterior sólo puede retirarse después de verificar un arranque
completo con la nueva. Sus claves y archivos cuentan como copias conocidas para
el recibo de retención o borrado mientras existan.

Ante una caída, el arranque sólo considera generaciones `complete`. Nunca crea
automáticamente una bóveda vacía encima de una corrupta o incompleta.

No existe atomicidad mágica entre varios archivos. El protocolo de generación y
recuperación es parte del contrato y debe tener inyección de fallos en cada paso.

## 10. Operación y concurrencia

- un solo escritor por bóveda mediante lock de proceso verificable;
- conexiones con foreign keys activas;
- transacciones SQLite y `BEGIN IMMEDIATE` donde lo exijan D1, D5, C6 y C7;
- ninguna transacción abierta durante una llamada de red;
- `synchronous=FULL` o política equivalente auditada;
- esquema y parámetros de cifrado comprobados antes de leer una fila;
- cuenta, generación y revisión verificadas en cada operación sensible;
- cierre de handles y limpieza de claves al bloquear o cerrar;
- `canExecute: false` ante conflicto, lock huérfano no reconciliado o estado
  indeterminado.

La bóveda preserva las garantías transaccionales existentes; no permite que una
capa de cifrado degrade CAS, idempotencia, checkpoints o ledger.

## 11. Migración desde el estado sintético

No hay migración de datos sintéticos a reales.

Cuando se autorice una cuenta real:

- la bóveda nace vacía y cifrada;
- D3 realiza un inventario completo autorizado;
- D4 clasifica desde los registros reales normalizados;
- D5 no copia decisiones sintéticas automáticamente;
- C6 y C7 no reutilizan planes, aprobaciones ni recibos sintéticos;
- la API no expone capacidad real hasta completar apertura, inventario,
  reconciliación y aceptación de Joa.

Una migración futura entre versiones privadas crea una generación nueva,
verifica y recién entonces cambia la activa. Nunca hace rekey parcial in-place.

## 12. Backup y restauración

Decisión v1 aceptada: **backups automáticos y exportación portable
deshabilitados**.

La razón es que un backup sólo protegido con DPAPI puede quedar irrecuperable al
perder el perfil o reinstalar Windows, mientras que una exportación portable
requiere una clave de recuperación o passphrase y otra superficie de seguridad.

Si una versión posterior habilita backup:

- autorización específica de Joa;
- snapshot consistente mediante SQLite Online Backup API;
- destino cifrado desde el primer byte con DEK distinta;
- manifiesto autenticado con cuenta opaca, esquema, generación y digest;
- ninguna credencial ni token OAuth;
- inventario explícito de copias conocidas;
- restauración primero a staging cifrado;
- verificación criptográfica, estructural y funcional antes de activar;
- nueva generación, sesión invalidada, inventario completo y reconciliación;
- `canExecute: false` hasta nueva aprobación.

Portabilidad exige elegir una clave de recuperación aleatoria o una passphrase
con KDF resistente. Ninguna opción se inventa dentro de D9.

## 13. Retención

Decisión v1 aceptada:

- no hay borrado automático en segundo plano;
- índice, políticas, mapas y planes se conservan hasta una acción explícita de
  Joa;
- el access token de acción sólo vive en memoria;
- el ledger C7 no puede borrarse mientras exista `outcome_unknown`,
  reconciliación pendiente, ejecución activa o reversión todavía ofrecida;
- Joa puede pedir borrar una cuenta completa después de resolver esas puertas;
- cada categoría debe mostrar alcance y consecuencia antes de borrar.

Esta política prioriza auditabilidad y evita que una caducidad automática quite
la posibilidad de reconciliar o revertir. Los plazos automáticos, si se desean,
requieren otra decisión de producto y privacidad.

## 14. Borrado honesto y verificable

MailCleanup distingue tres niveles:

### Borrado lógico verificable

Después de reiniciar, no existen estado activo, filas, archivos vivos, punteros,
handles ni backups conocidos dentro del alcance solicitado.

### Inaccesibilidad criptográfica de artefactos vivos conocidos

Se eliminan todas las copias conocidas de DEK y envelopes y se limpian buffers.
Sólo puede afirmarse que los artefactos vivos conocidos dejaron de ser
utilizables si los datos estuvieron cifrados desde su creación y no hay backup
conocido pendiente. No se promete crypto-erasure absoluto: un envelope recuperado
desde SSD, Volume Shadow Copy o backup podría seguir siendo descifrable mientras
exista la master key DPAPI del perfil.

### Saneamiento físico

Está fuera de la aplicación. En SSD/flash, wear leveling, overprovisioning,
snapshots, Volume Shadow Copy, backups y almacenamiento administrado impiden
demostrar que un overwrite de archivo eliminó toda copia física.

`secure_delete`, `VACUUM`, unlink o sobrescritura pueden reducir residuos
lógicos, pero no se presentan como saneamiento físico.

Cada pedido de borrado produce un recibo local no privado con:

- alcance solicitado;
- artefactos conocidos encontrados;
- artefactos eliminados;
- claves eliminadas;
- backups pendientes, inaccesibles o desconocidos;
- limitaciones;
- resultado `complete`, `partial` o `failed`.

No se borra un ledger incierto sin una confirmación separada que explique la
pérdida de reconciliación o reversión.

## 15. Corrupción, manipulación y rollback

Ante clave incorrecta, envelope truncado, HMAC/tag inválido, versión desconocida,
esquema divergente, ACL ampliada, reparse point, generación incompleta o fallo de
integridad:

- cerrar la bóveda;
- invalidar capacidad local;
- mantener `canExecute: false`;
- no entregar datos parciales;
- no migrar, reparar, reemplazar ni borrar automáticamente;
- conservar el artefacto cifrado para una recuperación consciente;
- exponer sólo un código cerrado y redactado.

El cifrado autenticado detecta alteraciones, no garantiza detectar que un
atacante reemplazó todos los archivos por una copia antigua válida. Toda
restauración o regresión de generación detectada invalida sesiones, planes y
aprobaciones y exige inventario completo y reconciliación remota.

Códigos mínimos:

```text
private_storage_unavailable
private_storage_access_denied
private_storage_key_unavailable
private_storage_profile_unavailable
private_storage_corrupt
private_storage_tampered
private_storage_version_unsupported
private_storage_restore_required
private_storage_stale_restore
local_authentication_required
local_authentication_unavailable
```

## 16. Registros y telemetría

No registrar:

- claves, envelopes, tokens o hashes de secretos;
- rutas completas por cuenta;
- direcciones, asuntos, IDs remotos o encabezados;
- páginas, consultas o respuestas de SQLite con datos;
- respuestas de Windows Hello;
- ACL completas si contienen identidad del usuario;
- errores criptográficos crudos o dumps de memoria.

Los eventos permitidos usan códigos cerrados, versión, operación, estado y
duración acotada. No existe telemetría externa en v1.

## 17. Pruebas obligatorias

Antes de aceptar una implementación, con datos `.example` y secretos inventados:

1. base real separada de la sintética desde su creación;
2. ruta resuelta por known folder, cuenta opaca y rechazo de rutas externas;
3. owner, DACL protegida y rechazo de ACEs amplias;
4. rechazo de symlinks, junctions y reparse points;
5. DEK de 256 bits por cuenta/generación mediante CSPRNG;
6. DPAPI CurrentUser, `UI_FORBIDDEN` y ausencia de `LOCAL_MACHINE`;
7. roundtrip DPAPI real no omitido bajo el perfil normal de Joa;
8. envelope versionado, truncado, sobredimensionado y manipulado;
9. ausencia de texto reconocible en DB, WAL, journal, temporales y backups;
10. clave incorrecta, HMAC/tag inválido y parámetros desconocidos;
11. esquema, foreign keys y migraciones equivalentes;
12. inyección de caída en cada paso de generación y activación;
13. recuperación de la última generación completa sin sobrescribir corrupción;
14. transacciones, CAS, idempotencia y checkpoints sin regresión;
15. un solo escritor y cierre ante bloqueo o perfil incorrecto;
16. capacidad local sólo en memoria y no presente en URL, storage o logs;
17. Windows Hello real mediante broker y todos sus resultados negativos;
18. aprobación de un solo uso ligada a acción y manifiesto;
19. backup ausente por defecto;
20. restauración, si se habilita, invalida planes y ejecución;
21. borrado lógico, destrucción de claves y recibos parciales;
22. prueba que impida llamar “saneamiento físico” a unlink u overwrite;
23. fallo cerrado y `canExecute: false` ante cada puerta incompleta;
24. búsqueda de secretos, datos reales y artefactos;
25. batería global y verificación visual de los consentimientos;
26. DEK entregada por API binaria, ausente de SQL, URI, entorno, argv y logs;
27. puerta de plataforma: Windows 11 build 22000 o alternativa aceptada;
28. pruebas negativas del almacén D2 endurecido antes de credenciales reales.

## 18. Stop points

Detener diseño o implementación ante:

- proveedor sin cifrado autenticado de DB y archivos laterales;
- necesidad de escribir plaintext a disco;
- dependencia nativa no autorizada o no reproducible;
- DACL, reparse points o ruta que no pueden verificarse;
- ausencia de perfil DPAPI o Windows Hello verificable;
- necesidad de pasar capacidad o clave por URL/frontend;
- migración que toca la base sintética con datos reales;
- corrupción que sólo puede “resolverse” recreando;
- backup sin política de clave y recuperación;
- pedido de prometer borrado físico del SSD;
- cualquier Gmail, OAuth, credencial o dato real durante pruebas sintéticas.

## 19. Decisiones aceptadas por Joa

Joa aceptó:

1. separación por cuenta y generación bajo LocalAppData;
2. DACL sólo para el usuario actual en v1;
3. SQLCipher 4 Community como primera opción a evaluar, sin aprobar todavía la
   dependencia hasta ver el spike de Windows;
4. backups y exportación portable deshabilitados en v1;
5. retención sin borrado automático y borrado siempre consciente;
6. lenguaje de borrado lógico e inaccesibilidad condicionada, sin garantía de
   crypto-erasure o saneamiento físico;
7. launcher/broker nativo como requisito previo a datos reales;
8. Windows Hello sin fallback a contraseña propia;
9. compatibilidad escalonada: Windows 10/11 para la experiencia sintética y
   Windows 11 build 22000 como mínimo inicial para datos y acciones reales,
   hasta aceptar una alternativa equivalente;
10. BitLocker como recomendación fuerte, no como control implementado por la
    app.

La aceptación tampoco autoriza implementar, agregar SQLCipher, usar datos reales
ni crear D9. Cada paso requiere su propia puerta.

## 20. Referencias oficiales verificadas

Consultadas por MAIN el 31 de agosto de 2026:

- DPAPI `CryptProtectData` y `CryptUnprotectData`:
  `https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata`;
  `https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata`;
- known folders:
  `https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid`;
- seguridad de archivos, ACL y reparse points:
  `https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights`;
  `https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control`;
  `https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points`;
- Windows Hello para escritorio:
  `https://learn.microsoft.com/en-us/uwp/api/windows.security.credentials.ui.userconsentverifier`;
  `https://learn.microsoft.com/en-us/windows/win32/api/userconsentverifierinterop/nf-userconsentverifierinterop-iuserconsentverifierinterop-requestverificationforwindowasync`;
- SQLite SEE:
  `https://sqlite.org/com/see.html`;
- SQLCipher:
  `https://github.com/sqlcipher/sqlcipher`;
  `https://www.zetetic.net/sqlcipher/documentation`;
- NIST SP 800-88 Rev. 2:
  `https://csrc.nist.gov/pubs/sp/800/88/r2/final`.

Las referencias describen controles y límites; no prueban una implementación ni
autorizan dependencias o datos reales.
