# Auditoría previa al desarrollo

Fecha: 18 de agosto de 2026.

Alcance: revisión crítica de `ESPECIFICACION_FUNCIONAL.md` y del prototipo CLI existente. Esta auditoría no modifica ni valida el código de Gmail y no autoriza una conexión real.

## 1. Dictamen

La visión de producto es valiosa y diferenciable, pero el documento original no puede usarse directamente como alcance de desarrollo. Contiene una mezcla de:

- núcleo de primera versión;
- funciones de producto comercial maduro;
- hipótesis todavía no verificadas;
- acciones que requieren permisos de Gmail diferentes;
- conceptos útiles que aún no tienen semántica operativa exacta.

El problema principal no es una mala idea, sino la ausencia de fronteras. Implementar las 115 funciones como una sola etapa produciría una aplicación difícil de verificar y aumentaría el riesgo sobre datos reales.

La corrección propuesta es conservar la visión completa y desarrollar mediante cortes verticales. El primer corte debe terminar en un **mapa local, explicable y de sólo lectura**. Las operaciones sobre Gmail se agregan únicamente después de validar identidad, clasificación, planes y protecciones con datos sintéticos.

## 2. Hallazgos bloqueantes

### A-01. El alcance inicial no está acotado

**Problema:** las 115 funciones mezclan onboarding, análisis, limpieza, automatización, monitoreo, múltiples cuentas y producto comercial.

**Impacto:** no existe una definición comprobable de “terminado”; cualquier desarrollo podría expandirse indefinidamente.

**Resolución:** dividir el trabajo en cuatro hitos: fundamento sin Gmail, mapa de sólo lectura, planificación sin efectos y acciones reales controladas.

### A-02. “Local” y “Guardián continuo” son incompatibles sin una decisión adicional

**Problema:** una aplicación local cerrada no puede monitorear permanentemente la casilla. Un Guardián continuo necesita un proceso residente, una aplicación instalada en segundo plano o infraestructura alojada.

**Impacto:** prometer mantenimiento continuo en la primera versión implicaría una arquitectura que todavía no fue elegida.

**Resolución:** primera versión local y manual. El Guardián queda diseñado, pero no se promete ejecución cuando la aplicación está cerrada.

### A-03. Varias acciones están nombradas de forma ambigua

**Problema:** “pausar”, “silenciar”, “bloquear”, “mandar a spam” y “borrar” pueden significar acciones distintas.

**Resolución semántica:**

- **Conservar:** no modificar mensajes ni crear reglas.
- **Archivar:** quitar `INBOX`; no libera almacenamiento.
- **Mover a Papelera:** acción reversible mientras Gmail mantenga el mensaje allí.
- **Desuscribir:** solicitar la baja al emisor; no modifica el historial.
- **Silenciar localmente:** ocultar o relegar en la aplicación; no cambia Gmail.
- **Regla futura local:** actuar cuando la aplicación vuelva a ejecutarse.
- **Filtro de Gmail:** regla persistente del proveedor; requiere otro permiso y queda fuera del MVP.
- **Marcar como spam:** clasificar mensajes concretos como spam; no equivale a una baja.
- **Bloquear:** queda fuera del MVP hasta definir si significa filtro de Gmail o política local.

### A-04. La taxonomía contiene solapamientos

**Problema:** “aplicaciones y software” se superpone con “tecnología y sistemas operativos”; “servicios pagos” con “membresías” y “comercio”; “spam” aparece como identidad, actividad e intención.

**Impacto:** un clasificador puede producir etiquetas formalmente válidas pero contradictorias.

**Resolución:** mantener ejes ortogonales:

1. identidad de la fuente;
2. rubro de la fuente;
3. intención del flujo;
4. estado de suscripción;
5. nivel de protección;
6. confianza y evidencias.

`Spam` no será un rubro. Será una evaluación de riesgo o legitimidad.

### A-05. No existe contrato entre confianza y acción

**Problema:** se definieron niveles de confianza, pero no qué puede hacer cada nivel.

**Resolución:**

- **Alta:** puede agrupar y sugerir una acción; nunca ejecutarla sin un plan aprobado.
- **Media:** puede mostrar una agrupación provisional y exige revisión.
- **Baja:** mantiene remitentes separados y clasifica como desconocido.
- **Evidencia contradictoria:** bloquea la acción automática sobre el subconjunto afectado.

### A-06. Fuente y flujo no tienen todavía una identidad estable

**Problema:** un dominio compartido por varias marcas no prueba una fuente común, y una misma marca puede utilizar múltiples proveedores de envío.

**Impacto:** una fusión incorrecta puede mezclar promociones y comprobantes o incluso organizaciones distintas.

**Resolución:** comenzar conservadoramente por remitente/lista técnica. Las fusiones de fuente serán sugeridas y explicadas. Las correcciones manuales deben persistir como decisiones del usuario.

### A-07. El modelo de permisos de Google no está incorporado al recorrido

**Problema:** `gmail.metadata`, `gmail.readonly`, `gmail.modify` y `gmail.settings.basic` son permisos distintos. Los permisos que permiten inventariar o modificar toda una casilla están clasificados como restringidos.

**Impacto:** una aplicación pública exige verificación. Almacenar o transmitir datos restringidos mediante servidores puede agregar una evaluación de seguridad. Pedir permisos “para el futuro” contradice el principio de mínimo acceso.

**Resolución:** autorización incremental:

1. análisis de sólo lectura con el permiso mínimo capaz de cumplir el hito;
2. solicitar `gmail.modify` recién cuando el usuario habilite acciones;
3. no solicitar `gmail.settings.basic` en el MVP;
4. documentar permisos y revocación en contexto.

Fuentes: [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy).

### A-08. “Metadatos solamente” no cubre todas las funciones propuestas

**Problema:** detectar con precisión adjuntos, tipos documentales, correos de bienvenida o mensajes mixtos puede requerir estructura MIME o contenido adicional.

**Impacto:** prometer protección documental perfecta contradice el acceso mínimo.

**Resolución:** el MVP clasifica con cabeceras, etiquetas y atributos disponibles. La detección de adjuntos o contenido se presenta como capacidad limitada hasta validar el formato de API necesario. El análisis de cuerpos queda fuera del primer corte.

### A-09. La baja automática necesita un contrato de seguridad más estricto

**Problema:** no todo `List-Unsubscribe` es una baja segura de un clic. Seguir enlaces genéricos puede activar rastreo, phishing o flujos manuales.

**Resolución:** el MVP de acciones sólo puede automatizar RFC 8058 cuando:

- existe HTTPS;
- existe `List-Unsubscribe-Post: List-Unsubscribe=One-Click`;
- existe autenticación DKIM válida que cubre ambas cabeceras;
- el usuario presta consentimiento específico;
- no se usan cookies, autorización ni redirecciones;
- el resultado se registra como “solicitud aceptada”, no como “baja cumplida”.

Los enlaces GET y `mailto:` se muestran como acciones manuales. Fuente: [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058.html).

### A-10. Faltaban criterios de aceptación

**Problema:** “agrupar correctamente” o “ser seguro” no son estados verificables sin casos concretos.

**Resolución:** el contrato MVP incorpora invariantes, fixtures sintéticos, pruebas de clasificación, simulación de planes, accesibilidad básica y una prohibición explícita de probar escrituras sobre la cuenta real sin una puerta de aprobación.

## 3. Incompatibilidades funcionales importantes

### A-11. “Interacción” no puede inferirse como lectura real

La etiqueta `UNREAD` sólo describe el estado del mensaje. No demuestra si el usuario leyó, valoró o utilizó el correo. La interfaz puede mostrar “estado de lectura actual”, pero no una tasa de apertura real.

### A-12. “Espacio recuperable” estaba expresado con demasiada seguridad

Gmail ofrece `sizeEstimate` por mensaje, pero mover mensajes a Archivo no libera espacio y moverlos a Papelera no garantiza una liberación inmediata. La aplicación debe mostrar **tamaño estimado seleccionado**, diferenciándolo de **espacio efectivamente liberado**.

### A-13. Las fechas del buscador de Gmail no son suficientes para una frontera civil exacta

Las búsquedas por fecha pueden utilizar una zona horaria diferente de la del usuario. Para una operación exacta “antes del 01/06/2024 en Córdoba”, el sistema debe comparar `internalDate` con un instante calculado en la zona horaria elegida y no confiar únicamente en el texto de búsqueda.

### A-14. Buscar con `gmail.metadata` tiene una limitación relevante

El parámetro `q` de `messages.list` no puede utilizarse con el permiso `gmail.metadata`. La arquitectura debe elegir entre:

- inventariar por paginación y filtrar localmente con el permiso mínimo; o
- pedir un permiso de lectura más amplio para usar consultas de Gmail.

Para el primer hito se recomienda inventario paginado con metadatos y filtros locales. Fuente: [messages.list](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list).

### A-15. Spam y Papelera requieren inclusión explícita

Los listados no incluyen necesariamente Spam y Papelera. Deben analizarse como ámbitos separados y nunca mezclarse silenciosamente con el correo activo. Papelera debe excluirse del inventario operativo inicial; Spam puede mostrarse en una sección independiente.

### A-16. “Reglas futuras” no significan automáticamente filtros de Gmail

Crear filtros persistentes requiere `gmail.settings.basic` y Gmail limita la cantidad de filtros. Una regla local sólo funciona cuando la aplicación se ejecuta. La interfaz debe distinguir ambas capacidades. Fuente: [crear filtros de Gmail](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.settings.filters/create).

### A-17. La sincronización incremental necesita estado y recuperación

Gmail utiliza `historyId` para sincronización parcial. Los registros pueden expirar y devolver `404`, caso en el que se necesita una sincronización completa. La especificación original mencionaba “continuar” pero no definía este fallback. Fuente: [sincronización de clientes Gmail](https://developers.google.com/workspace/gmail/api/guides/sync).

### A-18. Un plan puede quedar obsoleto

Entre la vista previa y la ejecución un mensaje puede:

- ser marcado como importante;
- recibir una etiqueta protegida;
- ser eliminado o movido;
- dejar de cumplir la fecha;
- pertenecer a una agrupación corregida.

La ejecución debe revalidar elegibilidad por mensaje y reportar diferencias. Una aprobación no es un cheque en blanco sobre mensajes futuros.

### A-19. Desuscribir y eliminar pueden terminar con resultados parciales diferentes

La baja puede fallar y la eliminación funcionar, o viceversa. El plan debe permitir elegir una política explícita:

- acciones independientes; o
- mover a Papelera sólo si la baja fue aceptada.

La recomendación inicial es tratarlas como independientes y mostrar ambos resultados.

### A-20. “Recuperar” tiene límites

Restaurar desde Papelera es distinto de revertir una baja, un filtro o una denuncia de spam. El historial debe declarar por acción si existe reversión técnica y durante qué estado.

## 4. Riesgos técnicos y de seguridad omitidos

### A-21. Visualizar HTML de correos puede ejecutar contenido no confiable

El MVP no renderizará cuerpos HTML, imágenes remotas ni píxeles de seguimiento. Los ejemplos se limitarán a texto seguro derivado de cabeceras.

### A-22. Las URL de baja son entradas hostiles

En una futura arquitectura alojada pueden generar SSRF, redirecciones o resolución DNS cambiante. La ejecución debe aislarse, bloquear redes privadas, no seguir redirecciones y no enviar cookies ni credenciales.

### A-23. Los tokens OAuth no deben almacenarse como archivos ordinarios en un producto comercial

El prototipo usa `token.json`. Para desarrollo personal puede aceptarse temporalmente, pero el producto debe usar el almacén seguro del sistema operativo o una solución equivalente.

### A-24. Falta idempotencia

Repetir una ejecución no debe enviar varias solicitudes de baja ni registrar dos veces la misma acción. Cada operación necesita un identificador estable y estados `pendiente`, `en curso`, `exitosa`, `fallida`, `omitida`.

### A-25. Falta registro transaccional ante cierres o fallos

El resultado no puede escribirse únicamente al final. Debe persistirse por lote para reanudar sin desconocer qué ya ocurrió.

### A-26. Faltan límites, reintentos y manejo de cuota

Las operaciones deben usar paginación, lotes acotados, backoff para fallos transitorios y un máximo de reintentos. `batchModify` admite como máximo 1.000 IDs por solicitud. Fuente: [messages.batchModify](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/batchModify).

### A-27. Falta estrategia de borrado de datos derivados

Desconectar Gmail no elimina automáticamente el índice local, las agrupaciones o el historial. La aplicación necesita acciones separadas para revocar acceso, borrar credenciales y borrar datos derivados.

### A-28. El análisis de correo con un proveedor de IA sería una transferencia adicional

El MVP no enviará asuntos, cabeceras ni cuerpos a un modelo externo. Una futura función de IA requerirá consentimiento, minimización, documentación, análisis de políticas y una arquitectura separada.

## 5. Problemas concretos del prototipo actual

El prototipo es una prueba descartable de conceptos y no debe conectarse a la cuenta real antes de corregir y verificar estos puntos:

1. Solicita `gmail.modify` desde el primer análisis en lugar de separar lectura y escritura.
2. La consulta cubre promociones, actualizaciones y spam antiguos, no el mapa completo de fuentes.
3. La llamada de listado no incluye explícitamente Spam/Papelera; `in:spam` no constituye evidencia suficiente de cobertura correcta.
4. Agrupa solamente por dirección exacta, sin fuentes ni flujos.
5. Confunde las etiquetas de Gmail con una clasificación propia muy reducida.
6. Invierte una lista que probablemente ya llega en orden reciente y puede elegir como ejemplo o baja un mensaje antiguo; no existe un contrato de orden verificado.
7. El plan posee un identificador, pero su integridad no se vuelve a verificar al cargarlo.
8. La ejecución no vuelve a consultar protecciones o elegibilidad.
9. No existe idempotencia para solicitudes de baja.
10. El registro final no contiene información suficiente para restauración granular.
11. Un fallo antes de escribir el resultado puede dejar acciones ejecutadas sin registro.
12. La comprobación DKIM es textual; no demuestra de forma robusta que el resultado `dkim=pass` corresponda a la firma que cubre las cabeceras de baja.
13. La validación DNS previa y la conexión HTTP posterior no constituyen por sí solas una defensa completa para una versión alojada.
14. El token se guarda sin integración con el almacén seguro del sistema.
15. Las pruebas son unitarias y sintéticas; no existe contrato de API, prueba de integración aislada ni simulación de fallos parciales.

Decisión: preservar el código como material de aprendizaje, pero exigir una auditoría explícita antes de reutilizar cada componente.

## 6. Huecos de producto y negocio

### A-29. El usuario pagador inicial todavía es demasiado amplio

“Personas con correo acumulado” es una población. Falta validar cuál subgrupo siente suficiente dolor y confianza para pagar.

Hipótesis inicial recomendada: personas con varios años de Gmail, miles de mensajes y miedo a borrar documentación importante.

### A-30. La promesa necesita una métrica observable

Propuesta:

> En una sesión, comprender las fuentes principales de una casilla y preparar una limpieza grande sin revisar los mensajes uno por uno.

No prometer “Inbox Zero”, espacio exacto liberado ni cancelación de pagos.

### A-31. El modelo comercial debe esperar la prueba de utilidad

El pase de limpieza y el Guardián son hipótesis, no requisitos del MVP. No se implementarán pagos antes de completar una limpieza personal y obtener evidencia con usuarios de prueba.

### A-32. Falta una estrategia explícita frente a Gmail y competidores

La ventaja no puede ser únicamente desuscripción. El producto debe validarse por:

- mapa de fuentes y flujos;
- separación de publicidad y documentación;
- acciones históricas por fecha;
- explicaciones y protecciones;
- control local y auditable.

## 7. Decisiones corregidas

Se recomiendan como contrato inicial:

1. Gmail únicamente.
2. Una cuenta por perfil en el primer corte.
3. Windows primero, aplicación local abierta en el navegador.
4. Datos e índice locales.
5. Metadatos sin cuerpos ni recursos remotos.
6. Clasificación determinista y explicable antes de incorporar IA.
7. Primer hito completamente sintético y sin OAuth.
8. Segundo hito de sólo lectura.
9. Acciones reales recién en un hito separado y con autorización incremental.
10. Sin filtros persistentes, Guardián en segundo plano, múltiples proveedores, pagos ni eliminación definitiva en el MVP.

Estas decisiones conservan el camino comercial, pero impiden que la visión futura contamine la primera entrega verificable.
