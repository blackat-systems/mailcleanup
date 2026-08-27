# Prompt D4 — Real Classification Domain

## Rol

Sos la dependencia especialista D4 `real-classification-domain` de MailCleanup.
No sos MAIN. Implementá únicamente la clasificación local de registros
normalizados, con un corpus completamente sintético. Tu entrega será evidencia
para la auditoría independiente de MAIN.

## Ubicación y base obligatorias

- Worktree: el checkout aislado creado por Codex para esta tarea.
- Rama esperada: una rama `codex/*` exclusiva de la tarea.
- Commit base: el SHA exacto indicado por MAIN junto con este prompt.
- Estado inicial esperado: limpio.

Antes de editar verificá y reportá:

```powershell
(Get-Location).Path
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git remote -v
```

Si la base, rama, limpieza o alcance no coinciden, detenete. No uses reset,
rebase, merge, clean ni maniobras para ocultar diferencias.

## Lectura obligatoria

Leé completamente:

1. `AGENTS.md`.
2. `docs/CONTRATO_MVP.md`.
3. `docs/contracts/CLASSIFICATION_DOMAIN_V1.md`.
4. `docs/contracts/INDEX_PERSISTENCE_V1.md`.
5. `docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`.
6. `docs/contracts/SECURITY_PRIVACY_V1.md`.
7. La sección D4 de `docs/PLAN_DEPENDENCIAS.md`.
8. `docs/DECISIONES.md`.
9. `src/mailmap/index_model.py`.
10. `src/mailmap/model.py`.
11. `src/mailmap/classifier.py`.
12. `src/mailmap/gmail_inventory.py`, especialmente la normalización.
13. `tests/test_base_segura_domain.py`.
14. `tests/test_base_segura_safety.py`.
15. `scripts/check.ps1`.

Para D4 prevalece `CLASSIFICATION_DOMAIN_V1.md`. No lo modifiques para acomodar
la implementación. La taxonomía vinculante es la compacta del contrato MVP, no
la taxonomía futura ampliada de la especificación funcional.

## Objetivo

Implementar una función pura y determinista que transforme
`IndexedMessageRecord` en fuentes, flujos y clasificaciones explicables sin
usar `brand_hint`, `rubro_hint`, `flow_hint`, `personal_signal`, `fixture_tags`
ni otras ayudas sintéticas.

Debe producir:

- identidad conservadora y estable de fuente;
- flujos separados por evidencia estructural e intención;
- rubro, intención y estado de suscripción;
- confianza alta, media, baja o contradictoria;
- evidencias cerradas, ordenadas y redactadas;
- desconocidos explícitos cuando falte fundamento.

## Archivos autorizados

Podés crear o modificar exclusivamente:

- `src/mailmap/classification_model.py`;
- `src/mailmap/classification_domain.py`;
- `tests/test_real_classification_domain.py`;
- `tests/test_base_segura_safety.py`, sólo para ampliar la barrera negativa de
  D4 sin debilitar ninguna prueba vigente.

No modifiques `model.py`, `classifier.py`, `fixtures.py`, `service.py`,
`repository.py`, D1, D2, D3, API, frontend, scripts, configuración,
dependencias ni documentación. Si el contrato exige otro archivo, devolvé el
bloqueo a MAIN.

## API pública obligatoria

En `classification_domain.py`:

```python
classify_indexed_records(
    records: Iterable[IndexedMessageRecord],
) -> ClassificationResult
```

En `classification_model.py` definí modelos inmutables, con `slots`, sin
`**kwargs` ni diccionarios de extensión:

- `EvidenceStrength`;
- `ClassificationEvidence`;
- `ClassifiedMessage`;
- `ClassifiedSource`;
- `ClassifiedFlow`;
- `ClassificationResult`;
- códigos y excepción controlada del dominio.

Reutilizá `Rubro`, `Intencion`, `Suscripcion` y `Confianza` desde `model.py`.
No dupliques ni amplíes sus valores.

## Reglas obligatorias

1. Validá toda la entrada antes de clasificar.
2. Rechazá cuentas mezcladas e identidades duplicadas.
3. La salida debe ser idéntica ante distinto orden de entrada.
4. No pongas direcciones, dominios, nombres, `List-ID` ni asuntos en IDs locales.
5. Empezá separando remitentes y fusioná sólo con evidencia positiva múltiple.
6. Infraestructura compartida, parecido de nombre o categoría Gmail por sí solos
   no fusionan fuentes.
7. Baja confianza mantiene direcciones distintas separadas.
8. `List-ID` identifica un flujo, nunca una fuente completa.
9. Seguridad, documentos y promociones permanecen como flujos separados.
10. Un remitente sin señales suficientes queda desconocido; no se lo presenta
    como persona u organización conocida.
11. No infieras comunicación personal solamente por ausencia de lista.
12. Toda inferencia incluye evidencia concreta y redactada.
13. Una contradicción produce `Confianza.CONTRADICTORIA` y nunca una certeza.
14. La confianza agregada no mejora la peor confianza material de sus miembros.
15. D4 no calcula protección, recomendación ni acciones.

## Corpus y pruebas mínimas

Construí los registros de prueba directamente como `IndexedMessageRecord` con
cuenta opaca y dominios reservados `.example`. Cubrí todos los quince casos de
la sección 11 del contrato, en particular:

- una fuente con varias direcciones autenticadas coherentes;
- dos fuentes bajo infraestructura compartida;
- cambio de dominio que no debe fusionarse;
- varios flujos de una misma fuente;
- seguridad y factura dentro de señales promocionales;
- remitentes ambiguos separados;
- desconocidos estables;
- orden determinista;
- aislamiento de cuenta;
- redacción de `repr` y errores.

Agregá una barrera estructural que falle si D4:

- importa red, Gmail, OAuth, navegador o IA externa;
- contiene los nombres de hints prohibidos;
- agrega rutas API o consumidores productivos;
- modifica las taxonomías compartidas;
- introduce correos que no terminen en `.example`.

## Seguridad y prohibiciones

D4 no autoriza:

- Gmail real ni simulado mediante red;
- OAuth, credenciales, tokens o navegador;
- datos privados;
- cuerpos, HTML, snippet, MIME, adjuntos o destinatarios;
- persistencia de clasificaciones;
- lectura directa de SQLite;
- API pública o UI;
- protección D5, planes o acciones;
- IA externa, telemetría o logging de metadatos;
- nuevas dependencias;
- D5 o D6.

No hagas commit, push, merge, rebase ni integración en `main`.

## Validación obligatoria

Ejecutá:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_real_classification_domain.py
.\.venv\Scripts\python.exe -m pytest tests\test_base_segura_domain.py tests\test_base_segura_safety.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src\mailmap tests
.\.venv\Scripts\python.exe -m mypy
.\scripts\check.ps1
git diff --check
git status --short --untracked-files=all
```

Si Node no está disponible, usá temporalmente el runtime ya provisto por Codex
sin modificar scripts o configuración y sin instalar nada.

Revisá el contenido completo de los archivos nuevos, los no rastreados y el
diff. Eliminá del alcance cachés, bases, builds y temporales generados.

## Stop points

Detenete y devolvé el bloqueo si:

- necesitás modificar un contrato o archivo no autorizado;
- una regla requiere datos no presentes en `IndexedMessageRecord`;
- necesitás un registro externo de marcas o dominios;
- aparece una decisión material de taxonomía;
- una prueba vigente exige depender de hints;
- necesitás red, Gmail, OAuth, credenciales, datos reales o una dependencia;
- no podés mantener desconocidos y baja confianza de forma conservadora.

## Done when

D4 está entregada cuando:

1. la API y los modelos coinciden exactamente con el contrato;
2. las quince familias del corpus están cubiertas;
3. no existe dependencia de ayudas sintéticas;
4. todas las inferencias son explicables y deterministas;
5. Base Segura y D1-D3 permanecen intactas;
6. todas las validaciones aplicables aprueban;
7. sólo existen cambios en los cuatro archivos autorizados;
8. no se hizo ninguna operación Git o externa prohibida.

## Handoff a MAIN

Entregá un único informe autosuficiente con:

1. resultado y límites;
2. ruta, rama, base, HEAD y estado final;
3. archivos creados o modificados;
4. modelos, reglas de agrupación y precedencias implementadas;
5. evidencia de determinismo, contradicción y separación conservadora;
6. pruebas exactas y resultados;
7. diff, archivos no rastreados y búsqueda de secretos/artefactos;
8. riesgos y casos que permanecen desconocidos;
9. confirmación explícita de ausencia de Gmail, OAuth, red, datos reales,
   persistencia, API, UI, D5 y D6.

No declares D4 integrada. MAIN debe auditarla independientemente.
