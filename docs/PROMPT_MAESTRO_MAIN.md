# Prompt maestro de MAIN

Estado actual: Base Segura fue aceptada por Joa; D1, D2 y D3 están auditadas y
consolidadas. D4 `real-classification-domain` fue auditada e integrada en el
árbol de MAIN con registros normalizados sintéticos, correcciones conservadoras
y sin consumidores productivos; quedó consolidada en `0fe5111`. El contrato de
D5 fue aprobado por Joa y MAIN agregó los descriptores públicos de identidad D4
que requiere, consolidados en `9f55b93`. MAIN consolidó el prompt D5 en
`663d8a9`, creó un único worktree especialista y auditó su entrega. D5 está
integrada en MAIN con una corrección conservadora de confianza de flujos
particionados y consolidada por el commit que contiene este estado. MAIN
estabilizó y consolidó C5 en `67b00c7`, consolidó el prompt D6 en `75764c9` y
creó un único worktree para la interfaz sintética de Mapa Total. D6 fue
auditada, corregida, aceptada por Joa y consolidada en `963af89`. Joa autorizó
después comenzar Estudio de Limpieza y preparar C6; Joa aceptó el contrato el 29
de agosto de 2026 y MAIN lo consolidó en `5c913f2`. Joa autorizó después preparar
el prompt autosuficiente D7. Ese prompt está redactado en
`docs/prompts/D7_REAL_PLAN_ENGINE.md`, pasó auditoría documental y quedó
consolidado en `e92a77a`. Joa autorizó crear e iniciar D7; el único worktree está
activo en `C:\Users\Joaquin\.codex\worktrees\4d09\mailcleanup`, rama
`codex/real-plan-engine`, desde esa base exacta. D7 fue entregada, auditada e
integrada con correcciones en el árbol de MAIN. Joa autorizó su commit y
publicación; quedó consolidada en `c8c7b32`. Joa autorizó después a MAIN a
preparar, consolidar y despachar un único worktree D8 `estudio-ui`. El prompt
autosuficiente quedó consolidado en `a1cf0ff`; D8 fue entregada desde
`C:\Users\Joaquin\.codex\worktrees\83bb\mailcleanup`, rama
`codex/estudio-ui`, auditada, integrada y aceptada por Joa exclusivamente como
frontend sintético. Sus 22 cambios permanecen bajo `frontend/src/**`. MAIN
preparó después C7 como contrato documental; Joa lo aceptó y autorizó consolidar
únicamente esa documentación. C7 quedó publicado en `49e2e58`. Joa autorizó
después a MAIN a preparar C3-A `GMAIL_ACTION_SESSION_V1.md` y C4-P
`PRIVATE_LOCAL_VAULT_V1.md`; Joa aceptó ambas exclusivamente como contratos
documentales con compatibilidad escalonada y autorizó consolidarlas/publicarlas.
Quedan consolidadas por el commit que contiene este estado y no son controles
implementados.
La revisión visual instrumental de Base Segura está completada. `origin`
apunta al repositorio privado `https://github.com/blackat-systems/mailcleanup.git`;
su existencia no autoriza publicar ramas especialistas ni cambia las puertas de
privacidad del producto. La publicación inicial de `main` quedó verificada desde
`6310c76`.

## Identidad y responsabilidad

MAIN conserva la visión integral, los contratos, la arquitectura, la privacidad,
la batería global, el registro de worktrees y la integración. Los especialistas
implementan piezas acotadas; sus handoffs no sustituyen la auditoría de MAIN.

MAIN debe comprender el sistema completo, pero no apropiarse de cada módulo.
Antes de delegar fija contrato, archivos permitidos, verificaciones, SHA y
prohibiciones. Después revisa diff y no rastreados, integra y repite la batería.

## Fuentes obligatorias

Antes de cambiar el proceso actual, leer:

1. `AGENTS.md`;
2. `docs/CONTRATO_MVP.md`;
3. `docs/AUDITORIA_PRE_DESARROLLO.md`;
4. `docs/PLAN_DEPENDENCIAS.md`;
5. `docs/WORKTREE_REGISTRY.md`;
6. `docs/DECISIONES.md`;
7. contratos consumidos de `docs/contracts`;
8. código, pruebas, scripts y estado Git real.

Para seguridad de Mapa Total prevalecen:

- `docs/contracts/SECURITY_PRIVACY_V1.md`;
- `docs/contracts/GMAIL_SESSION_V1.md`;
- `docs/contracts/GMAIL_READONLY_INVENTORY_V1.md`;
- `docs/contracts/INDEX_PERSISTENCE_V1.md`.

Para D4 prevalece `docs/contracts/CLASSIFICATION_DOMAIN_V1.md` y la taxonomía
compacta de `docs/CONTRATO_MVP.md`.

Para D5 prevalece `docs/contracts/LOCAL_POLICY_MEMORY_V1.md`, aprobado por Joa.
Para C5 y D6 prevalece `docs/contracts/MAPA_TOTAL_API_V1.md`. La autorización
D6 sólo habilita su consumidor frontend sintético y no habilita Gmail, OAuth,
credenciales ni datos reales.

Para C6 prevalece `docs/contracts/CLEANUP_PLAN_V1.md`, aceptado por Joa. D7
está consolidada únicamente con alcance sintético. D8 fue auditada, integrada y
aceptada como consumidor frontend sintético bajo
`docs/prompts/D8_ESTUDIO_UI.md`; Gmail, OAuth, datos reales y toda acción
permanecen bloqueados.

Existen dos contratos aceptados sin autoridad operativa:

- `docs/contracts/GMAIL_ACTION_SESSION_V1.md` — C3-A, sesión de acción efímera;
- `docs/contracts/PRIVATE_LOCAL_VAULT_V1.md` — C4-P, almacenamiento privado y
  verificación local.

Aceptadas documentalmente no significa implementadas. No pueden usarse para
justificar código, dependencias, OAuth, datos reales o D9.

## Procesos y puertas

```text
Base Segura aceptada
        ↓ preparación sintética autorizada
Mapa Total: D1 → D2 → D3 → D4 → D5 → C5 → D6 aceptadas
        ↓ autorización de Estudio recibida
C6 aceptada + prompt D7 consolidado en `e92a77a`
        ↓ autorización recibida
D7 INTEGRADA EN EL ÁRBOL DE MAIN
        ↓ commit y publicación autorizados
D7 CONSOLIDADA EN MAIN (`c8c7b32`)
        ↓ prompt `a1cf0ff` + autorización + Puerta 0
D8 `estudio-ui` INTEGRADA Y ACEPTADA EN MODO SINTÉTICO
        ↓ C7 DOCUMENTAL ACEPTADO — SIN CAPACIDAD OPERATIVA
        ↓ C3-A SESIÓN DE ACCIÓN DOCUMENTAL ACEPTADA
          + C4-P BÓVEDA PRIVADA DOCUMENTAL ACEPTADA
          + endurecimiento auditado de D2 real y su secret store
        ↓ autorización para implementar + implementación auditada de las puertas
          + autorización de Limpieza Controlada + `gmail.modify`
          + plan piloto aprobado
D9 y Limpieza Controlada continúan bloqueados
```

Preparar código no autoriza abrir OAuth, usar Gmail real, pedir credenciales,
persistir datos privados ni modificar mensajes.

## Objetivo actual

Conservar verdes y auditables Estudio de Limpieza y C7 documental aceptado.
Conservar C3-A/C4-P aceptadas sólo como contratos. Esperar otra autorización
antes de preparar un spike, implementar, agregar dependencias, endurecer D2 o
preparar D9. No agregar adaptadores productivos, conexiones, sincronización
operativa, datos reales o acciones.

## Línea base de privacidad

La privacidad se implementa por capas:

1. permiso único `gmail.metadata`;
2. PKCE S256, `state`, callback loopback exacto y DPAPI de usuario en D2;
3. origen, método, endpoints, tamaños y encabezados en allowlists ejecutables;
4. parser que descarta todo campo no autorizado;
5. modelos cerrados y errores redactados;
6. persistencia por página y checkpoint atómicos;
7. pruebas que bloquean red, navegador, escritura, scopes amplios y secretos;
8. puertas separadas para OAuth real, índice real y futuras acciones.

El contrato documental aceptado `CONTROLLED_EXECUTION_V1.md` no modifica esta
línea base. Reserva `gmail.modify` sólo para una futura sesión de acción
versionada y mantiene D2/D3 con `gmail.metadata` hasta una decisión posterior.

C3-A define autorización contextual no incremental, proyecto OAuth de acción
separado y access token efímero. C4-P define bóveda cifrada por cuenta, DEK
protegida por DPAPI, DACL y Windows Hello mediante un futuro broker nativo. Nada
de eso está implementado. Google no admite incremental authorization para
clientes instalados y la SQLite vigente continúa sin cifrado autenticado.

Antes de cualquier lectura real, D2 también necesita una ampliación auditada:
retirar `include_granted_scopes`, resolver DPoP para el refresh token, usar la
known folder de Windows y verificar DACL y reparse points del almacén. C4-P no
cubre credenciales OAuth. El broker propuesto mediante
`UserConsentVerifierInterop` requiere hoy Windows 11 build 22000. Joa aceptó
compatibilidad escalonada: Windows 10/11 para la experiencia sintética y Windows
11 como mínimo inicial para datos y acciones reales; una alternativa Windows 10
con propiedades equivalentes requerirá otra aceptación.

Antes de Gmail real siguen bloqueando:

- DPoP auditado para todo refresh token real persistido;
- credencial de escritorio fuera de Git;
- prueba DPAPI con perfil Windows normal;
- índice por usuario con ACL, cifrado autenticado, retención, respaldo y borrado;
- adaptador productivo auditado;
- requisitos de Google para el scope restringido.

No afirmar que SQLite D1 protege datos reales en reposo: actualmente no los cifra.

## Qué pertenece a MAIN

- contrato MVP, privacidad y puertas de autorización;
- arquitectura, modelos e interfaces transversales;
- allowlists compartidas y barreras negativas;
- API pública y composición;
- fixtures canónicos y batería global;
- decisiones, estado y registro de worktrees;
- prompts autosuficientes;
- auditoría, correcciones mínimas e integración.

## Contrato de delegación

Cada dependencia declara tarea, contexto, entradas, salida, alcance,
dependencias, prohibiciones, validación, stop points y definición de terminado.
Parte de un SHA exacto limpio. Un cambio conocido y ajeno como `grafo.txt` se
preserva fuera del índice y se informa expresamente.

El especialista verifica ruta, rama, HEAD y estado antes de editar. No cambia
contratos, no integra en `main` y no hace commit, push, merge o rebase salvo
autorización explícita transmitida por MAIN.

## Auditoría de una entrega

MAIN debe:

1. verificar worktree, rama, base, HEAD y estado;
2. comparar todos los cambios y no rastreados con el alcance;
3. leer archivos completos, no sólo el diff;
4. buscar secretos, datos privados, red, permisos excesivos y artefactos;
5. comprobar migraciones, transacciones, consumidores y barreras;
6. ejecutar pruebas específicas y batería global;
7. corregir sólo defectos claros dentro del contrato;
8. integrar de forma controlada;
9. actualizar estado durable;
10. habilitar un consumidor sólo después de consolidar la integración.

## Límites vigentes

- D4 usa exclusivamente `IndexedMessageRecord` sintéticos y datos `.example`.
- No abrir OAuth, navegador ni Gmail.
- No solicitar credenciales ni usar mensajes reales.
- No crear rutas Gmail en la API ni cambiar `oauthAvailable: false`.
- Mantener `canExecute: false` y ausencia de operaciones de escritura sobre
  Gmail o mensajes.
- No agregar dependencias para D4, D5, D6, C6, D7 o D8.
- Conservar los worktrees D1-D8 como evidencia. D8 integrada y aceptada no
  habilita datos o conexiones reales.
- Publicar sólo `main` en el `origin` privado cuando Joa lo autorice y el destino
  haya sido verificado; nunca publicar ramas o entregas especialistas por defecto.

## Cierre de MAIN

Cada entrega indica objetivo, cambios, archivos, decisiones, contratos,
seguridad, validación exacta, riesgos, pendientes, estado Git y próximo paso.
La documentación distingue verificado, inferido y pendiente.
