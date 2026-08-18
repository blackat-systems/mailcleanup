# Línea base de seguridad y privacidad v1

Estado: aprobada por MAIN para preparar D3 exclusivamente con dobles sintéticos.

Autoridad: instrucción explícita de Joa del 18 de agosto de 2026 para reforzar
la privacidad antes de incorporar Gmail.

Esta línea base no autoriza abrir OAuth, conectar Gmail, solicitar credenciales,
usar datos reales ni publicar la aplicación.

## Principios exigibles

- Minimización: pedir, recibir, conservar y mostrar sólo lo necesario.
- Denegación por defecto: toda operación, origen, campo o permiso no enumerado
  queda prohibido.
- Separación: credenciales, metadatos, inferencias y decisiones viven en
  fronteras distintas.
- Defensa en profundidad: un fallo de interfaz no puede habilitar red o escritura.
- Redacción: tokens, códigos OAuth, PKCE, URLs personales, errores remotos crudos
  y direcciones no aparecen en logs, excepciones ni representaciones.
- Borrado verificable: desconectar, revocar, olvidar credenciales y borrar el
  índice son operaciones separadas y auditables.

## Barrera para OAuth y Gmail reales

Antes de una conexión real deben cumplirse conjuntamente:

1. autorización específica de Joa en contexto;
2. credencial de aplicación de escritorio fuera de Git;
3. PKCE S256, `state` de un solo uso, callback exacto en `127.0.0.1` y puerto
   efímero conforme a `GMAIL_SESSION_V1.md`;
4. evaluación e implementación de DPoP para el refresh token o una decisión
   explícita de MAIN y Joa que acepte el riesgo residual documentado;
5. prueba de DPAPI en un proceso Windows normal con perfil de usuario;
6. ubicación por usuario y ACL restrictiva para el índice;
7. cifrado autenticado de los metadatos sensibles con una clave protegida por
   DPAPI, o una alternativa revisada y aprobada;
8. política de retención, respaldo y borrado verificable;
9. adaptador productivo de red separado y auditado;
10. confirmación de los requisitos de verificación de Google aplicables al
    permiso restringido `gmail.metadata`.

SQLite D1 no satisface por sí sola los puntos 6 a 8: su esquema sintético actual
no cifra el índice. Hasta resolverlos, ningún dato real puede persistirse.

## Red y permisos

- Único scope Gmail permitido: el constante de `session_model.py` para
  `gmail.metadata`.
- Único origen Gmail futuro: `https://gmail.googleapis.com`, validado sin
  credenciales embebidas, puerto alternativo ni host por sufijo.
- Inventario: sólo método HTTP `GET` y endpoints enumerados por
  `gmail_readonly_policy.py`.
- Prohibidos métodos de escritura, SDKs no auditados, redirecciones abiertas,
  proxies heredados implícitamente y envío de datos a terceros.
- OAuth usa únicamente los hosts definidos por `GMAIL_SESSION_V1.md`; Gmail API
  no recibe cookies ni credenciales distintas del token de acceso en memoria.

## Datos y registros

- No se solicitan cuerpos, HTML, `snippet`, estructura MIME, adjuntos,
  destinatarios ni encabezados arbitrarios.
- Los valores se validan y acotan antes de persistir.
- Enviados, Borradores y Papelera se descartan antes de escribir el índice.
- Spam se releva por separado y nunca habilita una acción automática.
- No se registra contenido de encabezados, IDs remotos, direcciones, asuntos,
  URLs de baja, tokens ni respuestas externas completas.
- Los errores persistibles son códigos cerrados sin payload remoto.

## Límites operativos

- Páginas de hasta 500 IDs.
- Cinco intentos como máximo para fallos transitorios, con demora exponencial,
  jitter inyectable y techo de 32 segundos.
- Cancelación comprobada antes de cada petición y antes de cada persistencia.
- Una página y su checkpoint se guardan en una misma transacción.
- Un `historyId` vencido produce `requires_full_resync`; nunca se improvisa una
  continuidad parcial.
- Toda identidad de cuenta se compara con la sesión antes de leer o persistir.

## Evidencia técnica vigente

La línea base se fundamenta en las recomendaciones vigentes de Google para
OAuth de aplicaciones instaladas, scopes Gmail, sincronización y reintentos;
en RFC 9700 (OAuth 2.0 Security Best Current Practice); y en DPAPI de Windows.
Las referencias directas se mantienen en `GMAIL_READONLY_INVENTORY_V1.md`.
