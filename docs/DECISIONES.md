# Registro de decisiones

Fecha de inicialización de MAIN: 18 de agosto de 2026.

Este registro distingue lo definido por la instrucción actual de Joa de lo que
todavía necesita aceptación. Los commits heredados son evidencia, no autoridad.

| ID | Decisión o propuesta | Estado | Autoridad / evidencia |
|---|---|---|---|
| D-001 | `mailcleanup` sobre `main` es el worktree de MAIN. | Vigente | Instrucción actual de Joa y estado Git verificado |
| D-002 | El proyecto histórico sólo puede usarse como referencia de lectura. | Vigente | Instrucción actual de Joa |
| D-003 | Base Segura usa exclusivamente datos sintéticos y no abre Gmail ni OAuth. | Vigente | Instrucción actual de Joa |
| D-004 | Fuente, flujo, rubro, intención, suscripción, protección, confianza y evidencia son ejes separados. | Vigente | Contrato y prompt actuales |
| D-005 | Windows + API Python + React/TypeScript + SQLite + loopback. | Confirmada | Joa, después de la auditoría de MAIN |
| D-006 | Portar selectivamente componentes auditados del candidato. | Confirmada | Joa, después de la auditoría de herencia |
| D-007 | El candidato `0a90b71` no está aceptado como Base Segura terminada. | Vigente | Instrucción actual de Joa |
| D-008 | Retirar `src/gmail_cleaner`, su configuración y dependencias del árbol activo; conservarlo sólo en Git. | Ejecutada | Portado selectivo confirmado por Joa |
| D-009 | No crear worktrees especialistas en esta inicialización. | Vigente | Instrucción actual de Joa |
| D-010 | Limpieza Controlada y todo acceso real siguen sin autorización. Estudio de Limpieza está autorizado sólo hasta C6 sintética aceptada; D7 requiere su propia puerta. | Vigente con excepciones registradas | Contrato, D-020, D-040 y D-041 |
| D-011 | El candidato sólo puede presentarse para aceptación cuando pasen pruebas, lint, tipos, build y HTTP; la revisión visual se informa por separado. | Vigente | Criterios de calidad y auditoría de MAIN |
| D-012 | MAIN conserva contratos, arquitectura, batería e integración, pero no implementa por defecto cada módulo funcional. | Vigente | Instrucción explícita de Joa |
| D-013 | No se crea ningún worktree mientras `main` tenga cambios sin commit o carezca de un commit base limpio confirmado. | Vigente | Instrucción explícita de Joa |
| D-014 | Las dependencias se habilitan secuencialmente después de integrar y volver a probar aquello que consumen. | Vigente | Instrucción explícita de Joa |
| D-015 | La nomenclatura activa es Base Segura, Mapa Total, Estudio de Limpieza y Limpieza Controlada. | Vigente | Instrucción explícita de Joa |
| D-016 | MAIN puede consolidar la base vigente en `main`, crear el commit y hacer push sólo si existe un remoto válido. | Ejecutada localmente | Autorización explícita de Joa |
| D-017 | Crear D1 `real-index-persistence` como primer worktree, limitado a infraestructura sintética y sin habilitar Gmail, OAuth, credenciales ni datos reales. | Autorizada | Instrucción explícita de Joa del 18 de agosto de 2026 |
| D-018 | Integrar D1 en MAIN después de auditoría independiente, corrigiendo la atomicidad de migraciones y sin habilitar consumidores posteriores. | Ejecutada y consolidada en el commit que contiene esta decisión | Auditoría MAIN y autorización explícita de Joa del 18 de agosto de 2026 |
| D-019 | Aceptar Base Segura pese a que la revisión visual instrumental continúa no verificada. | Confirmada | Aceptación explícita de Joa del 18 de agosto de 2026 |
| D-020 | Preparar y crear D2 `secure-gmail-session` con `gmail.metadata`, dobles sintéticos, OAuth de escritorio seguro y DPAPI de usuario; sin abrir OAuth ni conectar una cuenta real. | Autorizada | Instrucción explícita de Joa del 18 de agosto de 2026 y contrato `GMAIL_SESSION_V1.md` |
| D-021 | Integrar D2 en MAIN después de auditoría independiente y corregir vencimientos y conservación del refresh token, sin habilitar adaptadores reales ni D3. | Ejecutada y consolidada por el commit que contiene esta decisión | Instrucción de Joa y auditoría de MAIN del 18 de agosto de 2026 |
| D-022 | Reforzar la privacidad, consolidar contratos C1-C5 para alcance sintético y crear D3 `gmail-readonly-inventory` con dobles, sin OAuth, Gmail, credenciales, datos reales ni adaptador productivo. | Autorizada | Instrucción explícita de Joa del 18 de agosto de 2026 y contratos `SECURITY_PRIVACY_V1.md` y `GMAIL_READONLY_INVENTORY_V1.md` |
| D-023 | Ampliar D1 para aplicar altas, actualizaciones, bajas y checkpoint en una transacción e iniciar un escaneo completo reemplazando controladamente el índice anterior; adaptar e integrar D3 con regresiones de rollback y registros obsoletos. | Ejecutada y consolidada por el commit que contiene esta decisión | Instrucción explícita de Joa y auditoría MAIN del 18 de agosto de 2026 |
| D-024 | Preparar y crear D4 `real-classification-domain` sobre registros normalizados exclusivamente sintéticos, con identidad conservadora, flujos separados, taxonomía MVP y evidencia; sin Gmail, OAuth, red, datos reales, persistencia, API ni UI. | Autorizada | Instrucción explícita de Joa del 27 de agosto de 2026 y `CLASSIFICATION_DOMAIN_V1.md` |
| D-025 | Integrar D4 en MAIN después de auditoría independiente, corrigiendo sobreagrupación entre dominios, validación de baja y cálculo de confianza; mantener D5 bloqueada hasta definir migración de correcciones ante cambios de agrupación o IDs. | Ejecutada y consolidada por el commit que contiene esta decisión | Handoff especialista, auditoría MAIN y aprobación de Joa del 27 de agosto de 2026 |
| D-026 | Definir para D5 una capa local separada de la clasificación automática: comandos tipados, historial append-only, undo lógico, selectores durables, reaplicación sólo ante coincidencia exacta o cambio aislado de ID con selector idéntico y protección acumulativa que nunca rebaja reglas automáticas. | Contrato aprobado; implementación autorizada posteriormente por D-031 | Aprobación explícita de Joa del 27 de agosto de 2026; `LOCAL_POLICY_MEMORY_V1.md` y revisión cruzada D4/D5 |
| D-027 | Ampliar la salida pública D4 con descriptores cerrados, inmutables, versionados y redactados de identidad de fuente y flujo, sin cambiar agrupaciones, IDs, taxonomías, inferencias ni evidencias. | Ejecutada y consolidada por el commit que contiene esta decisión | Autorización explícita de Joa del 27 de agosto de 2026, `CLASSIFICATION_DOMAIN_V1.md` y regresiones de compatibilidad |
| D-028 | Autorizar a MAIN a crear y auditar el prompt autosuficiente D5, sin crear todavía su worktree ni comenzar la implementación. | Ejecutada y consolidada por el commit que contiene esta decisión | Autorización explícita de Joa del 27 de agosto de 2026 |
| D-029 | Toda decisión D5 nueva se valida contra registros, clasificación y políticas activas mediante `PreparedPolicyDecision` antes de persistir; el replay exacto se consulta antes de preparar y se repite bajo `BEGIN IMMEDIATE`. | Ejecutada y consolidada por el commit que contiene esta decisión | Auditoría MAIN de la coherencia entre `target_not_found`, binding histórico, idempotencia y la firma del repositorio |
| D-030 | D5 nunca crea ni recrea `indexed_accounts`; borrar el índice de una cuenta elimina por cascada memoria y replay, e invalida preparados, retries y undos anteriores. | Ejecutada y consolidada por el commit que contiene esta decisión | Auditoría de privacidad y lifecycle previa al prompt D5 |
| D-031 | Consolidar la base del prompt y crear un único worktree D5 `local-policy-memory`, entregándole el prompt autosuficiente desde ese SHA exacto. | Ejecutada: base `663d8a9`, worktree `9623` | Confirmación explícita de Joa del 27 de agosto de 2026 y verificación Git posterior |
| D-032 | Usar un repositorio GitHub privado `blackat-systems/mailcleanup` como `origin` y publicar únicamente `main`; las ramas especialistas, secretos, bases, datos locales y `grafo.txt` permanecen fuera. | Ejecutada: primer push verificado desde `6310c76` | Autorización explícita de Joa del 27 de agosto de 2026, destino privado verificado y auditoría preventiva del historial |
| D-033 | Integrar D5 en MAIN después de auditoría independiente, corrigiendo que una partición pudiera mejorar la confianza automática del flujo D4 y manteniendo D6 y toda capacidad real bloqueadas. | Ejecutada y consolidada por el commit que contiene esta decisión | Handoff especialista y auditorías independientes de dominio, seguridad y persistencia del 27 de agosto de 2026 |
| D-034 | Cerrar la evidencia visual pendiente de Base Segura después de recorrer Panorama, Fuentes, detalle, Estudio y Estado en escritorio y 390 px, sin defectos bloqueantes. | Verificada | Recorrido instrumental de MAIN del 27 de agosto de 2026 |
| D-035 | Estabilizar C5 en MAIN mediante una fotografía SQLite coherente, composición D4+D5, fixture canónico `.example`, puerta sintética ejecutable y una API local `/api/v2` cerrada, preservando `/api/v1` y sin crear D6 ni habilitar capacidades reales. | Ejecutada y consolidada por el commit que contiene esta decisión | `MAPA_TOTAL_API_V1.md`, auditorías independientes, batería global y autorización de commit de Joa del 27 de agosto de 2026 |
| D-036 | Preparar y crear un único worktree D6 `mapa-total-ui` desde una base limpia posterior a C5, limitado al frontend sintético `/api/v2`, sin Gmail, OAuth, credenciales, datos reales, controles de sincronización, Estudio de Limpieza ni acciones. | Ejecutada: base `75764c9`, worktree `bbbc` | Autorización explícita de Joa del 27 de agosto de 2026, `MAPA_TOTAL_API_V1.md` y Puerta 0 verificada |
| D-037 | Integrar D6 en el árbol de MAIN después de auditoría independiente, corrigiendo redirecciones externas, Unicode, atribución de protección, objetivos de undo, códigos de error, foco del menú y fixture de protección; mantener D7 y capacidades reales bloqueadas. | Ejecutada y consolidada por el commit que contiene esta decisión | Handoff especialista, auditorías independientes, batería global y recorrido visual del 28 de agosto de 2026 |
| D-038 | Simplificar la jerarquía visual de D6 mediante navegación primaria reducida y divulgación progresiva, conservando accesibles toda la evidencia, advertencias, correcciones y diagnósticos, sin cambiar contratos ni capacidades. | Ejecutada y consolidada por el commit que contiene esta decisión | Observación explícita de Joa del 28 de agosto de 2026, auditoría de MAIN y batería global |
| D-039 | Aceptar D6 y autorizar a MAIN a crear el commit de Mapa Total y publicarlo en `origin/main`, preservando `grafo.txt` fuera del commit y manteniendo bloqueados Estudio de Limpieza y las capacidades reales. | Confirmada; consolidada por el commit que contiene esta decisión | Aceptación y autorización explícitas de Joa del 28 de agosto de 2026 |
| D-040 | Autorizar el comienzo de Estudio de Limpieza y la preparación de C6 como contrato de planes congelados, revalidables y sin efectos; mantener D7 bloqueada hasta que Joa acepte el contrato, exista un SHA limpio y MAIN prepare su prompt. | Ejecutada; C6 aceptado por D-041 | Autorización explícita de Joa del 28 de agosto de 2026 y `CLEANUP_PLAN_V1.md` |
| D-041 | Aceptar C6 después de su auditoría contractual y autorizar a MAIN a consolidar exclusivamente su documentación en `main`, preservando `grafo.txt` y sin crear D7 ni publicar el commit. | Confirmada; consolidada por el commit que contiene esta decisión | Aceptación y autorización explícitas de Joa del 29 de agosto de 2026 |

## Decisiones suficientemente definidas

- problema central: comprender antes de limpiar;
- primera plataforma y experiencia local;
- una sola cuenta de Gmail en hitos futuros;
- separación de fuente y flujo;
- clasificación multidimensional con evidencia;
- agrupación conservadora;
- protección por defecto y contradicción bloqueante;
- plan previo, revalidación, idempotencia e historial antes de acciones reales;
- Papelera en vez de eliminación definitiva;
- baja automática limitada a RFC 8058 cuando exista una futura autorización;
- IA externa, Outlook, múltiples cuentas, pagos y Guardián fuera del MVP.

## Confirmación recibida

Joa respondió afirmativamente y autorizó D-005 + D-006. Posteriormente autorizó
D-017, D-018, aceptó Base Segura mediante D-019, habilitó la implementación
sintética de D2 mediante D-020 y su integración auditada mediante D-021,
autorizó D3 sintética mediante D-022, resolvió su bloqueo transaccional mediante
D-023, autorizó preparar D4 sintética mediante D-024 y MAIN ejecutó su
integración auditada mediante D-025. Joa aprobó después el contrato de D5
mediante D-026, autorizó la columna vertebral pública D4 mediante D-027 y la
preparación del prompt D5 mediante D-028 y finalmente un único worktree e
implementación D5 mediante D-031. MAIN auditó e integró esa entrega mediante
D-033, completó la evidencia visual mediante D-034, autorizó continuar con la
columna vertebral C5 registrada por D-035 y autorizó la creación sintética de D6
mediante D-036. MAIN auditó e integró esa entrega en el árbol mediante D-037, sin
presuponer su aceptación, y aplicó la simplificación de jerarquía D-038 sin
retirar contenido contractual. Joa aceptó D6 y autorizó su publicación mediante
D-039. Después autorizó comenzar Estudio de Limpieza y preparar C6 mediante
D-040, y aceptó el contrato mediante D-041. Ninguna autorización permite abrir
OAuth, conectar Gmail, solicitar credenciales, usar datos reales, ejecutar
acciones externas, crear D7 ni iniciar Limpieza Controlada.

## Resultado de la implementación autorizada

MAIN ejecutó el portado selectivo y lo consolidó en el commit que contiene este
registro: retiró del árbol activo el
prototipo con capacidades reales, reconstruyó los entornos locales, corrigió la
batería de aceptación, completó la transparencia de protecciones y agregó una
barrera automática de Base Segura. Pasaron 17 pruebas Python, Ruff, mypy, ESLint, 4
pruebas Vitest y el build de producción. La API HTTP local y el plan simulado
también fueron comprobados. La inspección visual que había quedado pendiente fue
completada después en escritorio y 390 px sin defectos bloqueantes.
