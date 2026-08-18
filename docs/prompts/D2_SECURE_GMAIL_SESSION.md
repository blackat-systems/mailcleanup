# Prompt D2 — Secure Gmail Session

## Rol

Sos la dependencia especialista D2 `secure-gmail-session` de MailCleanup. No
sos MAIN. Implementá exclusivamente la frontera de sesión segura definida por
el contrato y devolvé evidencia para que MAIN audite e integre.

## Ubicación y base obligatorias

- Worktree: el checkout aislado creado por Codex para este task.
- Rama esperada: una rama `codex/*` exclusiva del task.
- Commit base: el SHA exacto indicado por MAIN en el mensaje que acompaña este
  prompt; debe coincidir con tu `HEAD` inicial.
- Estado inicial esperado: limpio.

Antes de editar, ejecutá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short
git worktree list --porcelain
```

Si el HEAD no coincide, la rama está compartida, aparecen cambios ajenos o el
alcance exige cambiar el contrato, detenete y devolvé el bloqueo a MAIN.

## Lectura obligatoria

Leé completamente:

1. `AGENTS.md`.
2. `docs/CONTRATO_MVP.md`.
3. `docs/contracts/GMAIL_SESSION_V1.md`.
4. La sección D2 de `docs/PLAN_DEPENDENCIAS.md`.
5. `docs/DECISIONES.md`.
6. `docs/contracts/INDEX_PERSISTENCE_V1.md`.
7. `pyproject.toml`.
8. `src/mailmap/index_model.py`.
9. `tests/test_base_segura_safety.py`.
10. `scripts/check.ps1`.

`GMAIL_SESSION_V1.md` prevalece para tu alcance. No lo modifiques.

## Objetivo

Implementar el núcleo de sesión Gmail de sólo metadatos, con puertos
inyectables, OAuth de escritorio seguro y almacenamiento DPAPI por usuario,
usando exclusivamente secretos y transportes falsos en las pruebas.

La entrega debe demostrar:

- permiso exacto `gmail.metadata` y rechazo de permisos adicionales;
- autorización pendiente con PKCE S256, `state` y vencimiento;
- callback validado antes de intercambiar o persistir;
- verificación de la cuenta autenticada mediante un puerto de perfil;
- `account_key` opaco independiente de la dirección;
- almacenamiento cifrado por usuario y escritura atómica;
- restauración, renovación, desconexión, revocación y olvido local separados;
- redacción de secretos, direcciones y errores remotos;
- imposibilidad de usar red o navegador reales durante las pruebas.

## Alcance permitido

Podés crear o modificar únicamente:

- `src/mailmap/session_model.py`;
- `src/mailmap/oauth_session.py`;
- `src/mailmap/windows_secret_store.py`;
- `tests/test_gmail_session.py`;
- `tests/test_base_segura_safety.py`, sólo para convertir la prohibición total
  en una allowlist exacta de D2 sin reducir ninguna otra barrera;
- `pyproject.toml`, sólo para dependencias OAuth oficiales indispensables.

Si necesitás API, servicio, frontend, SQLite, fixtures, scripts, otros contratos
o documentación, no los modifiques: devolvé la necesidad a MAIN.

## Contratos obligatorios

1. El único permiso es
   `https://www.googleapis.com/auth/gmail.metadata`.
2. Toda constante de permisos de escritura continúa prohibida globalmente.
3. El dominio no importa HTTP, Google ni APIs Windows.
4. Navegador, callback, transporte, perfil, reloj, aleatoriedad y almacén son
   puertos inyectables.
5. El navegador real no se abre automáticamente en pruebas ni al importar.
6. El callback usa sólo `127.0.0.1`, puerto aleatorio, PKCE S256, `state`
   impredecible y vencimiento.
7. `account_key` es UUID opaco; nunca una dirección ni hash presentado como
   anonimización.
8. El perfil `me` sólo se usa para confirmar identidad; no se listan mensajes.
9. Una cuenta o permiso incorrectos fallan antes de guardar credenciales.
10. Tokens, códigos, verifier, `state`, dirección y cuerpos remotos no aparecen
    en `repr`, logs ni excepciones.
11. DPAPI usa ámbito del usuario actual, nunca máquina local.
12. El archivo cifrado vive bajo `%LOCALAPPDATA%\MailCleanup\credentials`, se
    identifica por `account_key` y se reemplaza atómicamente.
13. Desconexión local, revocación remota y olvido local son acciones distintas.
14. Un fallo de revocación no se informa como éxito ni elimina silenciosamente
    la credencial necesaria para reintentar.
15. No se agregan rutas API y `oauthAvailable` sigue siendo `false`.
16. D1, clasificación, planes, frontend y Base Segura no cambian.

## Dependencias

Preferí las bibliotecas oficiales de Google para autorización y credenciales.
Podés agregar únicamente paquetes OAuth indispensables y con límites de versión
compatibles con Python 3.11. No agregues `google-api-python-client` para
inventario, `keyring`, frameworks web adicionales ni clientes genéricos por
conveniencia.

Antes de agregar una dependencia:

1. justificá qué primitiva de seguridad evita reimplementar;
2. confirmá que no arrastra capacidades de escritura Gmail;
3. mantenela fuera del dominio;
4. cubrí el adaptador con dobles y pruebas negativas.

## Barrera de seguridad

La prueba vigente prohíbe toda red porque correspondía a Base Segura. Podés
evolucionarla únicamente así:

- allowlist por archivo exacto para los adaptadores D2;
- prohibición global de `gmail.modify`, `mail.google.com`, escritura Gmail,
  `credentials.json`, `token.json` y rutas públicas OAuth;
- ninguna excepción para API, servicio, dominio, frontend o scripts;
- prueba que falle si el transporte real se instancia durante tests;
- prueba que inspeccione archivos empaquetados y datos sensibles.

No borres la barrera ni reemplaces una comprobación fuerte por una afirmación.

## Pruebas obligatorias

`tests/test_gmail_session.py` debe cubrir como mínimo:

1. modelos cerrados, inmutables y con `repr` redactado;
2. permiso exacto y rechazo de scopes extra o faltantes;
3. PKCE S256, aleatoriedad, `state` de un uso y vencimiento;
4. callback con error, estado incorrecto, repetido o tardío;
5. cuenta esperada correcta e incorrecta;
6. generación y estabilidad de `account_key`;
7. persistencia sólo después de validar scope e identidad;
8. restauración y renovación;
9. fallo de renovación controlado y sin filtrar respuesta;
10. desconexión local sin falsa revocación;
11. revocación exitosa y fallida;
12. olvido local explícito;
13. DPAPI de usuario, formato versionado, corrupción y reemplazo atómico;
14. ausencia de red, navegador, correos o secretos reales;
15. regresión de D1 y Base Segura.

Ejecutá:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_gmail_session.py
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_safety.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
```

Si el entorno necesita instalar las dependencias aprobadas, usá el procedimiento
oficial y no guardes credenciales ni caches en Git.

## Fuera de alcance

- Abrir OAuth o conectar una cuenta real.
- Solicitar `credentials.json`, contraseñas, tokens o correos a Joa.
- Ejecutar llamadas reales, incluso de perfil o revocación.
- Listar, leer, clasificar o persistir mensajes Gmail.
- `gmail.readonly`, `gmail.modify`, `mail.google.com` o cualquier escritura.
- API pública, frontend, índice D1, clasificación, planes o acciones.
- D3 u otra dependencia.
- Datos, dominios, direcciones o secretos reales en pruebas.
- Cambiar el contrato o ampliar hosts permitidos.
- Hacer commit, push, merge, rebase o integrar en `main`.
- Crear otro worktree o delegar.

## Criterios de aceptación

D2 queda entregada cuando:

1. satisface `GMAIL_SESSION_V1.md`;
2. toda prueba usa dobles sintéticos y cero red/navegador real;
3. los secretos quedan protegidos en almacenamiento, memoria observable,
   errores y logs;
4. la barrera demuestra que no existe permiso ni ruta de escritura;
5. pasan todas las verificaciones aplicables;
6. el diff contiene sólo los archivos permitidos;
7. el worktree queda sin commit para auditoría de MAIN.

## Handoff a MAIN

Entregá un resumen autosuficiente con:

1. resultado;
2. ruta, rama, base y HEAD;
3. estado Git final;
4. archivos modificados y nuevos;
5. diseño, puertos, dependencias y equivalencia con el contrato;
6. pruebas exactas y resultados;
7. revisión de diff, secretos, datos privados y artefactos;
8. riesgos, limitaciones y pendientes;
9. confirmación de cero red, navegador, OAuth real, credenciales y datos reales;
10. confirmación de que no hiciste commit, push, merge ni integración.

No declares D2 integrada, publicada ni habilitada para una cuenta real.
