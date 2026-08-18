# Prompt D1 — Real Index Persistence

## Rol

Sos la dependencia especialista D1 `real-index-persistence` de MailCleanup. No
sos MAIN. Implementá exclusivamente la persistencia local sintética definida
por el contrato y devolvé evidencia para que MAIN audite e integre.

## Ubicación y base obligatorias

- Worktree: `C:\Users\Joaquin\.codex\worktrees\ab1f\mailcleanup`.
- Rama: `codex/real-index-persistence`.
- Commit base: `c3dc210e69e31eb252443d08558e78f756c719d2`.
- Estado inicial esperado: limpio.

Antes de editar, ejecutá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short
git worktree list --porcelain
```

Si la rama, el HEAD o la limpieza no coinciden, si aparece trabajo ajeno o si el
alcance exige cambiar un contrato, detenete y devolvé el bloqueo a MAIN.

## Lectura obligatoria

Leé completamente antes de modificar:

1. `AGENTS.md`.
2. `docs/CONTRATO_MVP.md`.
3. `docs/contracts/INDEX_PERSISTENCE_V1.md`.
4. La sección D1 de `docs/PLAN_DEPENDENCIAS.md`.
5. `docs/DECISIONES.md`.
6. `src/mailmap/model.py`.
7. `src/mailmap/repository.py`.
8. `src/mailmap/fixtures.py`.
9. `tests/test_base_segura_domain.py`.
10. `tests/test_base_segura_safety.py`.
11. `scripts/check.ps1`.

El contrato `INDEX_PERSISTENCE_V1.md` prevalece para tu alcance. No lo
modifiques.

## Objetivo

Implementar, usando exclusivamente datos sintéticos, el índice SQLite
versionado y el checkpoint atómico de D1 sin alterar Base Segura.

La entrega debe agregar:

- `IndexedMessageRecord` inmutable y validado;
- enums y tipo inmutable de `SyncCheckpoint`;
- migración acumulativa posterior a la v1;
- persistencia idempotente de páginas;
- checkpoint guardado en la misma transacción;
- consultas deterministas;
- eliminación aislada de mensajes y del índice de una cuenta;
- pruebas de migración, atomicidad, reanudación e aislamiento.

## Alcance permitido

Podés crear o modificar únicamente:

- `src/mailmap/index_model.py`;
- `src/mailmap/repository.py`;
- `tests/test_index_persistence.py`.

Si necesitás tocar otro archivo, no lo hagas: devolvé la necesidad a MAIN.

## Contratos obligatorios

1. La identidad es `(account_key, provider_message_id)`.
2. `account_key` es opaco, no vacío y no puede tener forma de correo.
3. Las fechas tienen zona horaria y se persisten normalizadas a UTC.
4. El modelo es cerrado: no admite `extra`, `headers_json`, `payload_json` ni
   campos arbitrarios.
5. No se persisten cuerpo, HTML, snippet, MIME, adjuntos, destinatarios,
   credenciales, tokens ni errores remotos crudos.
6. No se persisten inferencias de fuente, flujo, rubro, intención o protección.
7. Las tablas nuevas son `indexed_accounts`, `indexed_messages` y
   `sync_checkpoints` según el contrato.
8. Hay claves foráneas, clave primaria compuesta, checkpoint único por cuenta y
   borrado en cascada.
9. `save_index_page` valida toda la entrada y escribe registros y checkpoint en
   una sola transacción.
10. Reintentar la misma página no duplica filas.
11. Una actualización reemplaza sólo los campos permitidos de esa identidad.
12. La consulta ordena por fecha descendente y por ID ascendente ante empate.
13. Eliminar una cuenta no afecta otra cuenta ni Base Segura.
14. La migración desde v1 conserva mensajes sintéticos y planes simulados.
15. API v1, servicios, frontend, fixtures y clasificación no cambian.
16. `canExecute: false` y la barrera de Base Segura permanecen intactos.

Las operaciones públicas deben ser equivalentes a las firmadas en el contrato.
Si elegís nombres distintos, justificá la equivalencia en el handoff.

## Implementación esperada

- Preferí dataclasses congeladas, validación explícita y enums cerrados.
- Mantené la migración v1 intacta y agregá una migración nueva.
- Reutilizá conexión, transacción y serialización cuando corresponda.
- No hagas refactors generales.
- No agregues dependencias.
- No diseñes D2 o D3.
- No implementes cifrado ni afirmes aptitud para datos reales.

## Pruebas obligatorias

`tests/test_index_persistence.py` debe cubrir como mínimo:

1. validación de claves, fechas, tamaños, estados y versión;
2. rechazo de `account_key` con forma de correo;
3. normalización UTC y etiquetas canónicas sin duplicados;
4. base nueva en la última versión;
5. migración desde v1 conservando un mensaje y un plan;
6. guardado atómico de página y checkpoint;
7. rollback completo si falla el checkpoint;
8. reintento idempotente;
9. actualización de una identidad existente;
10. orden determinista;
11. lectura y reanudación del checkpoint;
12. eliminación parcial de IDs;
13. eliminación aislada por cuenta;
14. ausencia de columnas genéricas o prohibidas;
15. regresión de Base Segura.

Ejecutá:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_index_persistence.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
```

Si no existe el entorno, usá los scripts oficiales sin cambiar dependencias.
Informá cualquier comprobación que no puedas ejecutar.

## Fuera de alcance

- Gmail, OAuth, SDK de Google o cualquier red.
- Datos reales, direcciones reales o dominios no reservados.
- Credenciales, tokens, secretos o bases locales versionadas.
- API, servicio, frontend, scripts, configuración o documentación.
- Clasificación, protecciones, correcciones, planes o acciones.
- Cifrado en reposo o directorio final para datos reales.
- Habilitar Mapa Total operativo.
- Crear otro worktree o delegar.
- Modificar contratos o arquitectura.
- Hacer commit, push, merge, rebase o integrar en `main`.

## Criterios de aceptación

D1 está entregada cuando:

1. satisface `INDEX_PERSISTENCE_V1.md`;
2. conserva Base Segura y su migración v1;
3. demuestra atomicidad, idempotencia, reanudación y aislamiento;
4. no contiene datos privados, secretos, red ni capacidades Gmail;
5. pasan las comprobaciones aplicables;
6. el diff contiene sólo los tres archivos permitidos;
7. el worktree queda sin commit para auditoría de MAIN.

## Handoff a MAIN

Entregá un resumen autosuficiente con:

1. resultado;
2. ruta, rama, base y HEAD;
3. estado final de Git;
4. archivos modificados y nuevos;
5. diseño y equivalencia con el contrato;
6. pruebas y resultados exactos;
7. diff y archivos no rastreados;
8. riesgos, limitaciones y pendientes;
9. confirmación de que no hiciste commit, push o merge ni usaste Gmail, OAuth,
   red o datos reales.

No declares la función integrada, publicada ni apta para datos reales.
