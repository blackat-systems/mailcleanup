# Especificación funcional de la aplicación

Estado: visión futura heredada. No constituye alcance aprobado ni autorización
de desarrollo.

> Para iniciar desarrollo, usar primero `CONTRATO_MVP.md` y
> `AUDITORIA_PRE_DESARROLLO.md`. Cuando exista una diferencia, el contrato MVP
> prevalece. Este documento conserva la visión completa y el horizonte futuro.

## 1. Tesis del producto

La aplicación no es solamente un limpiador de correo. Es un centro de control que transforma una casilla acumulada en un mapa de:

- quién envía correos;
- en representación de qué organización o servicio;
- con qué finalidad;
- desde cuándo;
- con qué frecuencia;
- qué relación parece existir con el usuario;
- qué conviene conservar, revisar, silenciar, desuscribir o eliminar.

Promesa principal:

> Entendé quién ocupa tu correo y recuperá el control sin perder nada importante.

La unidad central no será el mensaje ni la dirección de envío aislada. Será la **fuente**, dividida en **flujos** diferenciados.

Ejemplo:

```text
Microsoft (fuente)
├── Seguridad de la cuenta (flujo protegido)
├── Facturación y compras (flujo documental)
├── Novedades de Windows (flujo informativo)
└── Rewards y promociones (flujo comercial)
```

## 2. Usuario inicial y evolución

### Usuario inicial

Una persona con varios años de correo acumulado que:

- recibe newsletters, publicidad, notificaciones y spam;
- desconoce cuántas suscripciones mantiene;
- teme borrar comprobantes o mensajes importantes;
- no quiere revisar miles de mensajes individualmente;
- necesita tomar decisiones por fuente, categoría o período.

### Evolución posible

- Personas con varias cuentas personales.
- Familias que quieran ordenar cuentas antiguas.
- Profesionales y freelancers con múltiples servicios.
- Pequeños negocios con casillas operativas saturadas.
- Personas que migran de una dirección a otra.

La primera experiencia debe optimizarse para una persona y una cuenta. La arquitectura conceptual no debe impedir varias cuentas en el futuro.

## 3. Principios del producto

1. **Comprender antes de actuar.** Primero se construye el mapa; después se proponen acciones.
2. **Fuente y flujo antes que remitente.** Una organización puede enviar comunicaciones de distinta importancia.
3. **La protección gana.** Ninguna automatización puede atravesar silenciosamente una protección.
4. **La incertidumbre se muestra.** Lo desconocido se clasifica como desconocido.
5. **Toda decisión se explica.** La aplicación debe mostrar las evidencias que sostienen una clasificación.
6. **Las acciones son independientes.** Desuscribir, borrar, bloquear, archivar y denunciar como spam no son sinónimos.
7. **Reversible por defecto.** La limpieza inicial utiliza Papelera o Archivo; no eliminación definitiva.
8. **Confirmación proporcional.** Se confirma el impacto real, no se repite un diálogo genérico para todo.
9. **Mínimo acceso necesario.** Analizar metadatos antes de solicitar o utilizar información más profunda.
10. **El usuario enseña mediante decisiones.** Las correcciones pueden transformarse en reglas, pero nunca sin consentimiento.

## 4. Modelo conceptual

### Cuenta

Casilla conectada. Mantiene sus permisos, estado de sincronización y políticas propias.

### Fuente

Organización, servicio, persona o infraestructura responsable de los mensajes. Puede reunir múltiples direcciones y dominios cuando existe evidencia suficiente.

### Flujo

Serie coherente de mensajes emitida por una fuente con una finalidad común: seguridad, facturación, marketing, noticias, actividad social, soporte, etcétera.

### Mensaje

Correo individual. Conserva sus atributos propios: fecha, remitente, asunto, etiquetas, adjuntos, estado y evidencias técnicas.

### Evidencia

Señal utilizada para inferir identidad o clasificación. Por ejemplo: dominio, `List-ID`, cabecera de desuscripción, etiqueta de Gmail, patrón de asunto o frecuencia.

### Política

Decisión persistente del usuario: proteger, conservar, archivar, enviar a Papelera, silenciar o revisar.

### Plan de acción

Vista previa inmutable de una operación futura: alcance, exclusiones, muestras, consecuencias y confirmaciones requeridas.

### Ejecución

Registro de lo que efectivamente ocurrió, con resultados parciales, fallos y posibilidades de recuperación.

## 5. Secciones de la aplicación

### 5.1. Bienvenida y conexión

Objetivo: explicar el valor y conseguir acceso informado.

Funciones:

1. Explicar qué datos necesita la aplicación y para qué.
2. Diferenciar análisis de modificación.
3. Conectar una cuenta mediante autorización oficial.
4. Verificar qué cuenta fue conectada.
5. Elegir un análisis rápido o completo.
6. Definir protecciones iniciales: seguridad, pagos, salud, trabajo, documentos y remitentes elegidos.
7. Permitir desconectar y eliminar el índice local.

### 5.2. Centro de análisis

Objetivo: convertir la casilla en un inventario comprensible.

Funciones:

8. Mostrar progreso por períodos y volumen.
9. Permitir pausar y continuar.
10. Trabajar por lotes para no perder el avance.
11. Mostrar cuántos mensajes, fuentes y flujos se identificaron.
12. Informar limitaciones o elementos que no pudieron clasificarse.
13. Actualizar únicamente los cambios posteriores en análisis futuros.
14. Ejecutar análisis de sólo lectura sin preparar acciones.

### 5.3. Inicio o panorama

Objetivo: responder rápidamente qué está pasando en la casilla.

Funciones:

15. Mostrar cantidad de mensajes analizados.
16. Mostrar número de fuentes y flujos.
17. Mostrar suscripciones confirmadas, probables e inactivas.
18. Mostrar los mayores generadores de volumen.
19. Mostrar spam frecuente y remitentes sospechosos.
20. Mostrar candidatos protegidos y candidatos a limpieza.
21. Estimar espacio recuperable cuando existan datos suficientes.
22. Mostrar fuentes nuevas desde el último análisis.
23. Mostrar bajas incumplidas o fuentes que reaparecieron.
24. Ofrecer accesos directos a las decisiones más rentables en tiempo o espacio.

### 5.4. Explorador de fuentes

Objetivo: administrar relaciones completas, no correos aislados.

Funciones:

25. Listar fuentes con nombre, rubro, volumen, frecuencia, primer y último correo.
26. Buscar por nombre, dirección o dominio.
27. Filtrar por categoría, estado de suscripción, riesgo, protección, frecuencia y período.
28. Ordenar por volumen histórico, volumen reciente, antigüedad, frecuencia o confianza.
29. Agrupar fuentes relacionadas cuando la evidencia sea sólida.
30. Separar manualmente fuentes agrupadas incorrectamente.
31. Fusionar manualmente direcciones pertenecientes a una misma fuente.
32. Corregir nombre, categoría y tipo.
33. Marcar una fuente como confiable, protegida, ignorada o sospechosa.
34. Seleccionar varias fuentes para una operación conjunta.

### 5.5. Detalle de fuente

Objetivo: permitir una decisión informada sobre una organización o servicio.

Funciones:

35. Mostrar direcciones y dominios asociados.
36. Mostrar los flujos detectados.
37. Mostrar primer mensaje encontrado y última actividad.
38. Mostrar una línea temporal de volumen.
39. Mostrar frecuencia aproximada y cambios de comportamiento.
40. Mostrar asuntos representativos sin abrir todos los mensajes.
41. Mostrar cuántos mensajes están leídos, destacados, etiquetados o contienen adjuntos.
42. Mostrar por qué se identificó la fuente y qué tan sólida es la identificación.
43. Mostrar si existe baja automática, manual o inexistente.
44. Mostrar acciones previas y reglas vigentes.
45. Permitir actuar sobre toda la fuente o solamente sobre uno de sus flujos.

### 5.6. Suscripciones

Objetivo: administrar newsletters y comunicaciones voluntarias o aparentemente voluntarias.

Funciones:

46. Separar suscripciones confirmadas, probables, desconocidas e inactivas.
47. Mostrar fecha de suscripción sólo cuando exista evidencia.
48. Mostrar “primer correo encontrado” cuando la fecha real no pueda conocerse.
49. Identificar correos de bienvenida o confirmación de alta.
50. Ofrecer conservar, desuscribir, pausar, bloquear o revisar.
51. Desuscribir y conservar historial.
52. Desuscribir y mover historial a Papelera.
53. Programar limpieza de mensajes anteriores a una fecha.
54. Registrar fecha, método y resultado de cada solicitud de baja.
55. Vigilar mensajes posteriores a una baja.
56. Proponer bloquear o marcar como spam a una fuente que incumple reiteradamente.

### 5.7. Ruido y spam

Objetivo: separar comunicaciones molestas, abusivas o sospechosas.

Funciones:

57. Mostrar spam reconocido por el proveedor.
58. Mostrar spam probable detectado por patrones.
59. Agrupar campañas relacionadas aunque roten direcciones.
60. Distinguir correo comercial legítimo de correo potencialmente malicioso.
61. Bloquear acciones de desuscripción inseguras.
62. Permitir enviar futuros mensajes a Spam sin solicitar una baja.
63. Permitir eliminar el historial de una campaña.
64. Mantener una lista de remitentes o dominios bloqueados.
65. Mostrar falsos positivos corregidos por el usuario.

### 5.8. Estudio de limpieza

Objetivo: construir una operación precisa antes de ejecutarla.

Funciones:

66. Seleccionar fuentes, flujos, categorías o resultados de una búsqueda.
67. Elegir todos los mensajes, solamente los anteriores a una fecha o un rango.
68. Elegir mensajes mayores a una antigüedad relativa.
69. Elegir solamente leídos o no destacados.
70. Conservar los últimos N mensajes.
71. Excluir mensajes con adjuntos.
72. Excluir etiquetas, remitentes, palabras o tipos documentales.
73. Elegir Archivo o Papelera.
74. Combinar desuscripción y disposición del historial sin confundir ambas acciones.
75. Mostrar el alcance exacto antes de confirmar.
76. Mostrar mensajes de ejemplo y exclusiones.
77. Guardar una selección como regla futura.
78. Guardar una selección como operación única.

### 5.9. Centro de protección

Objetivo: reducir el miedo a perder información relevante.

Funciones:

79. Proteger fuentes completas.
80. Proteger flujos específicos.
81. Proteger categorías documentales.
82. Proteger mensajes destacados o marcados como importantes.
83. Proteger mensajes con adjuntos, opcionalmente.
84. Proteger remitentes y dominios definidos por el usuario.
85. Proteger períodos recientes.
86. Mostrar qué protección excluyó cada mensaje de una operación.
87. Permitir un desbloqueo manual excepcional con confirmación reforzada.

### 5.10. Reglas y Guardián

Objetivo: evitar que la casilla vuelva al mismo estado.

Funciones:

88. Crear reglas por fuente, flujo o categoría.
89. Simular una regla sobre el historial antes de activarla.
90. Ejecutar reglas automáticamente, con aprobación periódica o sólo sugerirlas.
91. Conservar los últimos N mensajes de un flujo.
92. Archivar o enviar a Papelera después de cierta antigüedad.
93. Avisar cuando una fuente supera determinada frecuencia.
94. Detectar fuentes nuevas y pedir una decisión.
95. Proponer una regla cuando el usuario repite la misma acción.
96. Pausar una regla sin eliminarla.
97. Mostrar la prioridad y el motivo de cada regla.
98. Evitar reglas de eliminación definitiva.

### 5.11. Historial y recuperación

Objetivo: que ninguna operación desaparezca en una caja negra.

Funciones:

99. Registrar planes creados, aprobados, ejecutados o cancelados.
100. Mostrar cantidad real de mensajes afectados.
101. Mostrar acciones exitosas, fallidas y omitidas.
102. Restaurar mensajes desde Papelera cuando todavía sea posible.
103. Registrar solicitudes de baja, que no son reversibles de la misma manera.
104. Reintentar solamente operaciones fallidas.
105. Exportar un informe de la limpieza.
106. Mostrar qué versión de una regla tomó cada decisión.

### 5.12. Configuración y confianza

Objetivo: controlar cuentas, datos y comportamiento global.

Funciones:

107. Gestionar cuentas conectadas.
108. Elegir almacenamiento y retención del índice.
109. Borrar los datos derivados sin borrar correos.
110. Configurar categorías y protecciones predeterminadas.
111. Elegir frecuencia de análisis y mantenimiento.
112. Configurar notificaciones.
113. Exportar e importar reglas.
114. Ver permisos concedidos y revocarlos.
115. Consultar una explicación sencilla de privacidad y seguridad.

## 6. Cómo trabajará la aplicación

### Fase A: descubrimiento

1. El usuario conecta una cuenta.
2. La aplicación verifica identidad y permisos.
3. Se realiza un análisis inicial prioritariamente con metadatos.
4. Los mensajes se normalizan sin modificar la casilla.
5. Se identifican remitentes técnicos, fuentes y posibles organizaciones.
6. Cada fuente se divide en flujos cuando sus mensajes tienen finalidades distintas.
7. Se clasifica cada elemento en varias dimensiones.
8. Se aplican protecciones iniciales.
9. Se construye el panorama.

### Fase B: decisión

10. El usuario explora fuentes y categorías.
11. Corrige agrupaciones o clasificaciones cuando haga falta.
12. Elige acciones y condiciones temporales.
13. La aplicación construye un plan exacto.
14. Se muestran ejemplos, exclusiones y consecuencias.

### Fase C: ejecución

15. La aplicación vuelve a validar el alcance.
16. Solicita una confirmación proporcional al riesgo.
17. Ejecuta por lotes pequeños y registra resultados.
18. Un fallo parcial no oculta los éxitos ni repite acciones innecesarias.
19. Los mensajes se archivan o mueven a Papelera según lo elegido.
20. Las bajas se ejecutan y registran de forma independiente.

### Fase D: mantenimiento

21. La aplicación analiza solamente cambios nuevos.
22. Detecta nuevas fuentes, cambios de frecuencia e incumplimientos de bajas.
23. Aplica reglas permitidas o presenta sugerencias.
24. Produce un resumen periódico breve.

## 7. Sistema de clasificación

Un correo no recibirá una única etiqueta absoluta. Se clasificará en ejes independientes.

### Eje A: identidad de la fuente

- Persona.
- Organización conocida.
- Servicio o producto.
- Lista de correo.
- Infraestructura automática.
- Remitente desconocido.
- Campaña sospechosa.

### Eje B: rubro o actividad

- Medios y noticias.
- Aplicaciones y software.
- Tecnología y sistemas operativos.
- Comercio electrónico y tiendas.
- Bancos, tarjetas y finanzas.
- Servicios pagos y membresías.
- Redes sociales.
- Educación.
- Trabajo y empleo.
- Salud.
- Gobierno y trámites.
- Viajes y reservas.
- Entretenimiento y streaming.
- Videojuegos.
- Comunidades y foros.
- Servicios domésticos y públicos.
- Seguridad digital.
- Publicidad genérica.
- Personal.
- Desconocido.

### Eje C: intención del flujo

- Seguridad y acceso.
- Transaccional.
- Facturación y comprobantes.
- Operativo o de servicio.
- Soporte.
- Notificación de actividad.
- Editorial o informativo.
- Educativo.
- Promocional.
- Encuesta o investigación.
- Captación o venta.
- Spam probable.
- Potencialmente malicioso.

### Eje D: relación o suscripción

- Suscripción confirmada y activa.
- Suscripción probable y activa.
- Suscripción inactiva.
- Baja solicitada.
- Baja incumplida.
- Comunicación transaccional, no una suscripción.
- Comunicación no solicitada.
- Estado desconocido.

### Eje E: sensibilidad y protección

- Protección crítica: seguridad, identidad, salud o asuntos legales.
- Protección documental: facturas, recibos, garantías, contratos o reservas.
- Protección personal: conversaciones humanas o fuentes elegidas.
- Conservación sugerida.
- Limpieza sugerida.
- Revisión obligatoria.

### Eje F: confianza

- Alta: varias evidencias coherentes y verificables.
- Media: señales suficientes para sugerir, no para automatizar.
- Baja: evidencia ambigua o contradictoria.
- Desconocida: no hay base suficiente.

No se utilizará un porcentaje decorativo. La interfaz mostrará las evidencias concretas.

## 8. Evidencias utilizadas para clasificar

De mayor a menor fuerza aproximada:

1. Decisión explícita previa del usuario.
2. Identificadores estables de listas y flujos.
3. Cabeceras de suscripción y desuscripción.
4. Autenticación del dominio y coherencia técnica del remitente.
5. Dirección, dominio y organización asociada.
6. Etiquetas creadas por el usuario.
7. Etiquetas y categorías del proveedor de correo.
8. Patrones repetidos de asunto y plantilla.
9. Frecuencia, periodicidad y horario.
10. Presencia de adjuntos y tipo documental.
11. Palabras y estructuras características.
12. Contenido del mensaje, solamente cuando sea imprescindible y esté permitido.

La inteligencia artificial puede sugerir nombres, rubros o separaciones, pero no será la única evidencia para eliminar automáticamente.

## 9. Identificación de fuentes y flujos

### Regla de agrupación

La aplicación comienza separando y sólo fusiona cuando hay evidencia positiva. Es preferible mostrar dos fuentes relacionadas que unir por error facturación y publicidad.

Señales de que varias direcciones pertenecen a la misma fuente:

- dominio organizacional compartido;
- autenticación coherente;
- nombre de marca estable;
- enlaces y pie institucional coincidentes;
- identificadores de lista relacionados;
- correcciones confirmadas por el usuario.

Señales para dividir una fuente en flujos:

- distintos identificadores de lista;
- finalidad claramente diferente;
- vocabulario y plantilla diferentes;
- remitentes funcionales como `security`, `billing`, `news` o `offers`;
- periodicidad diferente;
- decisiones diferentes del usuario.

## 10. Fechas y afirmaciones temporales

La aplicación diferenciará:

- **Fecha de suscripción confirmada:** existe correo de bienvenida, confirmación o evidencia equivalente.
- **Fecha de suscripción estimada:** existen indicios, pero no confirmación directa.
- **Primer correo encontrado:** dato objetivo dentro del período analizado.
- **Primera actividad analizada:** el escaneo no alcanzó toda la historia.

Nunca se presentará “primer correo encontrado” como “fecha de suscripción” sin aclaración.

## 11. Reglas y resolución de contradicciones

Orden de autoridad:

1. Bloqueo técnico o de seguridad.
2. Protección absoluta creada por el usuario.
3. Decisión manual sobre mensajes concretos.
4. Regla de flujo.
5. Regla de fuente.
6. Regla de categoría.
7. Regla global.
8. Sugerencia automática.

Dentro del mismo nivel:

- la regla más específica gana;
- si tienen igual especificidad, gana la decisión explícita más reciente;
- si todavía existe conflicto, no se ejecuta y se solicita revisión.

Reglas adicionales:

- una protección puede excluir mensajes de una limpieza sin cancelar el resto del plan;
- una baja no autoriza a borrar historial;
- borrar historial no autoriza a crear una baja;
- bloquear no equivale a marcar como spam;
- una regla nunca realiza eliminación definitiva;
- una corrección manual no se generaliza silenciosamente a otras fuentes.

## 12. Confirmaciones proporcionales

### Sin confirmación adicional

- analizar;
- buscar y filtrar;
- corregir una categoría;
- crear una vista previa;
- proteger una fuente;
- pausar una regla.

### Confirmación simple

- archivar un lote;
- mover a Papelera un lote ordinario;
- activar una regla reversible;
- restaurar mensajes.

La pantalla debe mostrar cantidad, período, fuentes, ejemplos y exclusiones.

### Confirmación reforzada

- desuscribirse;
- bloquear una fuente;
- marcar grandes lotes como spam;
- atravesar una protección;
- afectar mensajes críticos o documentales;
- ejecutar una operación excepcionalmente grande.

### No disponible inicialmente

- eliminación definitiva automática;
- vaciado automático de Papelera;
- acciones sobre Enviados o Borradores;
- baja mediante enlaces no confiables ejecutada a ciegas.

## 13. Casos límite y comportamiento esperado

1. **Una empresa utiliza muchos dominios:** mantener separados hasta tener evidencia suficiente.
2. **Varias empresas usan la misma plataforma de envíos:** no agruparlas por la infraestructura compartida.
3. **Un remitente cambia de dirección:** sugerir continuidad y pedir revisión si impacta reglas.
4. **Un correo promocional contiene una factura:** la protección documental excluye ese mensaje.
5. **Una alerta de seguridad está dentro de Promociones:** intención y sensibilidad prevalecen sobre la categoría del proveedor.
6. **Un mensaje está marcado como importante:** queda excluido por defecto.
7. **Un hilo mezcla mensajes protegidos y eliminables:** decidir por mensaje, no por hilo completo.
8. **Una baja redirige a una web:** informar que requiere intervención y no simular éxito.
9. **Una baja devuelve éxito pero siguen llegando correos:** marcar posible incumplimiento.
10. **La fuente carece de baja:** ofrecer bloquear, filtrar o marcar como spam según el caso.
11. **Un mensaje tiene varios métodos de baja:** priorizar el estándar verificable y registrar el método.
12. **La casilla cambia durante la vista previa:** revalidar antes de ejecutar y mostrar diferencias.
13. **La conexión se interrumpe:** conservar avance y reanudar sin duplicar acciones.
14. **Una ejecución falla parcialmente:** registrar resultados por lote y reintentar sólo fallos.
15. **La clasificación cambia:** no reescribir decisiones históricas; aplicar la nueva clasificación hacia adelante.
16. **Dos reglas chocan:** aplicar precedencia o detener ese subconjunto.
17. **El usuario deshace una limpieza:** restaurar lo reversible sin fingir que una baja también fue revertida.
18. **Una fuente suplanta a otra:** identidad técnica y autenticación impiden fusionarla automáticamente.
19. **Un alias revela quién compartió la dirección:** mostrarlo como evidencia, no como acusación concluyente.
20. **Un posible servicio pago aparece:** informar “posible gasto recurrente”; nunca afirmar ni cancelar un pago basándose sólo en correo.

## 14. Usos comunes

- Cancelar newsletters que ya no interesan.
- Borrar años de promociones de una tienda.
- Conservar solamente los últimos mensajes de una aplicación.
- Limpiar diarios y alertas informativas antiguas.
- Vaciar spam acumulado de forma recuperable.
- Mantener comprobantes mientras se elimina publicidad.
- Crear reglas para que el ruido no regrese.
- Administrar varias direcciones pertenecientes a una misma organización.

## 15. Usos especiales o menos evidentes

- Inventariar cuentas y servicios olvidados.
- Detectar posibles membresías o gastos recurrentes.
- Preparar una migración a otra dirección de correo.
- Auditar qué fuentes incumplen solicitudes de baja.
- Descubrir campañas que rotan remitentes.
- Reconstruir períodos de actividad digital sin leer contenido personal.
- Detectar aumentos anormales en la frecuencia de una fuente.
- Aplicar un modo de reducción temporal del ruido.
- Preparar un archivo documental antes de una limpieza profunda.
- Identificar dónde se utilizó un alias de correo.

## 16. Alcance propuesto por versiones

### Experimento personal

- Una cuenta de Gmail.
- Análisis de metadatos.
- Agrupación por remitente y fuente sugerida.
- Categorías principales.
- Detalle con muestras.
- Selección por fuente y fecha.
- Vista previa.
- Papelera y baja segura.
- Registro local.

### Versión 1 comercial

- Experiencia visual completa.
- Fuentes y flujos corregibles.
- Clasificación multidimensional explicable.
- Protecciones.
- Estudio de limpieza.
- Pase de limpieza.
- Informes y recuperación.
- Varias cuentas en planes superiores.

### Versión 2: Guardián

- Análisis incremental.
- Reglas persistentes.
- Fuentes nuevas.
- Alertas por frecuencia.
- Seguimiento de bajas.
- Resúmenes periódicos.
- Plan recurrente.

### Visión avanzada

- Outlook y otros proveedores.
- Inventario de cuentas asociadas.
- Detección asistida de posibles gastos.
- Plan familiar.
- Herramientas para profesionales y pequeños equipos.
- Catálogo comunitario opcional de fuentes, sin compartir correos personales.

## 17. Modelo comercial preliminar

1. **Diagnóstico gratuito:** mapa parcial y oportunidades principales.
2. **Pase de limpieza:** pago único por una ventana limitada de limpieza profunda.
3. **Guardián:** suscripción para mantenimiento y reglas continuas.
4. **Multi-cuenta o familiar:** plan superior cuando exista demanda real.

No se venderán ni utilizarán datos del correo para publicidad. La confianza es parte del producto, no solamente una obligación legal.

## 18. Métricas de éxito del producto

- Porcentaje de fuentes correctamente agrupadas.
- Porcentaje de flujos correctamente separados.
- Cero mensajes críticos eliminados sin aprobación reforzada.
- Tiempo hasta la primera decisión útil.
- Tiempo necesario para revisar las principales fuentes.
- Cantidad de correos y espacio tratados por operación.
- Tasa de bajas que dejan de enviar mensajes.
- Porcentaje de clasificaciones corregidas.
- Porcentaje de usuarios que regresan para mantenimiento.
- Confianza declarada antes y después de la limpieza.

## 19. Hipótesis que deben validarse

1. Las personas comprenden mejor “fuentes y flujos” que una lista de remitentes.
2. Ver ejemplos y exclusiones reduce el miedo a borrar.
3. La limpieza por fecha y tipo aporta más valor que “eliminar todo”.
4. Un pase de limpieza resuelve mejor la compra inicial que una suscripción obligatoria.
5. El Guardián aporta valor recurrente suficiente para sostener una suscripción.
6. El procesamiento local mejora significativamente la confianza.
7. La clasificación puede ser útil utilizando principalmente metadatos.
8. Las personas desean administrar relaciones, no solamente newsletters.

## 20. Decisiones fundacionales pendientes

Estas decisiones cambian materialmente el diseño posterior:

1. Gmail solamente en la primera versión o Gmail y Outlook desde el inicio.
2. Producto local primero o servicio alojado desde la primera beta.
3. Enfoque inicial en limpieza histórica o equilibrio desde el principio con mantenimiento continuo.
4. Clasificación basada sólo en metadatos o análisis opcional del contenido para casos ambiguos.
5. Marca orientada a “limpieza” o a “mapa y control de relaciones digitales”.
