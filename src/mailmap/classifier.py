from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from dataclasses import replace
from email.utils import parseaddr

from mailmap.model import (
    Confianza,
    Evidence,
    Intencion,
    MessageAssessment,
    MetodoBaja,
    Proteccion,
    Recomendacion,
    Rubro,
    Suscripcion,
    SyntheticMessage,
)

SYSTEM_PROTECTED_LABELS = frozenset({"STARRED", "IMPORTANT", "SENT", "DRAFT", "TRASH"})
DEFAULT_USER_PROTECTED_LABELS = frozenset({"Trabajo", "Familia", "Pagos"})
SECURITY_WORDS = ("inicio de sesión", "contraseña", "código de acceso", "seguridad")
DOCUMENT_WORDS = ("factura", "recibo", "comprobante", "resumen de cuenta")


def normalize_email(value: str) -> str:
    """Normaliza una dirección sin inventar equivalencias específicas de proveedor."""

    _name, address = parseaddr(value)
    return address.strip().casefold()


def sender_domain(address: str) -> str:
    normalized = normalize_email(address)
    return normalized.rpartition("@")[2]


def normalize_list_id(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().strip("<>").casefold()
    return cleaned or None


def _slug(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value)
    ascii_value = folded.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")


def _source_identity(message: SyntheticMessage) -> tuple[str, str, bool, Evidence]:
    if message.brand_hint and message.dkim_pass and message.dmarc_pass:
        return (
            f"src-{_slug(message.brand_hint)}",
            message.brand_hint,
            False,
            Evidence(
                code="brand-authenticated",
                label="Identidad autenticada",
                detail=(
                    f"La marca declarada coincide con señales autenticadas de "
                    f"{message.authenticated_domain or sender_domain(message.sender_email)}."
                ),
                strength="fuerte",
            ),
        )

    if message.authenticated_domain and message.dmarc_pass:
        name = message.sender_name or message.authenticated_domain
        return (
            f"domain-{_slug(message.authenticated_domain)}",
            name,
            False,
            Evidence(
                code="domain-authenticated",
                label="Dominio autenticado",
                detail=f"El dominio {message.authenticated_domain} superó autenticación.",
                strength="media",
            ),
        )

    email = normalize_email(message.sender_email)
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:10]
    return (
        f"sender-{digest}",
        message.sender_name or email,
        True,
        Evidence(
            code="sender-isolated",
            label="Remitente aislado por precaución",
            detail="No hay evidencia suficiente para fusionarlo con otra fuente.",
            strength="débil",
        ),
    )


def _intent(message: SyntheticMessage) -> tuple[Intencion, list[Evidence]]:
    subject = message.subject.casefold()
    evidence: list[Evidence] = []

    if not message.dmarc_pass or "SPAM" in message.labels:
        evidence.append(
            Evidence(
                code="authentication-failed",
                label="Autenticación fallida",
                detail=(
                    "La señal de autenticación o la ubicación en Spam exige "
                    "tratarlo como sospechoso."
                ),
                strength="fuerte",
            )
        )
        return Intencion.SOSPECHOSO, evidence

    if message.personal_signal:
        evidence.append(
            Evidence(
                code="personal-language",
                label="Señal de conversación personal",
                detail="El patrón sintético representa una conversación dirigida a una persona.",
                strength="fuerte",
            )
        )
        return Intencion.PERSONAL, evidence

    if any(word in subject for word in SECURITY_WORDS):
        evidence.append(
            Evidence(
                code="security-subject",
                label="Patrón de seguridad",
                detail="El asunto contiene una señal operativa de seguridad.",
                strength="fuerte",
            )
        )
        return Intencion.SEGURIDAD, evidence

    if any(word in subject for word in DOCUMENT_WORDS):
        evidence.append(
            Evidence(
                code="document-subject",
                label="Patrón documental",
                detail="El asunto identifica una factura, recibo o comprobante.",
                strength="fuerte",
            )
        )
        return Intencion.DOCUMENTO, evidence

    if message.flow_hint:
        evidence.append(
            Evidence(
                code="fixture-flow-signal",
                label="Señal de flujo",
                detail=(
                    "Las cabeceras sintéticas y el asunto sostienen la intención "
                    f"{message.flow_hint.value}."
                ),
                strength="media",
            )
        )
        return message.flow_hint, evidence

    category_mapping = {
        "Promociones": Intencion.PROMOCIONAL,
        "Actualizaciones": Intencion.NOTIFICACION,
        "Social": Intencion.NOTIFICACION,
    }
    inferred = category_mapping.get(message.gmail_category, Intencion.DESCONOCIDO)
    evidence.append(
        Evidence(
            code="provider-category",
            label="Categoría del proveedor",
            detail=(
                f"La categoría disponible es {message.gmail_category}; "
                "se usa sólo como indicio."
            ),
            strength="débil",
        )
    )
    return inferred, evidence


def _unsubscribe_method(message: SyntheticMessage) -> MetodoBaja:
    if message.unsubscribe_method == "one_click" and message.dkim_pass and message.dmarc_pass:
        return MetodoBaja.UN_CLIC
    if message.unsubscribe_method == "manual" and message.dmarc_pass:
        return MetodoBaja.MANUAL
    if message.unsubscribe_method:
        return MetodoBaja.SOSPECHOSO
    return MetodoBaja.AUSENTE


def _subscription(
    message: SyntheticMessage,
    intent: Intencion,
    method: MetodoBaja,
) -> Suscripcion:
    if method is MetodoBaja.SOSPECHOSO:
        return Suscripcion.POSIBLE_INCUMPLIMIENTO
    if message.personal_signal:
        return Suscripcion.NO_CORRESPONDE
    if normalize_list_id(message.list_id) and method in {MetodoBaja.UN_CLIC, MetodoBaja.MANUAL}:
        return Suscripcion.CONFIRMADA
    if method in {MetodoBaja.UN_CLIC, MetodoBaja.MANUAL}:
        return Suscripcion.PROBABLE
    if intent in {Intencion.SEGURIDAD, Intencion.DOCUMENTO, Intencion.PERSONAL}:
        return Suscripcion.NO_CORRESPONDE
    return Suscripcion.DESCONOCIDO


def _confidence(message: SyntheticMessage, ambiguous: bool, intent: Intencion) -> Confianza:
    category_conflict = (
        intent in {Intencion.SEGURIDAD, Intencion.DOCUMENTO}
        and message.gmail_category == "Promociones"
    )
    personal_automation_conflict = message.personal_signal and bool(message.list_id)
    brand_auth_conflict = bool(message.brand_hint) and not message.dmarc_pass
    if category_conflict or personal_automation_conflict or brand_auth_conflict:
        return Confianza.CONTRADICTORIA
    if ambiguous:
        return Confianza.BAJA
    if message.dkim_pass and message.dmarc_pass and (message.brand_hint or message.list_id):
        return Confianza.ALTA
    return Confianza.MEDIA


def _protection(
    message: SyntheticMessage,
    intent: Intencion,
    confidence: Confianza,
    user_labels: frozenset[str],
) -> tuple[Proteccion, bool, list[Evidence]]:
    labels = set(message.labels)
    evidence: list[Evidence] = []
    protected_labels = labels & (SYSTEM_PROTECTED_LABELS | user_labels)
    if protected_labels:
        evidence.append(
            Evidence(
                code="protected-label",
                label="Etiqueta protegida",
                detail=f"Se respetan por defecto: {', '.join(sorted(protected_labels))}.",
                strength="fuerte",
            )
        )
        return Proteccion.USUARIO, True, evidence
    if intent is Intencion.SEGURIDAD:
        evidence.append(
            Evidence(
                code="critical-security",
                label="Contenido crítico",
                detail="Los avisos de seguridad quedan fuera de cualquier selección ordinaria.",
                strength="fuerte",
            )
        )
        return Proteccion.CRITICA, True, evidence
    if intent is Intencion.DOCUMENTO:
        evidence.append(
            Evidence(
                code="document-protection",
                label="Documento conservable",
                detail="Los comprobantes requieren revisión y conservación por defecto.",
                strength="fuerte",
            )
        )
        return Proteccion.DOCUMENTAL, True, evidence
    if intent is Intencion.PERSONAL or confidence in {Confianza.BAJA, Confianza.CONTRADICTORIA}:
        evidence.append(
            Evidence(
                code="mandatory-review",
                label="Revisión obligatoria",
                detail="La ambigüedad o contradicción impide incluirlo silenciosamente en un plan.",
                strength="fuerte",
            )
        )
        return Proteccion.REVISION, True, evidence
    return Proteccion.ORDINARIA, False, evidence


def classify_message(
    message: SyntheticMessage,
    *,
    user_protected_labels: frozenset[str] = DEFAULT_USER_PROTECTED_LABELS,
) -> MessageAssessment:
    source_id, source_name, ambiguous, identity_evidence = _source_identity(message)
    intent, intent_evidence = _intent(message)
    method = _unsubscribe_method(message)
    subscription = _subscription(message, intent, method)
    confidence = _confidence(message, ambiguous, intent)
    protection, protected, protection_evidence = _protection(
        message, intent, confidence, user_protected_labels
    )
    evidence: list[Evidence] = [identity_evidence, *intent_evidence, *protection_evidence]

    if message.list_id:
        evidence.append(
            Evidence(
                code="list-id",
                label="Lista identificada",
                detail=f"List-ID normalizado: {normalize_list_id(message.list_id)}.",
                strength="fuerte" if message.dmarc_pass else "débil",
            )
        )
    if method is not MetodoBaja.AUSENTE:
        evidence.append(
            Evidence(
                code="unsubscribe-method",
                label="Método de baja detectado",
                detail=method.value,
                strength="fuerte" if method is MetodoBaja.UN_CLIC else "media",
            )
        )
    if message.failure_state:
        evidence.append(
            Evidence(
                code="partial-ingestion",
                label="Ingesta con incidencia simulada",
                detail=message.failure_state.replace("_", " "),
                strength="media",
            )
        )

    recommendation = Recomendacion.REVISAR
    if protected:
        recommendation = (
            Recomendacion.CONSERVAR
            if protection is not Proteccion.REVISION
            else Recomendacion.REVISAR
        )
    elif intent in {Intencion.SOSPECHOSO, Intencion.PROMOCIONAL}:
        recommendation = Recomendacion.PAPELERA
    elif subscription in {Suscripcion.CONFIRMADA, Suscripcion.PROBABLE}:
        recommendation = Recomendacion.ARCHIVAR

    return MessageAssessment(
        message=message,
        source_id=source_id,
        source_name=source_name,
        source_ambiguous=ambiguous,
        rubro=message.rubro_hint or Rubro.DESCONOCIDO,
        intencion=intent,
        suscripcion=subscription,
        proteccion=protection,
        confianza=confidence,
        metodo_baja=method,
        recomendacion=recommendation,
        protected=protected,
        evidence=tuple(evidence),
    )


def assess_messages(messages: tuple[SyntheticMessage, ...]) -> tuple[MessageAssessment, ...]:
    assessed = tuple(classify_message(message) for message in messages)
    by_thread: dict[str, list[MessageAssessment]] = defaultdict(list)
    for item in assessed:
        by_thread[item.message.thread_id].append(item)

    mixed_threads = {
        thread_id
        for thread_id, items in by_thread.items()
        if any(item.protected for item in items) and any(not item.protected for item in items)
    }
    return tuple(
        item.with_thread_review()
        if item.message.thread_id in mixed_threads and not item.protected
        else item
        for item in assessed
    )


def with_user_labels(assessment: MessageAssessment, labels: tuple[str, ...]) -> MessageAssessment:
    """Helper de prueba para revalidar un plan frente a un cambio de etiquetas."""

    updated = replace(assessment.message, labels=labels, revision=assessment.message.revision + 1)
    return classify_message(updated)
