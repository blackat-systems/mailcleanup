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
| D-010 | Estudio de Limpieza, Limpieza Controlada y todo acceso real siguen sin autorización; sólo la preparación sintética de Mapa Total por D2 queda exceptuada por D-020. | Vigente con excepción D-020 | Contrato y prompt actuales |
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
D-017, D-018, aceptó Base Segura mediante D-019 y habilitó la implementación
sintética de D2 mediante D-020. Ninguna autorización permite abrir OAuth,
conectar Gmail, solicitar credenciales, usar datos reales, ejecutar acciones
externas, iniciar D3, Estudio de Limpieza o Limpieza Controlada.

## Resultado de la implementación autorizada

MAIN ejecutó el portado selectivo y lo consolidó en el commit que contiene este
registro: retiró del árbol activo el
prototipo con capacidades reales, reconstruyó los entornos locales, corrigió la
batería de aceptación, completó la transparencia de protecciones y agregó una
barrera automática de Base Segura. Pasaron 17 pruebas Python, Ruff, mypy, ESLint, 4
pruebas Vitest y el build de producción. La API HTTP local y el plan simulado
también fueron comprobados. La inspección visual permanece pendiente por un
fallo del servicio de control del navegador, no por una prueba fallida de la
aplicación.
