from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any

MODEL_VERSION = 1
DATASET_VERSION = "hito0-v1"


class Rubro(StrEnum):
    MEDIOS = "Medios y contenido"
    SOFTWARE = "Software y servicios digitales"
    COMERCIO = "Comercio y compras"
    FINANZAS = "Finanzas"
    TRABAJO = "Trabajo y educación"
    SALUD = "Salud y gobierno"
    VIAJES = "Viajes y entretenimiento"
    SOCIAL = "Social y comunidades"
    DOMESTICOS = "Servicios domésticos"
    PERSONAL = "Personal"
    DESCONOCIDO = "Desconocido"


class Intencion(StrEnum):
    SEGURIDAD = "Seguridad"
    DOCUMENTO = "Documento o comprobante"
    OPERATIVO = "Operativo o soporte"
    NOTIFICACION = "Notificación"
    EDITORIAL = "Informativo o editorial"
    PROMOCIONAL = "Promocional o venta"
    PERSONAL = "Comunicación personal"
    SOSPECHOSO = "Sospechoso"
    DESCONOCIDO = "Desconocido"


class Suscripcion(StrEnum):
    CONFIRMADA = "Confirmada"
    PROBABLE = "Probable"
    NO_CORRESPONDE = "No corresponde"
    BAJA_SOLICITADA = "Baja solicitada"
    POSIBLE_INCUMPLIMIENTO = "Posible incumplimiento"
    DESCONOCIDO = "Desconocido"


class Proteccion(StrEnum):
    CRITICA = "Crítica"
    DOCUMENTAL = "Documental"
    USUARIO = "Elegida por el usuario"
    ORDINARIA = "Ordinaria"
    REVISION = "Revisión obligatoria"


class Confianza(StrEnum):
    ALTA = "Alta"
    MEDIA = "Media"
    BAJA = "Baja"
    CONTRADICTORIA = "Contradictoria"


class MetodoBaja(StrEnum):
    UN_CLIC = "Un clic autenticado"
    MANUAL = "Manual"
    AUSENTE = "No detectada"
    SOSPECHOSO = "Cabecera no confiable"


class Recomendacion(StrEnum):
    CONSERVAR = "Conservar"
    REVISAR = "Revisar"
    PAPELERA = "Candidato a Papelera"
    ARCHIVAR = "Candidato a Archivo"


@dataclass(frozen=True, slots=True)
class Evidence:
    code: str
    label: str
    detail: str
    strength: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "label": self.label,
            "detail": self.detail,
            "strength": self.strength,
        }


@dataclass(frozen=True, slots=True)
class SyntheticMessage:
    id: str
    thread_id: str
    received_at: datetime
    sender_name: str
    sender_email: str
    subject: str
    labels: tuple[str, ...]
    gmail_category: str
    authenticated_domain: str | None
    list_id: str | None
    unsubscribe_method: str | None
    dkim_pass: bool
    dmarc_pass: bool
    brand_hint: str | None
    rubro_hint: Rubro | None
    flow_hint: Intencion | None
    personal_signal: bool = False
    size_bytes: int = 0
    failure_state: str | None = None
    fixture_tags: tuple[str, ...] = ()
    revision: int = 1

    def with_labels(self, labels: tuple[str, ...]) -> SyntheticMessage:
        return replace(self, labels=labels, revision=self.revision + 1)


@dataclass(frozen=True, slots=True)
class MessageAssessment:
    message: SyntheticMessage
    source_id: str
    source_name: str
    source_ambiguous: bool
    rubro: Rubro
    intencion: Intencion
    suscripcion: Suscripcion
    proteccion: Proteccion
    confianza: Confianza
    metodo_baja: MetodoBaja
    recomendacion: Recomendacion
    protected: bool
    evidence: tuple[Evidence, ...]

    def with_thread_review(self) -> MessageAssessment:
        evidence = self.evidence + (
            Evidence(
                code="mixed-thread",
                label="Hilo de protección mixta",
                detail=(
                    "Otro mensaje del mismo hilo está protegido; se exige "
                    "revisión del hilo completo."
                ),
                strength="fuerte",
            ),
        )
        return replace(
            self,
            proteccion=Proteccion.REVISION,
            recomendacion=Recomendacion.REVISAR,
            protected=True,
            evidence=evidence,
        )

    def as_dict(self) -> dict[str, Any]:
        message = self.message
        return {
            "id": message.id,
            "threadId": message.thread_id,
            "receivedAt": message.received_at.isoformat(),
            "senderName": message.sender_name,
            "senderEmail": message.sender_email,
            "subject": message.subject,
            "labels": list(message.labels),
            "gmailCategory": message.gmail_category,
            "sourceId": self.source_id,
            "sourceName": self.source_name,
            "sourceAmbiguous": self.source_ambiguous,
            "rubro": self.rubro.value,
            "intencion": self.intencion.value,
            "suscripcion": self.suscripcion.value,
            "proteccion": self.proteccion.value,
            "confianza": self.confianza.value,
            "metodoBaja": self.metodo_baja.value,
            "recomendacion": self.recomendacion.value,
            "protected": self.protected,
            "sizeBytes": message.size_bytes,
            "failureState": message.failure_state,
            "fixtureTags": list(message.fixture_tags),
            "revision": message.revision,
            "evidence": [item.as_dict() for item in self.evidence],
        }
