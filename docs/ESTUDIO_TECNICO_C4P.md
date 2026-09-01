# Estudio técnico C4-P — Fase A

Fecha de corte: 1 de septiembre de 2026.

Estado: AUDITADO POR MAIN Y ACEPTADO POR JOA. Estudio documental y experimental
acotado. No constituye selección de proveedor, aprobación de dependencia,
implementación de C4-P ni autorización para comenzar la Fase B.

Condición de ejecución: **FASE A EJECUTADA — FASES B-D NO EJECUTADAS**.

## Resultado ejecutivo

VERIFICADO:

- La Puerta 0 coincide exactamente con la base autorizada
  6f867544d8bc8319e082328163ea3684e24a86c0, en HEAD desacoplado y con el
  worktree limpio, incluidos los archivos no rastreados.
- La persistencia activa de MailCleanup abre SQLite estándar mediante el módulo
  sqlite3 de CPython. No existe una fábrica de proveedor, un binding cifrado,
  un broker, Windows Hello ni empaquetado desktop conectados al producto.
- Existe una primitiva DPAPI concreta en windows_secret_store.py, pero está
  desacoplada de la aplicación activa, protege únicamente un envelope pequeño
  de credenciales y no implementa la bóveda C4-P.
- El SQLite enlazado por el CPython disponible es SQLite 3.50.4, no declara
  opciones de codec conocidas, no responde con una versión de cipher y usa
  TEMP_STORE=1 como valor compilado.
- La prueba negativa A2 encontró el canario sintético en claro en los tres
  artefactos observados: base principal cerrada, WAL con conexión abierta antes
  de checkpoint y rollback journal durante una transacción abierta.
- Se estudiaron exactamente cuatro familias de provisión. Ninguna queda
  aprobada: cada opción conserva pendientes y ninguna cierra conjuntamente
  procedencia verificable, licencia aplicable, ABI, vía de clave, núcleo SQLite
  único y validación integral.

INFERIDO:

- El camino de menor superficie conceptual para un único launcher y un único
  backend hijo es un par de pipes anónimos con herencia explícitamente acotada.
  Es una recomendación de diseño sólo para launcher–backend, no resuelve el
  canal al navegador y no es un IPC implementado ni validado.
- SQLCipher Community y SEE exponen APIs C capaces de recibir bytes más
  longitud. Eso sólo sería compatible con C4-P si un adaptador futuro llamara
  directamente esa API sin convertir la clave a string ni pasarla por SQL,
  PRAGMA, URI, entorno, argumentos o logs.

PENDIENTE:

- No existe proveedor, binding, toolchain ni binario candidato seleccionado.
- No se descargó, instaló, compiló, cargó ni ejecutó SQLCipher, SEE o binding
  tercero.
- No se ejecutaron Windows Hello, broker, IPC, Gmail, OAuth, datos privados ni
  acciones reales.
- La versión exacta de CPython/ABI para Fase B y el canal
  launcher/broker→navegador permanecen como stop points sin resolver.
- La Fase B permanece bloqueada hasta una autorización nueva y explícita.

La conclusión de A2 es estrictamente negativa: SQLite estándar deja evidencia
legible y no satisface C4-P. La ausencia de un canario en otro proveedor sería
necesaria, pero nunca suficiente para aprobarlo.

## 1. Alcance, autoridad y límites

Este estudio cubre únicamente A1–A6:

1. inventario reproducible del entorno y del SQLite realmente enlazado;
2. prueba negativa de bytes con SQLite estándar dentro de un directorio
   temporal controlado;
3. inventario de la superficie actual de persistencia y seguridad;
4. matriz documental de cuatro opciones de provisión;
5. diseño del harness que debería validar un candidato futuro;
6. diseño conceptual mínimo del IPC launcher–backend.

Quedaron expresamente fuera de alcance:

- modificar código, configuración, dependencias o lockfiles;
- instalar, compilar o ejecutar un proveedor cifrado;
- crear una fábrica de conexiones, binding, broker o launcher;
- invocar DPAPI real, Windows Hello o IPC;
- abrir OAuth, conectar Gmail, solicitar credenciales o usar datos reales;
- iniciar una Fase B;
- hacer commit, push, merge, rebase, reset u otra operación Git mutante;
- leer o modificar New folder/grafo.txt;
- incorporar cambios no confirmados de MAIN.

### 1.1 Fuentes de verdad leídas completas

Gobierno, alcance y estado:

- [AGENTS.md](../AGENTS.md)
- [README.md](../README.md)
- [CONTRATO_MVP.md](CONTRATO_MVP.md)
- [AUDITORIA_PRE_DESARROLLO.md](AUDITORIA_PRE_DESARROLLO.md)
- [DECISIONES.md](DECISIONES.md)
- [ESTADO_BASE_SEGURA.md](ESTADO_BASE_SEGURA.md)
- [PLAN_DEPENDENCIAS.md](PLAN_DEPENDENCIAS.md)
- [PROMPT_MAESTRO_MAIN.md](PROMPT_MAESTRO_MAIN.md)
- [PRIVATE_LOCAL_VAULT_V1.md](contracts/PRIVATE_LOCAL_VAULT_V1.md)
- [SECURITY_PRIVACY_V1.md](contracts/SECURITY_PRIVACY_V1.md)

Stack, ejecución y límites de distribución:

- [pyproject.toml](../pyproject.toml)
- [frontend/package.json](../frontend/package.json)
- [.gitignore](../.gitignore)
- [check.ps1](../scripts/check.ps1)
- [run.ps1](../scripts/run.ps1)
- [setup.ps1](../scripts/setup.ps1)

Persistencia, seguridad y pruebas relevantes:

- [repository.py](../src/mailmap/repository.py)
- [api.py](../src/mailmap/api.py)
- [main.py](../src/mailmap/main.py)
- [windows_secret_store.py](../src/mailmap/windows_secret_store.py)
- [oauth_session.py](../src/mailmap/oauth_session.py)
- [gmail_inventory.py](../src/mailmap/gmail_inventory.py)
- [gmail_readonly_policy.py](../src/mailmap/gmail_readonly_policy.py)
- [map_api.py](../src/mailmap/map_api.py)
- [cleanup_plan_api.py](../src/mailmap/cleanup_plan_api.py)
- [service.py](../src/mailmap/service.py)
- [test_base_segura_safety.py](../tests/test_base_segura_safety.py)
- [test_gmail_session.py](../tests/test_gmail_session.py)

## 2. Puerta 0 de la ejecución original de Fase A

Esta sección conserva la fotografía histórica de la ejecución original realizada
en el worktree `a0ea`. No describe el checkout usado para las correcciones
posteriores; su procedencia durable se registra en la sección 9.

### 2.1 Identidad del checkout histórico

| Comprobación | Resultado verificado |
| --- | --- |
| Ruta canónica redactada | %USERPROFILE%\.codex\worktrees\a0ea\mailcleanup |
| Rama | HEAD desacoplado; git branch --show-current no devolvió una rama |
| HEAD | 6f867544d8bc8319e082328163ea3684e24a86c0 |
| Commit | docs: accept action session and private vault contracts |
| Padre | 49e2e58 |
| Estado inicial | Limpio, incluidos no rastreados; sólo se informó branch.oid y branch.head |
| Base exigida | Coincidencia exacta con 6f867544d8bc8319e082328163ea3684e24a86c0 |
| Remoto | origin = https://github.com/blackat-systems/mailcleanup.git para fetch y push |

El remoto sólo fue inspeccionado. No se usó la red de Git ni se modificó el
estado remoto.

### 2.2 Worktrees observados

git worktree list --porcelain informó diez worktrees:

| Ruta | Rama o estado | HEAD |
| --- | --- | --- |
| %USERPROFILE%/Desktop/chatgptprojects/mailcleanup | main | 6f867544d8bc8319e082328163ea3684e24a86c0 |
| %USERPROFILE%/.codex/worktrees/460d/mailcleanup | codex/real-classification-domain | ba1efb4eeb2c80c0c973ee2c7c6dce12089576f2 |
| %USERPROFILE%/.codex/worktrees/4d09/mailcleanup | codex/real-plan-engine | e92a77a34f25e468be3056a4c65bef8d59fa4506 |
| %USERPROFILE%/.codex/worktrees/6d71/mailcleanup | codex/secure-gmail-session | 889d5f55acf1262aea722ace3d48a9064d06803f |
| %USERPROFILE%/.codex/worktrees/83bb/mailcleanup | codex/estudio-ui | a1cf0ff5b0ea71b6656a5bf14951df189f874cc4 |
| %USERPROFILE%/.codex/worktrees/9623/mailcleanup | codex/local-policy-memory | 663d8a99e94da9c40b5787bfb5f7a6b1e5f595b8 |
| %USERPROFILE%/.codex/worktrees/a0ea/mailcleanup | detached | 6f867544d8bc8319e082328163ea3684e24a86c0 |
| %USERPROFILE%/.codex/worktrees/ab1f/mailcleanup | codex/real-index-persistence | c3dc210e69e31eb252443d08558e78f756c719d2 |
| %USERPROFILE%/.codex/worktrees/bbbc/mailcleanup | codex/mapa-total-ui | 75764c9fbc66b2ba36bf1c3ccc5e8141e91f3130 |
| %USERPROFILE%/.codex/worktrees/f1b0/mailcleanup | codex/gmail-readonly-inventory | f510db0799c94d944f28d3dd71db8a9bd79ae648 |

Esta observación no inspeccionó ni incorporó cambios del worktree de MAIN.

## 3. A1 — Inventario reproducible

### 3.1 Método

Se usaron únicamente capacidades ya presentes:

- PowerShell y CIM/registro para SO, arquitectura y runtimes visibles;
- RuntimeInformation para distinguir descripción del runtime y arquitectura del
  proceso;
- el ejecutable python resuelto por PATH para consultar CPython, sqlite3,
  _sqlite3 y el motor enlazado;
- PRAGMA compile_options, sqlite_compileoption_used, PRAGMA temp_store,
  PRAGMA cipher_version y sqlite_source_id();
- Get-Command y los comandos de versión de herramientas visibles.

No se ejecutó setup.ps1 porque habría creado un entorno e instalado
dependencias. El .venv del repositorio no existía.

Sondeo de sistema equivalente al ejecutado:

    $os = Get-CimInstance Win32_OperatingSystem
    $cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    $PSVersionTable
    [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
    [System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture
    Get-Command python, py, node, npm, pnpm, git, sqlite3

Sondeo SQLite equivalente al ejecutado:

    import sqlite3
    connection = sqlite3.connect(":memory:")
    connection.execute("select sqlite_source_id()").fetchone()
    connection.execute("pragma compile_options").fetchall()
    connection.execute("pragma temp_store").fetchone()
    connection.execute("pragma cipher_version").fetchall()
    connection.execute(
        "select sqlite_compileoption_used(?)",
        ("SQLITE_HAS_CODEC",),
    ).fetchone()

### 3.2 Sistema operativo y proceso

| Campo | Resultado verificado |
| --- | --- |
| Edición reportada por CIM | Microsoft Windows 11 Pro Insider Preview |
| Versión / build | 10.0.26340 / 26340 |
| DisplayVersion / UBR | 26H2 / 9233 |
| Arquitectura del SO | 64-bit |
| Arquitectura del proceso | X64 |
| Cadena RuntimeInformation | Microsoft Windows 10.0.26340 |
| PowerShell | 7.6.4, edición Core |

La cadena RuntimeInformation usa la numeración interna Windows 10.0; no
contradice el caption Windows 11 obtenido por CIM. La build Insider observada
sirve para reproducir esta evidencia, no para afirmar compatibilidad de
producción.

### 3.3 CPython y SQLite enlazado

| Campo | Resultado verificado |
| --- | --- |
| Python | CPython 3.14.7 |
| Ejecutable | %LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe |
| Compilador | MSC v.1944 64 bit (AMD64) |
| Arquitectura / puntero | AMD64 / 64 bits |
| Cache tag | cpython-314 |
| SOABI | cp314-win_amd64 |
| Módulo Python | %LOCALAPPDATA%\Python\pythoncore-3.14-64\Lib\sqlite3\__init__.py |
| Extensión nativa cargada | %LOCALAPPDATA%\Python\pythoncore-3.14-64\DLLs\_sqlite3.pyd |
| SQLite runtime | 3.50.4 |
| sqlite_source_id() | 2025-07-30 19:33:53 4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 |
| PRAGMA temp_store | 0: usa el valor compilado |
| Valor compilado | TEMP_STORE=1 |
| PRAGMA cipher_version | Cero filas |
| Probes de codec | SQLITE_HAS_CODEC=0, SQLITE_ENABLE_CODEC=0, HAS_CODEC=0 y CODEC=0 |

Las rutas de runtime se expresan de forma portable con `%LOCALAPPDATA%`. Sólo se
redactó el segmento personal del perfil; no se alteraron versión, arquitectura,
módulos, hashes, salidas técnicas ni ningún otro hecho observado.

### 3.3.1 Frontera de runtime y ABI

Se conservan dos inventarios ambientales observados, con procedencia distinta:

| Entorno inventariado | CPython | SQLite | Alcance de la evidencia |
| --- | --- | --- | --- |
| PATH de este worktree durante A1–A2 | 3.14.7 | 3.50.4 | Motor usado por la prueba negativa A2 |
| Entorno de proyecto MAIN conocido por auditoría | 3.12.13 | 3.53.1 | Inventario heredado de MAIN; no fue reejecutado en esta corrección |

Ambos son inventarios ambientales. Ninguno fija por sí solo el runtime, ABI ni
matriz de distribución del producto. `pyproject.toml` declara Python `>=3.11` y
la configuración de mypy apunta a 3.11, pero tampoco selecciona una versión
exacta de CPython ni un ABI nativo.

`cp314-win_amd64` puede tratarse únicamente como un target de laboratorio
observado. No es una matriz aceptada. La versión exacta de CPython y el ABI de
la Fase B permanecen **PENDIENTES — STOP POINT** y requieren una decisión de
MAIN/Joa antes de adquirir o compilar cualquier candidato. No corresponde
repetir A1–A3 sólo para volver a obtener estos datos.

Opciones completas devueltas por PRAGMA compile_options:

    ATOMIC_INTRINSICS=0
    COMPILER=msvc-1944
    DEFAULT_AUTOVACUUM
    DEFAULT_CACHE_SIZE=-2000
    DEFAULT_FILE_FORMAT=4
    DEFAULT_JOURNAL_SIZE_LIMIT=-1
    DEFAULT_MMAP_SIZE=0
    DEFAULT_PAGE_SIZE=4096
    DEFAULT_PCACHE_INITSZ=20
    DEFAULT_RECURSIVE_TRIGGERS
    DEFAULT_SECTOR_SIZE=4096
    DEFAULT_SYNCHRONOUS=2
    DEFAULT_WAL_AUTOCHECKPOINT=1000
    DEFAULT_WAL_SYNCHRONOUS=2
    DEFAULT_WORKER_THREADS=0
    DIRECT_OVERFLOW_READ
    ENABLE_FTS3
    ENABLE_FTS4
    ENABLE_FTS5
    ENABLE_MATH_FUNCTIONS
    ENABLE_RTREE
    MALLOC_SOFT_LIMIT=1024
    MAX_ATTACHED=10
    MAX_COLUMN=2000
    MAX_COMPOUND_SELECT=500
    MAX_DEFAULT_PAGE_SIZE=8192
    MAX_EXPR_DEPTH=1000
    MAX_FUNCTION_ARG=1000
    MAX_LENGTH=1000000000
    MAX_LIKE_PATTERN_LENGTH=50000
    MAX_MMAP_SIZE=0x7fff0000
    MAX_PAGE_COUNT=0xfffffffe
    MAX_PAGE_SIZE=65536
    MAX_SQL_LENGTH=1000000000
    MAX_TRIGGER_DEPTH=1000
    MAX_VARIABLE_NUMBER=32766
    MAX_VDBE_OP=250000000
    MAX_WORKER_THREADS=8
    MUTEX_W32
    OMIT_AUTOINIT
    SYSTEM_MALLOC
    TEMP_STORE=1
    THREADSAFE=1

VERIFICADO: éste es el motor usado por el python disponible durante A2.

INFERIDO: la suma de módulo nativo, source id, compile options, ausencia de
respuesta de cipher y prueba de bytes es consistente con SQLite estándar sin
codec. Ningún probe aislado se trata como prueba universal de ausencia.

PENDIENTE: un candidato futuro deberá atestar su propio módulo, source id,
compile options, biblioteca criptográfica y configuración efectiva. No puede
heredar esta evidencia.

### 3.4 Herramientas visibles

| Herramienta | Estado verificado |
| --- | --- |
| python / py | 3.14.7 |
| node | v24.20.0 |
| npm | 11.19.0 |
| pnpm | 11.19.0 |
| git | 2.55.0.windows.4 |
| sqlite3 CLI | 3.50.6, ejecutable de Android SDK y 32-bit |
| dotnet, cmake, ninja | No resueltos por PATH |
| cl, clang, gcc | No resueltos por PATH |
| cargo, rustc, uv, msbuild | No resueltos por PATH |
| gpg, openssl, signtool | No resueltos por PATH |
| dumpbin, vswhere | No resueltos por PATH |
| make, nmake, tclsh, 7z | No resueltos por PATH |

El sqlite3 CLI visible no es el motor enlazado por CPython: pertenece al Android
SDK, es 32-bit y reporta otra versión. No se usó para A2. La ausencia por PATH
es una fotografía del entorno actual, no prueba de que una herramienta no
exista en otra ubicación.

## 4. A2 — Prueba negativa con SQLite estándar

### 4.1 Objetivo y límites

El objetivo fue demostrar con canarios sintéticos si SQLite estándar deja
bytes legibles en artefactos persistentes normales. No se usaron datos privados
ni contenido de correo. Los tres canarios fueron identificadores ASCII
neutrales creados sólo para esta prueba.

La prueba se ejecutó dentro de un directorio generado por tempfile bajo el
directorio temporal del usuario. Antes de eliminarlo se verificó:

- que su padre resuelto fuera exactamente tempfile.gettempdir();
- que su nombre empezara con mailcleanup-c4p-phase-a-.

No se escanearon directorios ajenos ni se hizo una eliminación amplia.

### 4.2 Script ejecutado

Comando de invocación:

    @'
    # contenido Python siguiente
    '@ | python -

Contenido Python ejecutado:

    import hashlib
    import json
    import shutil
    import sqlite3
    import tempfile
    from pathlib import Path

    PREFIX = "mailcleanup-c4p-phase-a-"
    EXPECTED_PARENT = Path(tempfile.gettempdir()).resolve()
    ROOT = Path(tempfile.mkdtemp(prefix=PREFIX)).resolve()
    CANARIES = {
        "main": b"MC4P-A2-DB-CANARY-7E4C1B9D",
        "wal": b"MC4P-A2-WAL-CANARY-6A2F8D3C",
        "journal": b"MC4P-A2-JOURNAL-CANARY-91B7E5A4",
    }

    def inspect(path: Path, canary: bytes) -> dict[str, object]:
        payload = path.read_bytes()
        return {
            "path": str(path),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "canary_ascii": canary.decode("ascii"),
            "canary_count": payload.count(canary),
            "first_offset": payload.find(canary),
        }

    result: dict[str, object] = {
        "root": str(ROOT),
        "expected_parent": str(EXPECTED_PARENT),
        "root_parent_verified": ROOT.parent == EXPECTED_PARENT,
        "sqlite_runtime": sqlite3.sqlite_version,
    }
    cleanup_error: str | None = None
    try:
        main_path = ROOT / "standard-main.sqlite"
        connection = sqlite3.connect(main_path)
        connection.execute("CREATE TABLE evidence(value BLOB NOT NULL)")
        connection.execute(
            "INSERT INTO evidence(value) VALUES (?)",
            (CANARIES["main"],),
        )
        connection.commit()
        connection.close()
        result["main"] = inspect(main_path, CANARIES["main"])

        wal_path = ROOT / "standard-wal.sqlite"
        connection = sqlite3.connect(wal_path)
        journal_mode = connection.execute(
            "PRAGMA journal_mode=WAL"
        ).fetchone()[0]
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE evidence(value BLOB NOT NULL)")
        connection.commit()
        connection.execute(
            "INSERT INTO evidence(value) VALUES (?)",
            (CANARIES["wal"],),
        )
        connection.commit()
        result["wal"] = {
            "journal_mode": journal_mode,
            "wal_autocheckpoint": connection.execute(
                "PRAGMA wal_autocheckpoint"
            ).fetchone()[0],
            "connection_open_during_scan": True,
            "checkpoint_called_before_scan": False,
            **inspect(Path(f"{wal_path}-wal"), CANARIES["wal"]),
        }
        connection.close()

        rollback_path = ROOT / "standard-rollback.sqlite"
        connection = sqlite3.connect(rollback_path)
        journal_mode = connection.execute(
            "PRAGMA journal_mode=DELETE"
        ).fetchone()[0]
        connection.execute("CREATE TABLE evidence(value BLOB NOT NULL)")
        connection.execute(
            "INSERT INTO evidence(value) VALUES (?)",
            (CANARIES["journal"],),
        )
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE evidence SET value = ?",
            (b"MC4P-A2-ROLLBACK-REPLACEMENT-2C8F4D6A",),
        )
        result["rollback_journal"] = {
            "journal_mode": journal_mode,
            "transaction_open_during_scan": connection.in_transaction,
            **inspect(
                Path(f"{rollback_path}-journal"),
                CANARIES["journal"],
            ),
        }
        connection.rollback()
        connection.close()
    finally:
        if (
            ROOT.parent != EXPECTED_PARENT
            or not ROOT.name.startswith(PREFIX)
        ):
            cleanup_error = "cleanup target validation failed"
        else:
            try:
                shutil.rmtree(ROOT)
            except Exception as exc:
                cleanup_error = f"{type(exc).__name__}: {exc}"
        result["cleanup"] = {
            "attempted_exact_root": str(ROOT),
            "root_exists_after_cleanup": ROOT.exists(),
            "error": cleanup_error,
        }

    print(json.dumps(result, indent=2))

### 4.3 Resultado exacto observado

Directorio temporal:

    %TEMP%\mailcleanup-c4p-phase-a-<id>

La forma portable conserva la raíz temporal, el prefijo y el carácter opaco del
sufijo observados. No modifica tamaños, hashes, conteos, offsets ni el resultado
del cleanup de esa corrida.

| Superficie | Estado durante scan | Tamaño | SHA-256 observado | Canario | Conteo | Primer offset |
| --- | --- | ---: | --- | --- | ---: | ---: |
| Base principal | Conexión cerrada después de commit | 8192 | 9f2fdfa23a450dc909f0d567b5626b71364d81454fb6a9d88734915c2b1e2be4 | MC4P-A2-DB-CANARY-7E4C1B9D | 1 | 8166 |
| WAL | journal_mode=wal, conexión abierta, autocheckpoint=0, sin checkpoint previo | 12392 | 9e30d5997dd3842d18cd2a93bace25d21028679b99d12538ec7ddf9683ee61c6 | MC4P-A2-WAL-CANARY-6A2F8D3C | 1 | 12365 |
| Rollback journal | journal_mode=delete, transacción abierta | 4616 | 8503eb818247d33ca06496417ff0639aef1b8618b246a98f7e40c849f902e0b3 | MC4P-A2-JOURNAL-CANARY-91B7E5A4 | 1 | 4581 |

Los hashes identifican los bytes observados en esta corrida; no se proponen
como hashes reproducibles de SQLite.

Cleanup exacto:

| Campo | Resultado |
| --- | --- |
| Padre temporal verificado | true |
| Eliminación intentada sólo sobre la raíz exacta | true |
| La raíz existe después del cleanup | false |
| Error de cleanup | null |

### 4.4 Interpretación

VERIFICADO: el canario estuvo en claro en DB, WAL y rollback journal. El
rollback journal contenía la preimagen de la página durante la transacción, que
es precisamente la superficie que debía observarse.

INFERIDO: el SQLite estándar disponible es incompatible con la exigencia C4-P
de cifrado autenticado de la bóveda y sus artefactos persistentes.

PENDIENTE: A2 no estudió SHM, temporales de sort/statement, backups, staging de
migraciones, memoria o crash recovery. Esas superficies deben formar parte del
harness de un proveedor candidato. No hacen falta para sostener la conclusión
negativa ya demostrada.

## 5. A3 — Superficie actual de MailCleanup

La inspección fue estática. No se inició la aplicación ni se invocó una ruta.

| Área | Evidencia verificada | Consecuencia |
| --- | --- | --- |
| Persistencia | repository.py importa sqlite3 y Repository abre con sqlite3.connect(self.path) | Camino único actual hacia SQLite estándar |
| Abstracción de proveedor | No existe fábrica, adapter o binding intercambiable | C4-P no está implementada |
| Dependencias | pyproject.toml no declara SQLCipher, SEE, APSW ni binding alternativo | No hay proveedor cifrado instalado por el proyecto |
| DPAPI | windows_secret_store.py llama CryptProtectData y CryptUnprotectData mediante ctypes | Primitiva concreta, pero limitada a un envelope pequeño |
| Cableado DPAPI | api.py y main.py no instancian WindowsSecretStore, WindowsDpapiProtector ni SecureGmailSession | La primitiva está dormida |
| Windows Hello | Cero coincidencias de UserConsentVerifier, UserConsentVerifierInterop o APIs equivalentes | Contrato documental, no implementación |
| Broker / IPC | Cero coincidencias de broker, CreatePipe, CreateNamedPipe o transporte IPC | No hay boundary de proceso |
| D2 / D3 | oauth_session.py y gmail_inventory.py definen puertos inyectables; las pruebas usan dobles | Scaffolds, no adaptadores productivos |
| Gmail / red | No hay cliente productivo Google/Gmail ni cliente HTTP/socket saliente en src/mailmap | Sin ruta externa operativa |
| API activa | v1, v2 y v3 sirven proyecciones y planes locales sintéticos; capacidades reales son false | canExecute permanece false |
| Frontend | Usa credentials: omit y rechaza envelopes no sintéticos o ejecutables | No habilita capacidad real |
| Empaquetado | setuptools expone un script Python; Vite produce web; Uvicorn escucha 127.0.0.1:8765 | No hay launcher desktop empaquetado |
| Artefactos nativos | Cero DLL, PYD, EXE, MSI, MSIX, APPX o wheel versionados | No hay candidato binario oculto |

Búsquedas exactas relevantes, sobre código/configuración y excluyendo
documentación, devolvieron cero coincidencias:

- SQLCipher, pysqlcipher, sqlcipher3, sqlite3_key, sqlite3_rekey, PRAGMA key,
  PRAGMA rekey, SQLite SEE, wxSQLite3 y SQLITE_HAS_CODEC;
- Windows Hello, UserConsentVerifier y Windows.Security.Credentials.UI;
- broker, NamedPipe, CreateNamedPipe, CreatePipe, AnonymousPipe e IPC;
- PyInstaller, Nuitka, cx_Freeze, Briefcase, electron-builder, Tauri, MSIX,
  APPX, WiX, NSIS, Squirrel e Inno Setup.

El paquete electron-to-chromium del lockfile es dato de browserslist; no es el
runtime Electron.

### 5.1 Matiz obligatorio sobre DPAPI

No es correcto resumir A3 como “no existe nada real”. Sí existe código que llama
DPAPI:

- carga crypt32 y kernel32;
- implementa WindowsDpapiProtector;
- implementa WindowsSecretStore;
- persiste un envelope de credenciales pequeño.

Tampoco es correcto tratarlo como C4-P:

- no cifra SQLite;
- no implementa Windows Hello;
- no implementa broker o IPC;
- no está conectado al servidor activo;
- usa actualmente LOCALAPPDATA, no la cadena completa de known folder, DACL y
  rechazo de reparse points exigida antes de uso real.

VERIFICADO: tests/test_gmail_session.py incluye un roundtrip DPAPI real en
Windows en sus líneas 745–758. Esa prueba fue leída, no ejecutada, porque la
Fase A prohíbe invocar DPAPI real.

## 6. A4 — Matriz documental de proveedores

Corte documental: 1 de septiembre de 2026. Se consultaron fuentes oficiales del
proveedor, SQLite, Microsoft, GitHub o PyPI según correspondía. No se adquirió,
descargó ni ejecutó ningún artefacto.

### 6.1 Comparación de exactamente cuatro opciones

| Opción | Procedencia y licencia | Artefacto / firma | Integración y ABI | Vía de clave | Estado |
| --- | --- | --- | --- | --- | --- |
| 1. SQLCipher Community | Fuente oficial Zetetic; BSD-3-Clause con avisos | Source archive y firma PGP separada | Hay que construir y fijar el artefacto PE o LIB integrado y demostrar ABI CPython | API C sqlite3_key recibe puntero y longitud | No aprobada |
| 2. SQLCipher Commercial | Binarios oficiales Zetetic; licencia propietaria por app/plataforma | ZIP comercial con firma separada desde portal; contenido no adquirido | DLL/lib x86, x64 y arm64; binding Python sigue fuera del soporte del core | Misma API C, más gestión separada de licencia | No aprobada |
| 3. SQLite SEE | Fuente privada oficial Hwaci/SQLite; licencia propietaria | Entrega source-only; firma/hashes públicos insuficientes | Amalgamation de reemplazo; binding CPython y distribución deben resolverse | sqlite3_key_v3 recibe puntero, longitud y codec | No aprobada |
| 4. Bindings Python terceros | pysqlcipher3 o sqlcipher3; mantenimiento/licencia heterogéneos | Wheels con hashes PyPI, sin atestación suficiente observada | Riesgo de wheel autocontenido y dos núcleos SQLite | API pública documentada privilegia PRAGMA key string | No aprobada |

### 6.2 Opción 1 — SQLCipher Community Edition

VERIFICADO:

- El repositorio oficial [sqlcipher/sqlcipher](https://github.com/sqlcipher/sqlcipher)
  es un fork autónomo de SQLite mantenido por Zetetic.
- La edición Community usa licencia BSD-style/BSD-3-Clause y requiere conservar
  avisos. Véanse [Community Edition](https://www.zetetic.net/sqlcipher/community/)
  y [licencias oficiales](https://www.zetetic.net/sqlcipher/license/).
- Zetetic publica archivos fuente y firmas PGP separadas. La
  [guía oficial de verificación](https://www.zetetic.net/sqlcipher/verify/)
  documenta la huella y el procedimiento.
- La [API oficial](https://www.zetetic.net/sqlcipher/sqlcipher-api/) expone
  sqlite3_key y sqlite3_key_v2 con const void * y longitud int.
- La compilación requiere SQLITE_HAS_CODEC, una política de TEMP_STORE
  compatible y un proveedor criptográfico. El
  [README oficial](https://github.com/sqlcipher/sqlcipher#compiling) enumera
  las condiciones.
- SQLCipher cifra DB, rollback journal, WAL y statement journal, pero no promete
  cifrar todos los transitorios; el
  [diseño oficial](https://www.zetetic.net/sqlcipher/design/) exige evitar
  temporales sensibles en disco.
- Zetetic declara que no ofrece una solución Python turnkey en su
  [guía de integración Python](https://www.zetetic.net/sqlcipher/sqlcipher-python/).

INFERIDO:

- Podría satisfacer bytes más longitud sólo con un adapter que llame la API C
  directamente.
- Traslada a MailCleanup la compilación reproducible, el proveedor
  criptográfico, el binding, la firma del binario y la compatibilidad ABI.

PENDIENTE:

- tag, source id, hashes y manifest inmutables;
- build reproducible Windows;
- compile options y TEMP_STORE efectivos;
- EXE/DLL/PYD o LIB integrada, Authenticode cuando aplique, SBOM y dependencias;
- CPython exacto, único núcleo SQLite y harness completo.

### 6.3 Opción 2 — SQLCipher Commercial Edition

VERIFICADO:

- [SQLCipher for Windows](https://www.zetetic.net/sqlcipher/sqlcipher-windows/)
  describe paquetes oficiales con headers y bibliotecas dinámicas/estáticas
  para x86, x64 y arm64.
- La [edición Commercial](https://www.zetetic.net/sqlcipher/commercial/) se
  licencia por aplicación y plataforma. La oferta pública observada partía de
  USD 999 por aplicación/año; precio y términos deben revalidarse antes de una
  decisión.
- Zetetic afirma que los paquetes incluyen firma separada, distribuida desde el
  portal de cliente, según su
  [guía de verificación](https://www.zetetic.net/sqlcipher/verify/).
- Conserva la API C de bytes más longitud.
- La guía Python remite a un wrapper tercero y excluye esa frontera del soporte
  del core.

INFERIDO:

- Reduce el trabajo de compilar el core, pero no prueba el binding CPython, el
  núcleo único, la vía segura de clave ni la firma individual de DLL/PYD.
- La firma PGP del paquete no equivale automáticamente a Authenticode de cada
  artefacto PE ejecutable o cargable contenido.

PENDIENTE:

- paquete, hash, firma, contenido, SBOM, source id y compile options reales;
- licencia y tratamiento separado del código de licencia;
- ABI CPython, carga DLL, único núcleo y llamada directa a sqlite3_key;
- harness completo.

### 6.4 Opción 3 — SQLite Encryption Extension

VERIFICADO:

- SEE es una extensión propietaria distribuida por Hwaci/SQLite desde un
  repositorio Fossil privado. Véase el
  [portal oficial SEE](https://sqlite.org/see/doc/trunk/www/index.wiki).
- La [compra oficial](https://sqlite.org/purchase/see) publicaba una licencia
  perpetua source-only de USD 2.000 por equipo; el
  [acuerdo SEE](https://sqlite.org/com/license-see.html) condiciona la
  distribución.
- La [documentación SEE](https://sqlite.org/see/doc/release/www/readme.wiki)
  describe una amalgamation de reemplazo y sqlite3_key_v3 con puntero,
  longitud y codec.
- SEE no es un perfil único: ofrece variantes OFB, CCM, GCM y opciones legadas.
- Declara cifrado de DB, rollback journal y WAL, pero no de tablas TEMP; los
  datos están en claro en memoria y parte del header permanece legible. La
  documentación pública revisada no afirma cobertura de SHM.

INFERIDO:

- Python exigiría reconstruir un binding contra SEE o aislarlo detrás de un
  broker nativo.
- El cumplimiento depende de la variante exacta; no puede evaluarse “SEE” como
  una configuración única.

PENDIENTE:

- acceso licenciado, hashes, firma y SBOM del entregable;
- variante, autenticación, nonce, formato, migración y distribución permitida;
- TEMP y SHM;
- binding CPython, ABI, núcleo único y firma del binario resultante.

STOP POINT: la falta de cifrado de TEMP bloquea esta opción mientras no se
demuestren conjuntamente temp_store=MEMORY, ausencia de spill a disco y
canarios limpios en cada archivo temporal observable. El plaintext en memoria debe
quedar explícitamente dentro del modelo de amenazas; no se confunde con un
archivo TEMP persistente.

### 6.5 Opción 4 — Bindings Python de terceros

VERIFICADO:

- Zetetic remite a
  [rigglemania/pysqlcipher3](https://github.com/rigglemania/pysqlcipher3),
  cuyo repositorio se declara beta, no mantenido activamente y potencialmente
  vulnerable. Su ejemplo usa PRAGMA key con string.
- [coleifer/sqlcipher3](https://github.com/coleifer/sqlcipher3) es otro binding
  DB-API 2.0. La
  [versión 0.6.2 en PyPI](https://pypi.org/project/sqlcipher3/0.6.2/) publica
  wheels autocontenidos, incluidos CPython 3.14 para Windows x64, con hashes
  SHA-256.
- PyPI informó que esos archivos no se cargaron con Trusted Publishing. No se
  observó atestación Sigstore.
- El repositorio muestra licencia zlib mientras los metadatos PyPI muestran
  MIT; la divergencia debe resolverse.

INFERIDO:

- Un wheel autocontenido puede cargar un segundo core SQLite junto a _sqlite3.
- Los hashes de PyPI prueban identidad contra el índice, no por sí solos
  autoría, reproducibilidad o cadena de suministro completa.
- No hay evidencia documental suficiente de una API Python que entregue la
  clave directamente como bytes más longitud a sqlite3_key.

PENDIENTE:

- mantenimiento, licencia efectiva y política de vulnerabilidades;
- wheel real, símbolos, DLL transitivas, SBOM, firma y reproducibilidad;
- ABI exacto, único núcleo SQLite y atestación runtime;
- vía de clave sin PRAGMA, SQL, string, URI, entorno, argv o logs.

### 6.6 Decisión de A4

No se selecciona ninguna opción.

Stop points comunes antes de cualquier Fase B:

- artefacto no fijado por tag, source id y hash;
- firma de origen no verificable;
- licencia no resuelta;
- ABI CPython o arquitectura no demostrada;
- más de un núcleo SQLite en el proceso autorizado;
- compile options o biblioteca criptográfica no atestadas;
- clave convertida a string o pasada por una superficie textual;
- imposibilidad de observar DB, WAL, journal, SHM, temporales y backups;
- ausencia de fallo cerrado frente a clave incorrecta o corrupción;
- dependencia de una afirmación comercial sin validación local.

## 7. A5 — Diseño del harness futuro

Esta sección es PROPUESTA. No se implementó ni ejecutó.

### 7.1 Principios de aceptación

Un candidato sólo podría avanzar si demuestra conjuntamente:

1. procedencia y licencia aceptables;
2. build propio reproducible o paquete oficial inmutable, autenticado y
   verificable;
3. ABI exacto y un único núcleo SQLite;
4. clave binaria entregada por una frontera no textual;
5. atestación runtime antes de abrir el schema;
6. ausencia de canarios en todas las superficies persistentes observables;
7. lectura correcta con clave válida y fallo cerrado con clave ausente,
   incorrecta, artefacto alterado o configuración divergente;
8. migración por generaciones, recovery y actualización sin fallback a
   plaintext;
9. rendimiento medido sin debilitar seguridad;
10. cleanup exacto y auditable.

La ausencia de canarios es una condición necesaria. No reemplaza revisión
criptográfica, autenticación, procedencia, recovery ni modelo de amenazas.

### 7.2 Adquisición, procedencia y SBOM

El harness debería:

- adquirir una versión exacta desde la fuente oficial;
- verificar firma del proveedor y hash antes de extraer;
- conservar manifest con URL, fecha, tag, commit/source id, hashes, huella de la
  clave firmante y licencia;
- registrar compilador, Windows SDK, CPython, SQLite, proveedor criptográfico y
  todas las dependencias;
- generar SBOM SPDX o CycloneDX;
- verificar Authenticode de cada EXE, DLL o PYD distribuido y registrar subject,
  issuer, timestamp y digest; fijar por hash las LIB estáticas;
- operar offline después de la adquisición verificada;
- fallar si el artefacto o manifest difiere.

Para builds propios:

- ejecutar dos builds limpios desde fuentes fijadas;
- comparar hashes binarios o documentar y eliminar causas de no determinismo;
- impedir descarga dinámica durante el build;
- conservar comandos, variables permitidas y logs sin secretos.

Para una distribución propietaria sin fuentes reproducibles:

- no afirmar reproducibilidad que MailCleanup no pueda demostrar;
- exigir paquete oficial inmutable, firma del proveedor y hash fijado;
- verificar todos los artefactos PE y dependencias contenidos;
- obtener o reconstruir una SBOM suficiente para revisión;
- tratar la imposibilidad de verificar procedencia o composición como stop
  point.

### 7.3 ABI y núcleo SQLite único

El target `cp314-win_amd64` fue observado como posibilidad de laboratorio en el
PATH de A1. No está aceptado como ABI de Fase B ni decide la matriz soportada del
producto. El entorno de proyecto MAIN conocido por auditoría usa CPython 3.12.13
y SQLite 3.53.1; esa segunda fotografía tampoco fija el ABI. La selección exacta
permanece **PENDIENTE — STOP POINT** hasta una decisión de MAIN/Joa anterior a
cualquier adquisición o compilación.

El harness debería:

- comprobar arquitectura, imports, exports y runtime de cada EXE/DLL/PYD;
- fijar por hash cualquier LIB estática antes de integrarla al PE final;
- cargar el candidato en un proceso aislado;
- enumerar módulos cargados, rutas resueltas, hashes y firmas;
- identificar sqlite3_libversion, sqlite3_sourceid y símbolos de codec;
- demostrar que todas las conexiones de la bóveda pasan por una única fábrica;
- impedir que ese proceso cargue también el _sqlite3 estándar;
- fallar si aparecen dos cores SQLite, un DLL no fijado o una ruta inesperada.

La coexistencia en procesos distintos sólo podría aceptarse con una frontera
IPC explícita y sin acceso cruzado a la bóveda.

### 7.4 Vía de clave

C4-P parte de una DEK aleatoria de 256 bits. No debe confundirse con una
passphrase sometida a KDF.

El adapter futuro debería:

- recibir la DEK como buffer mutable de bytes y longitud explícita;
- llamar sqlite3_key, sqlite3_key_v2 o equivalente nativo directamente;
- no convertirla a str;
- no usar PRAGMA key, SQL, URI, DSN, entorno, argv, archivo, clipboard o log;
- no incluir la DEK en excepciones, telemetry, dumps o repr;
- borrar el buffer temporal propio al terminar, sin prometer borrar copias que
  controle el runtime o proveedor;
- demostrar documental y empíricamente si la API interpreta esos 32 bytes como
  raw key o como passphrase.

STOP POINT: si el proveedor o binding sólo ofrece una ruta textual, no sigue a
pruebas con una DEK real.

### 7.5 Atestación runtime

Antes de abrir el schema, el proceso debería verificar en memoria la ruta
absoluta resuelta de cada módulo nativo contra la allowlist. La evidencia durable
debería emitir un registro no secreto con:

- ruta canónica redactada o relativa, hash y firma de cada módulo nativo;
- arquitectura y ABI;
- SQLite version y source id;
- versión del proveedor y del backend criptográfico;
- compile options completas;
- temp_store efectivo;
- codec y algoritmo efectivos;
- autenticación efectiva mediante HMAC, tag o equivalente, o evidencia expresa
  de que no aplica;
- semántica de clave raw frente a passphrase/KDF;
- parámetros efectivos de página, formato y compatibilidad;
- una prueba positiva de cifrado y la marca “no aplica” respaldada cuando una
  opción no exponga un concepto con el nombre de otro proveedor;
- manifest esperado;
- confirmación de núcleo único.

La comprobación in-memory conserva la ruta absoluta exacta. El registro durable
nunca incorpora el nombre del perfil personal: usa la forma canónica redactada
o relativa junto con hash, firma y manifest, sin debilitar la comparación contra
la allowlist.

El registro debe compararse con una allowlist inmutable. Una divergencia aborta
antes de crear, migrar o reparar una base.

### 7.6 Canarios, materialización y superficies

Usar datos completamente sintéticos y al menos:

- canario ASCII;
- canario binario con bytes nulos y altos;
- canario UTF-8 multibyte;
- variantes exactas de encoding sólo donde el camino pueda transformarlas.

Antes de ejecutar cada workload, el harness debe declarar su matriz de
superficies aplicables. Por cada superficie declarada aplicable debe existir un
control positivo de materialización: la corrida debe forzar el estado que crea
el artefacto, comprobar que efectivamente apareció y demostrar que el
inventario y el escáner lo observaron. Si un artefacto esperado nunca fue
creado, la corrida falla; un archivo inexistente nunca se interpreta como
“ausencia de plaintext”.

La matriz y los workloads deben cubrir, cuando corresponda:

- DB principal después de close;
- WAL con conexión abierta y antes de checkpoint;
- rollback journal durante transacción;
- SHM mientras WAL está activo;
- statement journal materializado por un workload específico;
- temporales de sort, índices y tablas forzados bajo una raíz TEMP aislada;
- staging y generaciones de creación o migración;
- backups, copias y exports sólo si una capacidad autorizada los vuelve
  aplicables;
- recovery, generaciones parciales y crash leftovers producidos mediante
  inyección controlada de fallas;
- archivos truncados y nombres alternativos esperables para el candidato.

Cada workload debe inventariar la raíz aislada allowlisted antes, durante y
después de la operación. Para cada artefacto debe registrar ruta relativa a esa
raíz, tamaño, hash, momento y transición de lifecycle, conteos de cada canario y
todos sus offsets. El harness debe observar o prevenir escrituras fuera de la
raíz allowlisted y fallar si detecta una; esto no autoriza escanear
indiscriminadamente el equipo.

SHM exige tratamiento explícito: el workload WAL debe comprobar su
materialización cuando corresponda, su DACL correcta y restrictiva, el lifecycle
esperado y la ausencia de datos de aplicación en sus bytes. La mera ausencia de canarios
con un SHM inexistente, no observado o con permisos no verificados no es un
resultado válido.

Todo “NO APLICA” debe incluir una justificación explícita y verificable basada
en la configuración efectiva, el workload y el lifecycle del candidato. No
basta con que el proveedor no documente una superficie o que el archivo no haya
aparecido accidentalmente.

El escáner debe calibrarse con un control negativo separado sobre SQLite
estándar: los mismos canarios y workloads aplicables deben materializar los
artefactos esperados y el escáner debe encontrarlos. Si ese control no detecta
los canarios conocidos, no puede usarse para declarar limpio al candidato.

Además:

- clave correcta abre y valida el contenido;
- sin clave y con clave incorrecta fallan;
- cambiar un byte autenticado provoca rechazo;
- no se crea una base nueva sobre un path existente ilegible;
- no hay fallback automático, reparación destructiva ni downgrade silencioso.

### 7.6.1 Detección de filtración de DEK sintética

Cada corrida futura del harness debe usar una DEK de laboratorio exclusiva,
completamente sintética, de 32 bytes y nunca real. Esa DEK actúa únicamente como
canario de filtración y no autoriza crear ni usar una clave productiva.

El harness debe generar por sí mismo el conjunto de patrones: la secuencia raw
exacta de los 32 bytes y sus representaciones textuales previsibles, incluidas
hexadecimal y Base64, sin inventar passphrases. La validación separa dos fases y
dos raíces allowlisted distintas:

1. **Calibración sintética.** Crear una raíz exclusiva de calibración, plantar
   allí la DEK raw y cada representación generada y exigir que el detector las
   encuentre todas. Los controles deben incluir coincidencias divididas entre
   chunks y coincidencias ubicadas después del límite de retención de evidencia.
   Al terminar, cerrar todos sus handles, registrar el resultado, borrar sólo
   esa raíz exacta y confirmar su ausencia antes de evaluar el candidato.
2. **Evaluación candidata.** Crear después una raíz candidata nueva, vacía y
   validada. No copiar controles, exceptuar archivos conocidos ni excluir
   subárboles dentro de ella. Cualquier coincidencia en esta fase es un fallo del
   candidato. Su resultado se registra separado del resultado de calibración.

En ambas fases, el detector debe:

- inspeccionar DB, WAL, rollback journal, SHM, statement journals, temporales,
  staging, recovery, crash leftovers y cualquier otro artefacto dentro de la
  raíz allowlisted de esa fase;
- inspeccionar argv y entorno construidos para cada proceso del laboratorio;
- escanear todos los bytes observados de archivos, stdout, stderr, logs y
  excepciones serializadas antes de descartarlos;
- mantener estado incremental y un overlap mínimo de la longitud del patrón más
  largo menos uno entre chunks, para detectar coincidencias que crucen sus
  límites;
- aplicar el límite únicamente a la evidencia retenida, nunca a los bytes
  escaneados, y continuar escaneando y drenando después de alcanzar ese límite;
- contrastar cada byte contra el patrón raw y todas las representaciones
  textuales generadas por el harness;
- fallar cerrado ante cualquier coincidencia y conservar sólo evidencia
  genérica y redactada, nunca bytes de la DEK ni de sus representaciones.

El cleanup final debe cubrir las dos raíces exactas y verificar su ausencia; en
la calibración esto confirma el borrado ya realizado antes de crear la raíz
candidata. Ningún cleanup permite actuar fuera de esas raíces.

Esta prueba no promete detectar copias arbitrarias en memoria y no autoriza
escanear indiscriminadamente el equipo. Permanece como diseño futuro: no se
implementó ni ejecutó en Fase A.

### 7.7 Migraciones y crash recovery

La primera generación sensible debe nacer cifrada. No se acepta una migración
in-place que deje una base plaintext.

El harness debería:

- crear una generación nueva dentro de staging autorizado;
- copiar lógicamente dentro de transacciones verificables;
- validar schema, conteos, invariantes y autenticación;
- activar atómicamente sólo una generación completa;
- conservar la última generación completa ante crash;
- inyectar fallas antes y después de cada etapa durable;
- repetir fallas durante WAL, journal, checkpoint, rekey si existiera, rename y
  activación;
- demostrar recovery idempotente y ausencia de selección automática de una
  generación parcial.

No debe prometer sanitización física de sectores liberados, SSD o copias del
sistema. Debe evitar crear plaintext desde el principio.

### 7.8 Rendimiento

Con fixtures sintéticos representativos:

- medir apertura y cierre;
- transacciones pequeñas y por lote;
- consultas y paginación usadas por MailCleanup;
- checkpoint y recovery;
- p50/p95, CPU, memoria y crecimiento de DB/WAL;
- comparación con SQLite estándar sólo como baseline funcional.

Los umbrales de aceptación son PENDIENTES de decisión de producto. Una regresión
de rendimiento no habilita bajar autenticación, reutilizar claves, omitir sync
o permitir temporales plaintext.

### 7.9 Actualización y downgrade

El harness debería validar:

- versión N y N-1;
- compatibilidad de formato explícita;
- apertura controlada después de upgrade;
- rechazo de downgrade no soportado;
- actualización sólo con artefactos firmados y manifest permitido;
- SBOM y revisión de vulnerabilidades por release;
- inexistencia de fallback a sqlite3 estándar.

### 7.10 Cleanup

Cada corrida debería:

- usar una raíz temporal creada y validada por el harness;
- cerrar conexiones, handles, procesos y listeners;
- borrar sólo la raíz exacta;
- verificar que no queden DB, WAL, journal, SHM, temporales o procesos;
- informar fallas de cleanup como fallas de la corrida;
- conservar evidencia textual no sensible fuera de la raíz sólo si está
  autorizada.

### 7.11 Regresión negativa de herencia de handles

El harness futuro del IPC debe incluir una regresión negativa específica para
descendientes:

1. el launcher crea al hijo con la allowlist exacta de handles del protocolo;
2. durante bootstrap, el hijo quita inmediatamente la heredabilidad de sus
   propias copias y lo hace antes de crear cualquier descendiente;
3. antes de crear al nieto, el hijo comprueba mediante GetHandleInformation que
   ninguno de sus extremos del canal conserve HANDLE_FLAG_INHERIT;
4. el hijo crea un proceso nieto controlado deliberadamente con
   bInheritHandles=TRUE y sin una allowlist que oculte un defecto residual;
5. aun bajo esa condición adversarial, el nieto demuestra que no recibió ningún
   extremo del protocolo y que no puede leer ni escribir frames;
6. al cerrar los únicos extremos propietarios, el launcher y el hijo observan
   EOF dentro del timeout previsto y el nieto no mantiene vivo el canal;
7. un control del propio harness usa un handle sintético, deliberadamente
   heredable y sin secretos ni datos reales, para demostrar que la inspección
   detectaría una herencia efectiva.

La prueba falla si el nieto hereda un extremo, puede intercambiar un frame o
retiene EOF; también falla si se lo crea con bInheritHandles=FALSE, si una
allowlist vuelve trivial el resultado, si GetHandleInformation observa
HANDLE_FLAG_INHERIT residual, si el control sintético no es detectado o si queda
un duplicado no propio abierto.

Esta regresión permanece como diseño futuro: no se implementó ni ejecutó.

### 7.12 Regresión negativa de allowlist launcher→hijo

El harness futuro debe comprobar que PROC_THREAD_ATTRIBUTE_HANDLE_LIST limita la
herencia aun cuando existan otros handles heredables:

1. el launcher conserva abierto un handle sintético deliberadamente heredable
   que no integra la allowlist;
2. la allowlist se materializa como un array contiguo y estable equivalente a
   HANDLE inherited_handles[3], con exactamente hStdInput, hStdOutput y
   hStdError en ese orden;
3. lpValue apunta a inherited_handles y cbSize es exactamente
   3 * sizeof(HANDLE) al llamar UpdateProcThreadAttribute;
4. la identidad, dirección, tamaño y contenido de inherited_handles permanecen
   invariantes desde antes de UpdateProcThreadAttribute hasta después de
   DeleteProcThreadAttributeList;
5. la creación usa bInheritHandles=TRUE, STARTUPINFOEX inicializada y
   EXTENDED_STARTUPINFO_PRESENT;
6. el hijo recibe sólo los tres handles estándar allowlisted y el handle
   sintético externo no aparece ni puede usarse;
7. el control demuestra que el handle sintético habría sido heredable sin la
   restricción de la attribute list.

La prueba falla si lpValue no apunta a un array contiguo y estable, si ese array
no contiene exactamente tres HANDLE en el orden hStdInput, hStdOutput y
hStdError, si cbSize no es 3 * sizeof(HANDLE), si falta cualquiera de los tres
handles, si aparece uno adicional o si el almacenamiento desaparece, se mueve,
se reemplaza, cambia o se libera antes de DeleteProcThreadAttributeList. También
falla si falta EXTENDED_STARTUPINFO_PRESENT, si la attribute list no se
inicializó o aplicó, si bInheritHandles no es TRUE o si el hijo recibe cualquier
handle fuera de la lista exacta; si StartupInfo.cb no es
sizeof(STARTUPINFOEX), lpAttributeList no apunta al buffer inicializado, ese
buffer deja de existir antes de que CreateProcessW retorne o lpStartupInfo no
referencia la STARTUPINFOEX completa. El control usa sólo objetos sintéticos,
sin secretos ni datos reales, y permanece sin implementar ni ejecutar en Fase
A.

## 8. A6 — Diseño conceptual del IPC launcher–backend

Esta sección es PROPUESTA. No se creó launcher, backend hijo, pipe, broker,
capacidad ni proceso.

### 8.1 Comparación

| Opción | Ventaja | Costo / límite | Uso propuesto |
| --- | --- | --- | --- |
| Dos pipes anónimos | No publica nombre; encaja con un padre que crea un único hijo | Streams sin límites de mensaje y sin overlapped I/O nativo | Recomendación inicial |
| Named pipe por lanzamiento | Permite reconexión, procesos no relacionados, modo mensaje y overlapped | Superficie de nombre, ACL, suplantación del mismo usuario y lifecycle mayor | Sólo si aparece una necesidad demostrada |

Microsoft documenta que un canal bidireccional con pipes anónimos necesita dos
pipes, que su caso natural es padre–hijo, que no preserva límites de escritura y
que no ofrece overlapped I/O. Véanse
[Anonymous Pipe Operations](https://learn.microsoft.com/en-us/windows/win32/ipc/anonymous-pipe-operations),
[Pipe Handle Inheritance](https://learn.microsoft.com/en-us/windows/win32/ipc/pipe-handle-inheritance)
y [Windows IPC](https://learn.microsoft.com/en-us/windows/win32/ipc/interprocess-communications).

### 8.2 Recomendación conceptual

Para un launcher que crea y supervisa exactamente un backend hijo:

1. crear un pipe launcher→hijo y otro hijo→launcher;
2. asignar a hStdInput y hStdOutput únicamente los extremos exactos del
   protocolo destinados al hijo;
3. proporcionar siempre un hStdError válido, separado del framing y allowlisted,
   dirigido a un sink o pipe de diagnóstico seguro y acotado incluso cuando el
   hijo no emita logs; stderr nunca comparte hStdOutput ni stdout del protocolo;
4. inicializar a cero una STARTUPINFOEX y fijar
   StartupInfo.cb=sizeof(STARTUPINFOEX);
5. invocar primero InitializeProcThreadAttributeList con lpAttributeList=NULL
   sólo para obtener el tamaño requerido para un atributo; aceptar únicamente
   el resultado documentado de dimensionamiento, con retorno FALSE,
   ERROR_INSUFFICIENT_BUFFER y tamaño mayor que cero, y fallar cerrado ante
   cualquier otra combinación;
6. asignar un buffer del tamaño exacto informado y mantenerlo vivo hasta que
   CreateProcessW retorne;
7. asignar STARTUPINFOEX.lpAttributeList a ese buffer, ejecutar allí la
   inicialización final con InitializeProcThreadAttributeList y fallar cerrado
   si no concluye correctamente;
8. materializar la allowlist en almacenamiento estable y contiguo equivalente a
   HANDLE inherited_handles[3] = {hStdInput, hStdOutput, hStdError}; el array
   debe existir antes de UpdateProcThreadAttribute y no puede moverse,
   reemplazarse ni liberarse durante la creación;
9. llamar UpdateProcThreadAttribute con lpValue apuntando exactamente a
   inherited_handles y cbSize igual a 3 * sizeof(HANDLE), y fallar cerrado si la
   actualización falla;
10. tratar los tres handles, el array inherited_handles que contiene sus
    valores, el buffer de lpAttributeList y la propia STARTUPINFOEX como objetos
    distintos, cada uno con ownership y lifecycle explícitos; mantener el array
    vivo e invariable después del retorno de CreateProcessW y hasta ejecutar
    DeleteProcThreadAttributeList, y liberarlo sólo después de destruir la
    attribute list;
11. fijar StartupInfo.hStdInput, StartupInfo.hStdOutput, StartupInfo.hStdError y
   STARTF_USESTDHANDLES; comprobar que los tres handles son válidos y coinciden
   exactamente con la allowlist, manteniéndolos todavía no heredables;
12. pasar (LPSTARTUPINFO)&startupInfoEx como lpStartupInfo e incluir
    EXTENDED_STARTUPINFO_PRESENT en dwCreationFlags;
13. proporcionar un lpApplicationName no nulo con la ruta absoluta atestada del
    ejecutable. Si existe lpCommandLine, debe ser un buffer escribible, sin
    secretos y construido sin ambigüedad sobre qué ejecutable se inicia;
14. serializar la ventana de creación de procesos, salvo que toda creación
    concurrente use también una allowlist explícita;
15. marcar HANDLE_FLAG_INHERIT en esos tres handles sólo inmediatamente antes de
    CreateProcessW y comprobar que los tres quedaron efectivamente heredables;
16. llamar CreateProcessW con bInheritHandles=TRUE sólo después de completar y
    validar los pasos anteriores, manteniendo vivos STARTUPINFOEX, la attribute
    list, su buffer e inherited_handles hasta que la llamada retorne;
17. después del retorno, retirar inmediatamente los flags de herencia e invocar
    DeleteProcThreadAttributeList mientras STARTUPINFOEX, inherited_handles y el
    buffer de lpAttributeList siguen vivos; sólo después liberar el array y el
    buffer, y cerrar duplicados, extremos y handles temporales en orden de
    ownership, tanto en éxito como en error o cancelación. Aplicar el cleanup
    equivalente ante cada fallo anterior a CreateProcessW y conservar únicamente
    los handles de proceso o canal que su lifecycle todavía requiera;
18. durante bootstrap, el hijo quita inmediatamente HANDLE_FLAG_INHERIT de sus
    copias de hStdInput, hStdOutput y hStdError, antes de crear cualquier proceso
    descendiente;
19. launcher e hijo cierran inmediatamente todos los duplicados y extremos no
    propios, incluido hStdError según su lifecycle y los handles conservados sólo
    para la creación;
20. mantener abiertos únicamente los extremos propietarios necesarios para que
    el cierre sea observable como EOF y ningún descendiente retenga el canal;
21. conservar el handle del proceso creado durante su lifecycle autorizado;
22. enmarcar cada mensaje con magic, versión, rol, tipo, longitud máxima,
    request id y nonce por lanzamiento;
23. aplicar timeouts, correlación, orden esperado y fallo cerrado ante EOF,
    frame inválido, tamaño excesivo o replay;
24. usar hilos dedicados si la sincronía del pipe anónimo no alcanza.

Si hStdError usa un pipe, un lector dedicado debe drenarlo continuamente hasta
EOF. Limitar lo retenido nunca significa dejar de drenar: la captura aplica
redacción, límite de memoria, timeout, cierre y observación de EOF sin mezclar
stderr con los frames del protocolo ni permitir que el hijo quede bloqueado por
un buffer lleno. Como alternativa futura puede usarse un sink válido, no
bloqueante y sin persistencia sensible. Esta Fase A no selecciona entre pipe y
sink; sólo fija las invariantes.

CreateProcessW con bInheritHandles=true puede heredar todos los handles marcados.
La allowlist explícita reduce esa superficie. Véanse
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw),
[UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
y [SetHandleInformation](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-sethandleinformation).
El requisito de los tres handles estándar se apoya en
[STARTUPINFOW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-startupinfow).
Fuentes oficiales adicionales para la attribute list y el creation flag:

- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-initializeprocthreadattributelist`;
- `https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags`.

### 8.3 Capacidad de lanzamiento, autorización de acción y navegador

Son dos secretos con roles y ciclos de vida distintos. No pueden reutilizarse,
derivarse uno del otro ni representarse mediante el mismo valor.

No se usa el mismo secreto para ambos roles.

#### launch_capability

- 256 bits generados con CSPRNG por lanzamiento;
- sólo en memoria;
- nunca en URL, logs, localStorage, archivo, argumento de proceso ni cookie
  persistente;
- vigente únicamente durante ese lanzamiento;
- revocada al cerrar, bloquear o perder el proceso o el canal.

La launch_capability prueba posesión dentro de la sesión local de lanzamiento.
No representa presencia humana ni autoriza por sí sola una acción sensible.

#### action_grant

- emitido únicamente después de que UserConsentVerifierInterop devuelva
  Verified;
- auténtico y no falsificable, con emisor y validador explícitos dentro de la
  frontera launcher/broker/backend;
- si una alternativa futura fuera bearer, criptográficamente impredecible y con
  entropía suficiente;
- sólo en memoria;
- nunca en URL, query, fragment, cookies, web storage, clipboard, archivos,
  argv, entorno, logs, excepciones, telemetry ni dumps;
- nuevo para cada acción sensible;
- ligado exactamente a cuenta, acción, manifest, commandId y sesión de
  lanzamiento;
- consumido atómicamente, una sola vez y junto con la decisión del comando, de
  forma que dos consumidores concurrentes no puedan usarlo;
- replay posterior rechazado con fallo cerrado;
- con vencimiento corto;
- invalidado al usarse, vencer por timeout, cambiar el manifiesto, cerrar,
  bloquear o perder el proceso o el canal.

La action_grant no puede ser la launch_capability ni una extensión de su
vigencia. Cualquier resultado de Windows Hello distinto de Verified falla
cerrado y no emite el grant. Estos invariantes no seleccionan token bearer,
assertion, protocolo, transporte ni algoritmo; cualquier mención de bearer es
condicional y las alternativas permanecen sin elegir. La representación del
grant y su eventual canal al navegador siguen **PENDIENTES — STOP POINT**.

#### Canal launcher/broker→navegador

**PENDIENTE — STOP POINT**

El canal desde el launcher o broker hacia el navegador todavía no está
resuelto. Esta corrección no selecciona ni propone un transporte. En particular,
no se usarán silenciosamente URL, query string, fragment, cookie, localStorage,
sessionStorage, archivo, clipboard ni argumento de proceso. Resolver esta
frontera requiere una decisión posterior de arquitectura y seguridad de
MAIN/Joa.

### 8.4 Si un named pipe se vuelve necesario

Exigir conjuntamente:

- nombre aleatorio por lanzamiento, entendido como reducción de colisiones y no
  como autenticación;
- FILE_FLAG_FIRST_PIPE_INSTANCE;
- una única instancia;
- PIPE_REJECT_REMOTE_CLIENTS;
- DACL explícita y mínima para el SID de logon actual;
- derechos específicos mínimos; evitar FILE_GENERIC_WRITE porque incluye
  FILE_CREATE_PIPE_INSTANCE;
- el launcher servidor compara GetNamedPipeClientProcessId con
  GetProcessId(handle del hijo esperado) y confirma en ese instante que el
  proceso continúa activo;
- el hijo compara simétricamente GetNamedPipeServerProcessId con el PID del
  launcher esperado;
- fallo cerrado si el proceso terminó, el handle no es válido o hay mismatch;
- handles de ambos procesos esperados mantenidos abiertos durante la
  autenticación;
- el mismo framing, nonce, límites y timeouts, preservando la separación entre
  launch_capability y action_grant.

Esta alternativa se refiere sólo al canal launcher–backend. No resuelve ni
selecciona el canal launcher/broker→navegador.

La DACL identifica un token/logon, no un ejecutable exacto. Otro proceso del
mismo logon y sesión puede satisfacerla. Véanse
[Named Pipe Security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights),
[CreateNamedPipe](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createnamedpipea),
[GetNamedPipeClientProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid)
y
[GetNamedPipeServerProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeserverprocessid).
La relación entre el handle conservado y su PID se obtiene mediante
[GetProcessId](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessid).

### 8.5 Límites y stop points

El IPC no protege frente a malware con las mismas capacidades del usuario,
lectura o inyección de procesos, administrador, SYSTEM o kernel comprometido.
Tampoco reemplaza Windows Hello, DPAPI, autorización de acción ni cifrado de la
bóveda.

Detener el diseño si:

- la herencia de handles no puede acotarse;
- falta EXTENDED_STARTUPINFO_PRESENT, lpStartupInfo no apunta a una
  STARTUPINFOEX inicializada o falla InitializeProcThreadAttributeList o
  UpdateProcThreadAttribute;
- lpValue no apunta a almacenamiento estable y contiguo equivalente a un array
  de exactamente tres HANDLE, o cbSize no es 3 * sizeof(HANDLE);
- el almacenamiento de lpValue se mueve, reemplaza, cambia, libera o deja de
  existir antes de completar DeleteProcThreadAttributeList;
- no puede demostrarse que la lista contiene únicamente hStdInput, hStdOutput y
  hStdError, en ese orden y sin ausencias ni handles adicionales;
- StartupInfo.cb no es sizeof(STARTUPINFOEX), lpAttributeList no referencia el
  buffer inicializado, ese buffer no vive hasta el retorno de CreateProcessW o
  lpStartupInfo no referencia la STARTUPINFOEX completa;
- lpApplicationName es nulo o no contiene la ruta absoluta atestada, o
  lpCommandLine es inmutable, contiene secretos o introduce ambigüedad de
  ejecutable;
- la attribute list no contiene exactamente los handles allowlisted o el hijo
  hereda el handle sintético externo de control;
- la creación concurrente deja una ventana de herencia amplia;
- quedan extremos duplicados abiertos, un descendiente hereda un extremo o EOF
  no puede observarse al cerrar los propietarios;
- stderr comparte el framing, deja de drenarse por alcanzar el límite retenido,
  persiste información sensible o puede bloquear al hijo por llenar su buffer;
- la launch_capability aparece en argv, entorno, URL, query string, fragment,
  cookie, storage web, archivo, clipboard o logs;
- launch_capability y action_grant comparten secreto, rol o lifecycle;
- se emite un action_grant sin Verified, se reutiliza para otra acción o no se
  liga exactamente a cuenta, acción, manifest, commandId y sesión de
  lanzamiento;
- el action_grant carece de autenticidad, no falsificabilidad, emisor o
  validador explícitos, o aparece en una superficie persistente o registrable;
- el consumo de action_grant no es atómico con la decisión del comando o un
  replay posterior puede prosperar;
- se intenta seleccionar el canal launcher/broker→navegador dentro de esta
  corrección documental;
- el protocolo carece de versión, límites, nonce, correlación o expiry;
- se requiere overlapped I/O pero se insiste en pipes anónimos;
- un named pipe carece de DACL, rechazo remoto, primera instancia o validación
  de PID y proceso vivo;
- aparecen elevación, servicio, SYSTEM, cross-session o impersonación sin un
  contrato de seguridad nuevo.

## 9. Validación de esta entrega

### 9.1 Procedencia durable de la corrección

| Campo | Evidencia verificada |
| --- | --- |
| Worktree de corrección | %USERPROFILE%\.codex\worktrees\eeaa\mailcleanup |
| Estado de rama | detached HEAD |
| Base exacta | 6f867544d8bc8319e082328163ea3684e24a86c0 |
| HEAD exacto | 6f867544d8bc8319e082328163ea3684e24a86c0 |
| Distancia base→HEAD / HEAD→base | 0 / 0 |
| Hash de entrada de la segunda corrección | 5AD6E95E5DE6A5565D00442944E7BDDF7208D4D6306DDCD8AEF4D071AF04CC91 |
| Hash de entrada de la tercera corrección | 31CDB5608B7B9269AA7B05E6B7CDA1869AD5E15C6D76211A1F54911E8998FC77 |
| Hash de entrada de la cuarta corrección | BCABBB213D820F238C275ADDA30C41E706DF3627EB891B3681AF55D8FD0B1F79 |
| Hash de entrada de la corrección acotada final | EBFA6B9182DC1C33E59EC36432F312686D5439D5B47173A1CAA8227AA141D071 |
| Hash de la candidata final auditada por MAIN | DB50327F3EE524503E3D85F041452133777579A1F06BA3F5BBB2895AAA326AF3 |
| Estado final esperado y verificado | únicamente `?? docs/ESTUDIO_TECNICO_C4P.md` |

La Puerta 0 de la sección 2 pertenece a la ejecución original en `a0ea`. El
worktree histórico `%USERPROFILE%\.codex\worktrees\a0ea\mailcleanup` y MAIN en
`%USERPROFILE%\Desktop\chatgptprojects\mailcleanup` no fueron escritos ni
modificados por esta corrección.

MAIN reauditó la candidata final con hash `DB50327F...26AF3`, cerró sin
hallazgos P0-P2 y Joa autorizó su integración documental, commit y publicación
mediante D-054. La tabla anterior conserva el estado histórico de la fuente
especialista; el encabezado refleja el estado posterior de aceptación.

VERIFICADO:

- sólo se creó docs/ESTUDIO_TECNICO_C4P.md;
- la fuente anterior permaneció sólo lectura, con 49.078 bytes y SHA-256
  5D107D4B2D9DA933A6BF5E667F3B71D7182BD4DA5E59E3B9F7D32248D20B5569;
- no se modificaron dependencias, lockfiles, código o configuración;
- no se instaló ni ejecutó un proveedor;
- A2 eliminó su raíz temporal exacta y confirmó que ya no existía;
- no se inició la app, un servidor, un listener, un broker, un backend hijo ni
  un proceso destinado a probar IPC;
- no se invocó DPAPI real, Windows Hello, Gmail u OAuth;
- se revisaron el documento completo contra NUL, el diff completo de esta
  corrección contra la entrada con hash `EBFA6B91...1D071` y el diff acumulado
  contra la fuente original;
- git diff --check terminó con código 0 y sin salida;
- el check equivalente del archivo nuevo mediante git diff --no-index --check
  no informó errores de whitespace; su código 1 es el esperado porque el
  archivo difiere del dispositivo nulo;
- se inventariaron 58 enlaces Markdown;
- sus 28 destinos locales se resolvieron en el filesystem y existen;
- sus 30 destinos externos son URLs HTTPS sintácticamente válidas, pero no se
  reconsultaron durante esta corrección porque no hubo autorización de red; esta
  corrida no afirma que esos destinos externos estén disponibles o “no rotos”;
- las dos fuentes oficiales literales agregadas en A6 también son URLs HTTPS
  sintácticamente válidas, no se reconsultaron y no integran el conteo de enlaces
  Markdown;
- el archivo es UTF-8 válido, termina en newline, no contiene bytes NUL ni
  trailing whitespace;
- se validaron un título H1, 56 títulos totales, 12 tablas sin divergencias de
  columnas y bloques Markdown balanceados;
- las búsquedas precisas no encontraron placeholders, direcciones de correo,
  claves privadas ni formatos comunes de tokens;
- las búsquedas precisas encontraron cero nombres completos y cero rutas con el
  nombre literal del perfil, tanto con separadores invertidos como directos;
- las menciones a Joa corresponden únicamente a la autoridad de gobierno del
  proyecto y no identifican rutas, datos Gmail ni fixtures;
- Git informó únicamente ?? docs/ESTUDIO_TECNICO_C4P.md;
- no quedaron raíces mailcleanup-c4p-phase-a-* en el directorio temporal;
- .venv, data, frontend/node_modules y frontend/dist permanecieron ausentes;
- A3–A4 quedaron preservadas byte a byte y A2 conserva los tres hashes,
  tamaños, conteos y offsets observados.

El documento conserva la evidencia Git con rutas canónicas basadas en
`%USERPROFILE%`. Las rutas de runtime y temporales usan `%LOCALAPPDATA%` y
`%TEMP%`; no incorpora nombres completos, mensajes, direcciones de Gmail,
credenciales ni fixtures privados. Las menciones breves a Joa conservan sólo la
autoridad de gobierno del proyecto.

No se ejecutó la batería funcional global. No corresponde para un cambio
exclusivamente documental y no está autorizado repetir capacidades reales ni
pruebas externas; además, la batería alcanzaría el roundtrip DPAPI real de
tests/test_gmail_session.py, fuera de la autorización de esta Fase A. Esto no se
presenta como una batería verde. Las Fases B–D no se ejecutaron.

## 10. Riesgos, pendientes y recomendación a MAIN

### Riesgos

- La evidencia de proveedores es documental; no sustituye inspección del
  artefacto real.
- El PATH de A1 observó CPython 3.14.7 / SQLite 3.50.4 y el entorno de proyecto
  MAIN conocido por auditoría usa CPython 3.12.13 / SQLite 3.53.1. Ninguno fija
  la matriz de compatibilidad ni el ABI del producto.
- Ningún binding Python estudiado demostró todavía una vía raw-key compatible.
- Un proceso con dos cores SQLite puede invalidar atestación, configuración y
  aislamiento aunque las APIs parezcan compatibles.
- Cifrado en reposo no protege memoria, procesos comprometidos, backups externos
  ni metadatos que el formato deje deliberadamente visibles.
- El IPC propuesto reduce superficie accidental; no autentica un ejecutable
  frente a un atacante con el mismo nivel de acceso.

### Pendientes antes de Fase B

1. decisión explícita de Joa/MAIN de abrir una nueva fase;
2. elegir un único candidato documental para inspección, no para integración;
3. resolver licencia, costo y distribución;
4. definir la versión exacta de CPython, ABI y Windows soportados;
5. estabilizar la frontera de bytes más longitud y núcleo único;
6. resolver el canal launcher/broker→navegador mediante una decisión separada;
7. autorizar adquisición aislada del artefacto;
8. implementar el harness antes de conectar el candidato al producto;
9. mantener Gmail, OAuth, datos reales y acciones fuera de esa validación.

### Recomendación

MAIN puede usar este documento para decidir si prepara una propuesta separada de
Fase B. No debería seleccionar proveedor sólo por esta matriz ni comenzar un
spike sobre el producto. El próximo paso seguro, si recibe autorización nueva,
es fijar un único artefacto candidato y ejecutar primero procedencia, ABI,
núcleo único y vía de clave en un harness aislado. Si cualquiera falla, se
detiene sin tocar MailCleanup.
