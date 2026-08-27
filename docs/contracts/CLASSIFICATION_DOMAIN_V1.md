# Contrato de clasificación de registros normalizados v1

Estado: D4 auditada e integrada. La ampliación pública de identidad fue
autorizada por Joa el 27 de agosto de 2026 y mantiene el alcance exclusivamente
sintético de este contrato.

Autoridad: autorización explícita de Joa del 27 de agosto de 2026, el contrato
del MVP y la planificación durable de D4.

Este contrato no autoriza Gmail, OAuth, red, credenciales, datos reales,
persistencia de clasificaciones, API pública, interfaz ni acciones sobre
mensajes.

## 1. Objetivo

D4 transforma registros normalizados por D3 en un mapa determinista y
explicable de candidatos a fuente y flujo. Debe funcionar sin `brand_hint`,
`rubro_hint`, `flow_hint`, `personal_signal`, `fixture_tags` ni cualquier otra
verdad preparada por los fixtures de Base Segura.

Una clasificación es una inferencia con evidencia, no un hecho ni una
autorización para limpiar.

## 2. Entrada pública

La operación pública es:

```python
classify_indexed_records(
    records: Iterable[IndexedMessageRecord],
) -> ClassificationResult
```

La entrada:

- se materializa y valida completamente antes de clasificar;
- pertenece a una sola `account_key` opaca;
- no contiene dos veces la misma identidad compuesta de mensaje;
- puede llegar en cualquier orden y produce siempre el mismo resultado;
- utiliza únicamente campos cerrados de `IndexedMessageRecord`.

Una entrada vacía devuelve un resultado vacío. Mezclar cuentas, duplicar IDs o
recibir un tipo distinto produce un error controlado sin incluir direcciones,
asuntos, IDs remotos ni encabezados en su texto o representación.

## 3. Salida cerrada

`src/mailmap/classification_model.py` define modelos inmutables, con `slots`,
sin campos arbitrarios:

- `EvidenceStrength`;
- `ClassificationEvidence`;
- `ClassifiedMessage`;
- `ClassifiedSource`;
- `ClassifiedFlow`;
- `ClassificationResult`;
- códigos y error controlado del dominio.

`ClassificationResult` contiene tuplas ordenadas de mensajes, fuentes y flujos.
Cada mensaje conserva la relación con su `provider_message_id`, `source_id` y
`flow_id`. Cada fuente enumera de manera determinista sus remitentes y dominios;
cada flujo pertenece a una única fuente.

Las representaciones y errores deben redactar direcciones, asuntos, IDs,
valores de `List-ID` y cabeceras de baja. Ningún identificador local contiene
esos valores en texto claro.

### 3.1. Descriptores públicos de identidad

La versión 2 de `ClassificationResult` agrega una descripción estructural y
versionada de la identidad que D4 ya utilizaba internamente. No cambia las
agrupaciones, taxonomías, IDs, inferencias ni evidencias de D4.

`SourceIdentityDescriptor`, versión 1, usa exactamente una de estas anclas:

- `senders`: una tupla no vacía, canónica, ordenada y sin duplicados de
  direcciones normalizadas;
- `isolated_message`: ninguna dirección y un único ID remoto de mensaje para
  una fuente que D4 mantuvo aislada por falta de remitente.

`FlowIdentityDescriptor`, versión 1, incluye el descriptor de su fuente, la
intención automática y exactamente una de estas anclas:

- `list_intent`: `List-ID` canónico;
- `sender_intent`: dirección normalizada perteneciente a la fuente;
- `isolated_message`: ID remoto único cuando la contradicción o ausencia de
  remitente obliga a aislar el flujo.

`ClassifiedSource.identity_descriptor` y
`ClassifiedFlow.identity_descriptor` son públicos y cerrados. El resultado
valida que cada descriptor coincida con su entidad, que el descriptor de cada
flujo referencie al de su fuente y que no existan descriptores duplicados.

Los descriptores pueden contener metadatos privados para permitir una futura
reconciliación exacta. Sus representaciones y errores siempre los redactan; no
son anónimos, no se persisten en esta ampliación y no autorizan datos reales.

## 4. Taxonomías vigentes

D4 reutiliza exactamente los enums actuales de `src/mailmap/model.py`:

- `Rubro`;
- `Intencion`;
- `Suscripcion`;
- `Confianza`.

Para D4 prevalecen las categorías compactas de `docs/CONTRATO_MVP.md`. Las
categorías más amplias de `docs/ESPECIFICACION_FUNCIONAL.md` siguen siendo una
visión futura y no se incorporan silenciosamente.

D4 no decide `Proteccion`, `Recomendacion` ni ejecución. D5 consumirá la salida
clasificada y aplicará las reglas de protección. Hasta entonces una confianza
baja o contradictoria sólo marca revisión y nunca habilita acciones.

## 5. Identidad conservadora de fuente

La clasificación comienza separando remitentes. Sólo puede fusionar varias
direcciones cuando existe evidencia positiva y coherente.

Reglas mínimas:

1. La misma dirección normalizada produce una identidad estable dentro de la
   misma cuenta.
2. Dos direcciones pueden compartir fuente únicamente si tienen nombre visible
   normalizado coherente, autenticación DKIM y DMARC aprobada y dominio
   autenticado coherente con el dominio remitente.
3. Compartir infraestructura o dominio autenticado sin identidad visible
   coherente no alcanza para fusionar.
4. Un cambio de dominio no se fusiona por parecido de nombre solamente.
5. Autenticación fallida, dirección ausente o evidencia contradictoria mantiene
   candidatos separados.
6. La baja confianza nunca fusiona direcciones diferentes.
7. La ausencia de evidencia produce una fuente desconocida estable y aislada,
   no una organización inventada.

Los IDs locales son hashes deterministas con namespace y versión. Incluyen la
cuenta opaca en la clave canónica para evitar colisiones entre cuentas, pero no
exponen correo, dominio, nombre ni `List-ID`.

## 6. Identidad de flujo

Los flujos se construyen siempre dentro de una fuente ya determinada.

- Un `List-ID` normalizado y coherente es la señal estructural más fuerte.
- La intención forma parte de la identidad del flujo: seguridad, documentos y
  promociones no se agrupan aunque compartan remitente o lista.
- Sin `List-ID`, se usa de forma conservadora remitente normalizado más intención.
- Sin remitente o con contradicción, el flujo permanece aislado.
- Dos `List-ID` distintos no se fusionan por compartir categoría de Gmail.
- El nombre mostrado es una descripción inferida y debe indicar desconocido
  cuando no haya evidencia suficiente.

## 7. Clasificación explicable

La precedencia mínima de intención es:

1. Spam o autenticación fallida: `SOSPECHOSO`.
2. Señales acotadas de seguridad en asunto: `SEGURIDAD`.
3. Señales acotadas documentales en asunto: `DOCUMENTO`.
4. Señales coherentes de lista, baja y categoría: editorial, promocional,
   notificación u operativo según las reglas cerradas del módulo.
5. Sin evidencia suficiente: `DESCONOCIDO`.

No se infiere comunicación personal únicamente porque falten cabeceras de
lista. No se usa el nombre de una marca concreta como verdad codificada.

El rubro puede inferirse sólo mediante reglas genéricas, versionadas y
explicables sobre nombre, dominio, `List-ID` o asunto. Si la evidencia no es
suficiente, el resultado correcto es `Rubro.DESCONOCIDO`.

El estado de suscripción se deriva de evidencia técnica:

- `CONFIRMADA`: `List-ID`, mecanismo de baja coherente y autenticación aprobada;
- `PROBABLE`: señal de lista o baja parcial pero coherente;
- `NO_CORRESPONDE`: seguridad o documento sin señal de lista;
- `POSIBLE_INCUMPLIMIENTO`: cabeceras contradictorias o no confiables;
- `DESCONOCIDO`: evidencia insuficiente.

D4 no envía solicitudes de baja ni afirma que una suscripción fue cancelada.

## 8. Confianza y contradicción

- `ALTA`: al menos dos señales independientes fuertes y coherentes.
- `MEDIA`: una señal fuerte o varias señales débiles coherentes.
- `BAJA`: sólo evidencia débil o identidad aislada.
- `CONTRADICTORIA`: señales materiales incompatibles.

Son contradicciones mínimas:

- dominio autenticado incompatible con el dominio remitente;
- categoría promocional frente a una intención fuerte de seguridad o documento;
- cabeceras de lista o baja junto con autenticación fallida;
- miembros que una agrupación intentaría unir con identidades técnicas
  incompatibles.

La confianza agregada de una fuente o flujo nunca puede ser mejor que la peor
confianza material de sus miembros.

## 9. Evidencia

Toda inferencia conserva al menos una `ClassificationEvidence` con:

- código cerrado y estable;
- etiqueta comprensible;
- detalle redactado;
- fuerza `strong`, `medium` o `weak`;
- campo de procedencia enumerado, nunca un diccionario arbitrario.

La evidencia explica la señal utilizada, no reproduce el asunto, la dirección,
el ID remoto ni la URL completa. El orden es determinista y no se duplican
códigos equivalentes dentro del mismo resultado.

## 10. Pureza, privacidad y límites

D4 es una función local y pura:

- no persiste;
- no lee SQLite directamente;
- no usa reloj, aleatoriedad ni estado global mutable;
- no importa red, Gmail, OAuth, navegador, SDKs ni IA externa;
- no abre archivos ni variables de entorno;
- no usa cuerpos, HTML, snippet, MIME, adjuntos, destinatarios ni encabezados
  distintos de los ya normalizados por D3;
- no registra ni imprime datos.

No se agregan dependencias. No se modifican API, servicio, frontend, fixtures,
repositorio, sesión, inventario ni planes.

## 11. Corpus sintético obligatorio

Las pruebas específicas construyen `IndexedMessageRecord` sintéticos `.example`
y cubren como mínimo:

1. misma dirección estable en entradas repetidas;
2. varias direcciones coherentes de una misma fuente;
3. infraestructura compartida por fuentes distintas;
4. dos marcas distintas bajo un mismo proveedor técnico;
5. cambio de dominio sin evidencia suficiente, conservado separado;
6. una fuente con seguridad, documento y promoción como flujos distintos;
7. `List-ID` distintos como flujos distintos;
8. baja confianza con remitentes separados;
9. contradicción que no se presenta como certeza;
10. Spam y autenticación fallida;
11. registro sin remitente, asunto ni señales suficientes;
12. orden de entrada diferente con salida idéntica;
13. aislamiento de cuentas y rechazo de entrada mezclada;
14. ausencia completa de hints sintéticos y campos prohibidos;
15. representaciones y errores redactados.

## 12. Criterio histórico de entrega e integración

La entrega especialista original de D4 estuvo lista para auditoría cuando:

1. implementa la operación y modelos cerrados del contrato;
2. todas las agrupaciones e inferencias conservan evidencia;
3. los desconocidos y contradicciones permanecen conservadores;
4. no depende de ayudas de Base Segura;
5. Base Segura continúa pasando sin cambiar su comportamiento;
6. las pruebas específicas, globales, Ruff, mypy y la barrera de seguridad
   aprueban;
7. el diff contiene exclusivamente los cuatro archivos autorizados;
8. no existen red, Gmail, OAuth, credenciales, datos reales ni artefactos.

Ese alcance especialista contenía cuatro archivos y no se integraba por sí
solo. MAIN auditó, corrigió e integró esa entrega. La ampliación pública de
identidad fue un cambio posterior de columna vertebral realizado por MAIN sobre
modelo, dominio, pruebas y documentación. Todo cambio futuro debe conservar las
mismas puertas: diff completo, batería global, privacidad y decisión explícita
de integración.
