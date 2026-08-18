# Contrato del MVP

Estado: aprobado por Joa para ejecutar el Hito 0 el 18 de agosto de 2026.

Este documento prevalece sobre la visión amplia para el desarrollo inicial.

## 1. Resultado buscado

Construir una aplicación local para Windows que permita conectar una cuenta de Gmail, inventariar metadatos de mensajes entrantes y mostrar un mapa explicable de remitentes, fuentes sugeridas y flujos, sin modificar la casilla durante los dos primeros hitos.

El usuario debe poder comprender las principales fuentes de volumen y preparar una selección de limpieza sin revisar mensajes individualmente.

## 2. Alcance por hitos

### Hito 0: fundamento sin Gmail

Objetivo: demostrar el modelo y las reglas sin datos privados ni permisos externos.

Incluye:

- modelo local versionado;
- fixtures sintéticos realistas;
- normalización de remitentes y cabeceras;
- identificación conservadora de listas y flujos;
- clasificación multidimensional explicable;
- protecciones;
- plan de limpieza simulado;
- pruebas de invariantes y casos límite;
- interfaz navegable con datos sintéticos.

No incluye OAuth, Gmail real, desuscripción ni modificación de mensajes.

Puerta de salida: Joa revisa la interfaz y los resultados sintéticos y autoriza el Hito 1.

### Hito 1: mapa real de sólo lectura

Objetivo: construir el mapa de una cuenta real sin modificarla.

Incluye:

- OAuth oficial con permiso de metadatos de sólo lectura;
- una cuenta;
- sincronización inicial reanudable;
- exclusión de Enviados, Borradores y Papelera;
- sección separada para Spam;
- índice local;
- fuentes, flujos, categorías, evidencias y confianza;
- correcciones manuales persistentes;
- borrado de credenciales e índice;
- manejo de cuota, reintentos y errores.

No incluye cuerpos, imágenes remotas, adjuntos descargados ni acciones sobre Gmail.

Puerta de salida: se audita el mapa, se corrigen falsos agrupamientos y Joa autoriza el Hito 2.

### Hito 2: planificación sin efectos

Objetivo: preparar operaciones exactas y comprobables.

Incluye:

- seleccionar por remitente, fuente o flujo;
- condiciones por fecha civil, antigüedad y estado de lectura;
- exclusiones por estrella, importancia, etiquetas y protecciones locales;
- conservar los últimos N;
- vista previa inmutable;
- muestras seguras;
- tamaño estimado seleccionado;
- simulación de revalidación;
- historial de planes sin ejecutar.

No incluye todavía modificación de Gmail.

Puerta de salida: una batería sintética demuestra que ningún mensaje protegido entra silenciosamente en un plan y Joa autoriza el Hito 3.

### Hito 3: acciones controladas

Objetivo: ejecutar solamente planes aprobados.

Incluye:

- autorización incremental para `gmail.modify`;
- revalidación por mensaje;
- Archivo y Papelera;
- restauración mientras Gmail la permita;
- baja RFC 8058 con consentimiento específico;
- registro transaccional e idempotente;
- resultados parciales y reintentos seguros;
- prueba inicial con un lote pequeño elegido por Joa.

No incluye eliminación definitiva, filtros de Gmail, bloqueo permanente, automatización en segundo plano ni acciones masivas sin revisión.

## 3. Secciones del MVP

1. **Conexión:** cuenta, permisos y estado.
2. **Análisis:** progreso, pausa, reanudación y errores.
3. **Panorama:** totales y mayores fuentes de volumen.
4. **Fuentes:** lista, búsqueda, filtros y correcciones.
5. **Detalle:** remitentes, flujos, evidencias y muestras.
6. **Plan de limpieza:** selección, condiciones, exclusiones y vista previa.
7. **Historial:** planes y, desde Hito 3, ejecuciones.
8. **Configuración:** protecciones, credenciales e índice local.

Suscripciones y Spam aparecen inicialmente como vistas filtradas de Fuentes, no como subsistemas independientes.

## 4. Clasificación MVP

### Rubro de la fuente

- Medios y contenido.
- Software y servicios digitales.
- Comercio y compras.
- Finanzas.
- Trabajo y educación.
- Salud y gobierno.
- Viajes y entretenimiento.
- Social y comunidades.
- Servicios domésticos.
- Personal.
- Desconocido.

### Intención del flujo

- Seguridad.
- Documento o comprobante.
- Operativo o soporte.
- Notificación.
- Informativo o editorial.
- Promocional o venta.
- Comunicación personal.
- Sospechoso.
- Desconocido.

### Estado de suscripción

- Confirmada.
- Probable.
- No corresponde.
- Baja solicitada.
- Posible incumplimiento.
- Desconocido.

### Protección

- Crítica.
- Documental.
- Elegida por el usuario.
- Ordinaria.
- Revisión obligatoria.

### Confianza

- Alta.
- Media.
- Baja.
- Contradictoria.

Cada clasificación debe incluir `evidencias[]`. No se mostrarán porcentajes inventados.

## 5. Invariantes de seguridad

1. Hitos 0, 1 y 2 no realizan llamadas de modificación.
2. Enviados, Borradores y Papelera nunca forman parte de un plan ordinario.
3. Estrella, importancia, protección crítica y protección manual excluyen mensajes por defecto.
4. Una fuente de confianza baja no se fusiona automáticamente con otra.
5. Una clasificación contradictoria no habilita acciones automáticas.
6. Un plan sólo contiene IDs existentes al momento de su creación y se revalida antes de actuar.
7. Ningún plan incluye mensajes llegados después de su aprobación.
8. Desuscribir y disponer del historial son decisiones separadas.
9. Ninguna respuesta HTTP se presenta como prueba definitiva de baja cumplida.
10. No se renderizan cuerpos HTML ni se cargan imágenes remotas.
11. No se envían datos de correo a servicios de IA en el MVP.
12. No existe eliminación definitiva.
13. Toda acción real genera registro durable antes, durante y después de cada lote.

## 6. Fixtures sintéticos obligatorios

La suite debe incluir como mínimo:

1. Una misma fuente con seguridad, facturación y promociones.
2. Dos marcas diferentes usando la misma plataforma de email.
3. Una marca que cambia de dominio o dirección.
4. Una factura dentro de un flujo promocional.
5. Un correo de seguridad mal categorizado por Gmail.
6. Una newsletter autenticada con baja de un clic.
7. Una newsletter con baja manual.
8. Spam que suplanta una marca conocida.
9. Un mensaje personal automatizado incorrectamente.
10. Un hilo con mensajes de distinta protección.
11. Mensajes con y sin estrella, importancia y etiquetas personales.
12. Fechas ubicadas a ambos lados de una frontera civil en Córdoba.
13. Fallos parciales y reintentos.
14. Un plan obsoleto por cambio de etiqueta.

Nunca se usarán correos reales, nombres privados ni tokens en fixtures, logs o capturas.

## 7. Criterios de aceptación

### Hito 0

- Todos los fixtures producen resultados deterministas.
- Cada agrupación y clasificación muestra sus evidencias.
- Los casos ambiguos permanecen separados o desconocidos.
- Las protecciones excluyen correctamente mensajes.
- La interfaz permite recorrer panorama, fuentes, detalle y plan.
- Las pruebas unitarias y de integración local pasan.
- La interfaz se renderiza e inspecciona en resoluciones de escritorio y móvil estrecho.

### Hito 1

- La cuenta mostrada coincide con la autorizada.
- El escaneo puede interrumpirse y reanudarse.
- No existe ninguna llamada de modificación en el recorrido.
- La desconexión revoca o elimina las credenciales locales según lo elegido.
- El índice puede borrarse completamente.
- Los errores de cuota y red no corrompen el progreso.

### Hito 2

- La fecha civil se convierte de forma explícita a instantes.
- La vista previa enumera alcance, exclusiones y muestras.
- Un cambio de protección invalida o reduce el plan.
- Los IDs futuros no pueden incorporarse a un plan aprobado.
- El usuario puede cancelar sin efectos.

### Hito 3

- Se solicita permiso de modificación en contexto.
- Cada lote es idempotente y queda registrado.
- Los mensajes protegidos al revalidar se omiten.
- Los fallos parciales pueden reintentarse sin repetir éxitos.
- La primera prueba real afecta un lote pequeño aprobado por Joa.
- No se vacía Papelera ni se utiliza borrado definitivo.

## 8. Fuera del MVP

- Outlook y otros proveedores.
- Varias cuentas simultáneas.
- Cuerpos completos e IA externa.
- Filtros persistentes de Gmail.
- Guardián funcionando con la aplicación cerrada.
- Aplicación móvil.
- Inventario de cuentas y cancelación de servicios pagos.
- Pagos, planes comerciales y analítica de negocio.
- Clasificación comunitaria.
- Eliminación definitiva.

Estas capacidades permanecen en la visión, pero no son dependencias del MVP.

## 9. Arquitectura confirmada para el Hito 0

- Plataforma inicial: Windows.
- Experiencia: aplicación web local abierta en el navegador.
- Backend: Python, preservando únicamente componentes auditados del prototipo.
- Persistencia: SQLite local con migraciones desde el comienzo.
- Interfaz: React con TypeScript en un frontend separado y preparado para empaquetado futuro.
- Tokens: almacén seguro del sistema operativo antes de conectar Gmail real.
- Red: sólo loopback para la aplicación local; OAuth y Gmail como servicios externos esperados.

Joa confirmó explícitamente esta arquitectura. La comparación y sus consecuencias se registran en `docs/adr/0001-arquitectura-hito-0.md`. Esta confirmación autoriza únicamente el Hito 0 con datos sintéticos; no autoriza OAuth, acceso a Gmail ni acciones reales.
