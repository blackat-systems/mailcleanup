from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from mailmap.classification_model import (
    ClassificationError,
    ClassificationErrorCode,
    ClassificationEvidence,
    ClassificationResult,
    ClassifiedFlow,
    ClassifiedMessage,
    ClassifiedSource,
    EvidenceCode,
    EvidenceOrigin,
    EvidenceStrength,
    FlowAnchorKind,
    FlowIdentityDescriptor,
    SourceAnchorKind,
    SourceIdentityDescriptor,
)
from mailmap.index_model import IndexedMessageRecord
from mailmap.model import Confianza, Intencion, Rubro, Suscripcion

_ID_NAMESPACE = "mailcleanup.classification.v1"
_ADDRESS = re.compile(
    r"^[^@\s<>]+@(?P<domain>[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)$",
    re.IGNORECASE,
)
_DOMAIN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$", re.IGNORECASE)
_BRACKETED_LIST_ID = re.compile(r"(?:[^<>]*\s+)?<(?P<value>[^<>]+)>")
_LIST_ID_COMPONENT = re.compile(
    r"^(?:[a-z0-9]|[a-z0-9][a-z0-9_+-]*[a-z0-9])$", re.IGNORECASE
)
_UNSUBSCRIBE_URI = re.compile(
    r"(?:"
    r"https://[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?(?::[0-9]{1,5})?"
    r"(?:[/?#][^\s<>,]*)?"
    r"|mailto:[^@\s<>,]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?"
    r"(?:\?[^\s<>,]*)?"
    r")",
    re.IGNORECASE,
)
_UNSUBSCRIBE_HEADER = re.compile(
    rf"^(?:{_UNSUBSCRIBE_URI.pattern}|<{_UNSUBSCRIBE_URI.pattern}>"
    rf"(?:\s*,\s*<{_UNSUBSCRIBE_URI.pattern}>)*?)$",
    re.IGNORECASE,
)

_SECURITY_TERMS = (
    "actividad inusual",
    "alerta de seguridad",
    "cambio de contrasena",
    "codigo de acceso",
    "codigo de seguridad",
    "inicio de sesion",
    "restablecer contrasena",
    "verificacion de cuenta",
)
_DOCUMENT_TERMS = (
    "comprobante",
    "estado de cuenta",
    "factura",
    "recibo",
    "resumen de cuenta",
)
_OPERATIONAL_TERMS = (
    "incidencia",
    "mantenimiento programado",
    "mesa de ayuda",
    "soporte tecnico",
    "ticket de soporte",
)
_NOTIFICATION_TERMS = (
    "actualizacion de estado",
    "aviso de actividad",
    "confirmacion de estado",
    "notificacion",
)
_EDITORIAL_TERMS = (
    "boletin",
    "edicion semanal",
    "newsletter",
    "resumen semanal",
)
_PROMOTIONAL_TERMS = (
    "cupon",
    "descuento",
    "oferta",
    "promocion",
    "rebaja",
)
_PROMOTIONAL_CATEGORIES = frozenset({"promociones", "promotions"})
_NOTIFICATION_CATEGORIES = frozenset(
    {"actualizaciones", "forums", "social", "updates"}
)
_RUBRO_RULES = (
    (Rubro.MEDIOS, ("boletin", "editorial", "media", "newsletter", "noticias", "revista")),
    (Rubro.SOFTWARE, ("aplicacion", "cloud", "digital", "plataforma", "software")),
    (Rubro.COMERCIO, ("comercio", "compra", "market", "shop", "store", "tienda")),
    (Rubro.FINANZAS, ("banco", "bank", "finanzas", "tarjeta")),
    (Rubro.TRABAJO, ("curso", "educacion", "empleo", "escuela", "trabajo", "universidad")),
    (Rubro.SALUD, ("clinica", "gobierno", "government", "hospital", "salud")),
    (Rubro.VIAJES, ("entretenimiento", "evento", "hotel", "travel", "viaje", "vuelo")),
    (Rubro.SOCIAL, ("comunidad", "foro", "social")),
    (Rubro.DOMESTICOS, ("agua", "energia", "gas", "internet", "servicio domestico")),
)
_CONFIDENCE_ORDER = (
    Confianza.ALTA,
    Confianza.MEDIA,
    Confianza.BAJA,
    Confianza.CONTRADICTORIA,
)
_SOURCE_EVIDENCE_CODES = frozenset(
    {
        EvidenceCode.SOURCE_AUTHENTICATED,
        EvidenceCode.SOURCE_MERGED,
        EvidenceCode.SOURCE_SENDER_ISOLATED,
        EvidenceCode.SOURCE_SENDER_MISSING,
        EvidenceCode.SOURCE_IDENTITY_UNRESOLVED,
        EvidenceCode.AUTH_DKIM_PASSED,
        EvidenceCode.AUTH_DMARC_PASSED,
        EvidenceCode.AUTH_FAILED,
        EvidenceCode.AUTH_INCOMPLETE,
        EvidenceCode.AUTH_DOMAIN_COHERENT,
        EvidenceCode.AUTH_DOMAIN_CONFLICT,
        EvidenceCode.RUBRO_GENERIC_SIGNAL,
        EvidenceCode.RUBRO_UNKNOWN,
        EvidenceCode.CONFLICT_CATEGORY_INTENT,
        EvidenceCode.CONFLICT_GROUP_AUTHENTICATION,
    }
)


@dataclass(frozen=True, slots=True)
class _NormalizedRecord:
    record: IndexedMessageRecord = field(repr=False)
    sender_name: str | None = field(repr=False)
    sender_name_key: str | None = field(repr=False)
    sender_address: str | None = field(repr=False)
    sender_domain: str | None = field(repr=False)
    authenticated_domain: str | None = field(repr=False)
    subject_key: str = field(repr=False)
    category_key: str = field(repr=False)
    labels: frozenset[str] = field(repr=False)
    list_id: str | None = field(repr=False)
    list_header_present: bool
    list_untrusted: bool
    unsubscribe_present: bool
    unsubscribe_untrusted: bool
    one_click_post: bool
    unsubscribe_conflict: bool
    auth_passed: bool
    auth_failed: bool
    domain_coherent: bool
    domain_conflict: bool


@dataclass(frozen=True, slots=True)
class _SourceGroup:
    source_id: str
    identity_descriptor: SourceIdentityDescriptor = field(repr=False)
    identity_key: str = field(repr=False)
    records: tuple[_NormalizedRecord, ...] = field(repr=False)
    mergeable_name: str | None = field(repr=False)
    identity_evidence: tuple[ClassificationEvidence, ...]


@dataclass(frozen=True, slots=True)
class _MessageDraft:
    normalized: _NormalizedRecord = field(repr=False)
    source_id: str
    source_identity_descriptor: SourceIdentityDescriptor = field(repr=False)
    rubro: Rubro
    intencion: Intencion
    suscripcion: Suscripcion
    confianza: Confianza
    evidence: tuple[ClassificationEvidence, ...]


@dataclass(frozen=True, slots=True)
class _FlowGroup:
    flow_id: str
    source_id: str
    identity_descriptor: FlowIdentityDescriptor = field(repr=False)
    drafts: tuple[_MessageDraft, ...] = field(repr=False)
    identity_evidence: ClassificationEvidence


def _evidence(
    code: EvidenceCode,
    label: str,
    detail: str,
    strength: EvidenceStrength,
    origin: EvidenceOrigin,
) -> ClassificationEvidence:
    return ClassificationEvidence(
        code=code,
        label=label,
        detail=detail,
        strength=strength,
        origin=origin,
    )


def _strength_rank(value: EvidenceStrength) -> int:
    if value is EvidenceStrength.STRONG:
        return 0
    if value is EvidenceStrength.MEDIUM:
        return 1
    return 2


def _ordered_evidence(
    values: Iterable[ClassificationEvidence],
) -> tuple[ClassificationEvidence, ...]:
    selected: dict[EvidenceCode, ClassificationEvidence] = {}
    for value in values:
        current = selected.get(value.code)
        if current is None or (
            _strength_rank(value.strength), value.origin.value, value.label, value.detail
        ) < (
            _strength_rank(current.strength),
            current.origin.value,
            current.label,
            current.detail,
        ):
            selected[value.code] = value
    return tuple(selected[code] for code in sorted(selected, key=lambda item: item.value))


def _fold_text(value: str | None) -> str:
    if value is None:
        return ""
    folded = unicodedata.normalize("NFKD", value)
    ascii_value = folded.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value).split())


def _normalized_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _normalize_sender_address(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    normalized = value.strip().casefold()
    match = _ADDRESS.fullmatch(normalized)
    if match is None:
        raise ClassificationError(ClassificationErrorCode.INVALID_RECORD)
    return normalized, match.group("domain").casefold().rstrip(".")


def _normalize_domain(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold().rstrip(".")
    if not normalized or _DOMAIN.fullmatch(normalized) is None:
        raise ClassificationError(ClassificationErrorCode.INVALID_RECORD)
    return normalized


def _normalize_list_id(value: str | None) -> tuple[str | None, bool, bool]:
    if value is None or not value.strip():
        return None, False, False
    raw = value.strip()
    if "<" in raw or ">" in raw:
        match = _BRACKETED_LIST_ID.fullmatch(raw)
        if match is None:
            return None, True, True
        candidate = match.group("value")
    else:
        candidate = raw
    canonical = candidate.strip().casefold()
    components = canonical.split(".")
    untrusted = (
        not canonical
        or any(character.isspace() for character in canonical)
        or "<" in canonical
        or ">" in canonical
        or len(components) < 2
        or any(
            _LIST_ID_COMPONENT.fullmatch(component) is None
            for component in components
        )
    )
    return (None if untrusted else canonical), True, untrusted


def _normalize_unsubscribe(value: str | None) -> tuple[bool, bool, bool]:
    if value is None or not value.strip():
        return False, False, False
    raw = value.strip()
    coherent = _UNSUBSCRIBE_HEADER.fullmatch(raw) is not None
    has_https = coherent and re.search(r"(?:^|<)https://", raw, re.IGNORECASE) is not None
    return coherent, not coherent, has_https


def _domains_coherent(sender_domain: str | None, authenticated_domain: str | None) -> bool:
    if sender_domain is None or authenticated_domain is None:
        return False
    return (
        sender_domain == authenticated_domain
        or sender_domain.endswith(f".{authenticated_domain}")
        or authenticated_domain.endswith(f".{sender_domain}")
    )


def _normalize_record(record: IndexedMessageRecord) -> _NormalizedRecord:
    sender_address, sender_domain = _normalize_sender_address(record.sender_address)
    authenticated_domain = _normalize_domain(record.authenticated_domain)
    sender_name = _normalized_optional_text(record.sender_name)
    sender_name_key = _fold_text(sender_name) or None
    list_id, list_header_present, list_untrusted = _normalize_list_id(record.list_id)
    (
        unsubscribe_present,
        unsubscribe_untrusted,
        unsubscribe_has_https,
    ) = _normalize_unsubscribe(record.list_unsubscribe)
    raw_post = " ".join((record.list_unsubscribe_post or "").casefold().split())
    one_click_post = (
        raw_post == "list-unsubscribe=one-click" and unsubscribe_has_https
    )
    unsubscribe_conflict = bool(raw_post) and (
        not unsubscribe_present or not one_click_post
    )
    auth_passed = record.dkim_result == "pass" and record.dmarc_result == "pass"
    auth_failed = record.dkim_result == "fail" or record.dmarc_result == "fail"
    domain_coherent = _domains_coherent(sender_domain, authenticated_domain)
    domain_conflict = (
        sender_domain is not None
        and authenticated_domain is not None
        and not domain_coherent
    )
    return _NormalizedRecord(
        record=record,
        sender_name=sender_name,
        sender_name_key=sender_name_key,
        sender_address=sender_address,
        sender_domain=sender_domain,
        authenticated_domain=authenticated_domain,
        subject_key=_fold_text(record.subject),
        category_key=_fold_text(record.category),
        labels=frozenset(label.casefold() for label in record.label_ids),
        list_id=list_id,
        list_header_present=list_header_present,
        list_untrusted=list_untrusted,
        unsubscribe_present=unsubscribe_present,
        unsubscribe_untrusted=unsubscribe_untrusted,
        one_click_post=one_click_post,
        unsubscribe_conflict=unsubscribe_conflict,
        auth_passed=auth_passed,
        auth_failed=auth_failed,
        domain_coherent=domain_coherent,
        domain_conflict=domain_conflict,
    )


def _validated_records(
    records: Iterable[IndexedMessageRecord],
) -> tuple[_NormalizedRecord, ...]:
    try:
        materialized = tuple(records)
    except Exception:
        raise ClassificationError(ClassificationErrorCode.INVALID_INPUT) from None
    validated: list[IndexedMessageRecord] = []
    for record in materialized:
        if not isinstance(record, IndexedMessageRecord):
            raise ClassificationError(ClassificationErrorCode.INVALID_RECORD)
        validated.append(record)
    if not validated:
        return ()

    account_keys = {record.account_key for record in validated}
    if len(account_keys) != 1:
        raise ClassificationError(ClassificationErrorCode.MIXED_ACCOUNTS)
    identities = [
        (record.account_key, record.provider_message_id) for record in validated
    ]
    if len(set(identities)) != len(identities):
        raise ClassificationError(
            ClassificationErrorCode.DUPLICATE_MESSAGE_IDENTITY
        )

    try:
        normalized = tuple(_normalize_record(record) for record in validated)
    except ClassificationError:
        raise
    except (AttributeError, TypeError, ValueError):
        raise ClassificationError(ClassificationErrorCode.INVALID_RECORD) from None
    return tuple(
        sorted(normalized, key=lambda item: item.record.provider_message_id)
    )


def _stable_id(kind: str, account_key: str, *parts: str) -> str:
    canonical = "\x1f".join((_ID_NAMESPACE, kind, account_key, *parts))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{kind}-v1-{digest}"


def _mergeable_name(records: tuple[_NormalizedRecord, ...]) -> str | None:
    names = {record.sender_name_key for record in records}
    if None in names or len(names) != 1:
        return None
    if any(
        record.sender_address is None
        or not record.auth_passed
        or not record.domain_coherent
        or record.auth_failed
        or record.domain_conflict
        for record in records
    ):
        return None
    return next(iter(names))


def _source_identity_evidence(
    records: tuple[_NormalizedRecord, ...], mergeable_name: str | None
) -> tuple[ClassificationEvidence, ...]:
    addresses = {record.sender_address for record in records if record.sender_address}
    evidence: list[ClassificationEvidence] = []
    if not addresses:
        evidence.append(
            _evidence(
                EvidenceCode.SOURCE_SENDER_MISSING,
                "Remitente ausente",
                "La fuente queda desconocida y aislada porque falta un remitente normalizado.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.SENDER,
            )
        )
    elif mergeable_name is not None:
        evidence.append(
            _evidence(
                EvidenceCode.SOURCE_AUTHENTICATED,
                "Identidad técnica coherente",
                "Nombre visible, DKIM, DMARC y dominio autenticado son coherentes.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
        if len(addresses) > 1:
            evidence.append(
                _evidence(
                    EvidenceCode.SOURCE_MERGED,
                    "Remitentes unidos conservadoramente",
                    "Varias direcciones comparten identidad visible y evidencia técnica positiva.",
                    EvidenceStrength.STRONG,
                    EvidenceOrigin.AGGREGATION,
                )
            )
    else:
        evidence.append(
            _evidence(
                EvidenceCode.SOURCE_SENDER_ISOLATED,
                "Remitente aislado",
                "La dirección se mantiene separada hasta reunir evidencia positiva suficiente.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.SENDER,
            )
        )
        if any(record.sender_name_key is None for record in records):
            evidence.append(
                _evidence(
                    EvidenceCode.SOURCE_IDENTITY_UNRESOLVED,
                    "Identidad no resuelta",
                    "La evidencia visible no alcanza para presentar una organización conocida.",
                    EvidenceStrength.WEAK,
                    EvidenceOrigin.SENDER,
                )
            )
    return _ordered_evidence(evidence)


def _source_groups(
    records: tuple[_NormalizedRecord, ...], account_key: str
) -> tuple[_SourceGroup, ...]:
    candidates: dict[str, list[_NormalizedRecord]] = defaultdict(list)
    for record in records:
        if record.sender_address is None:
            candidate_key = f"missing\x1f{record.record.provider_message_id}"
        else:
            candidate_key = f"sender\x1f{record.sender_address}"
        candidates[candidate_key].append(record)

    buckets: dict[str, list[_NormalizedRecord]] = defaultdict(list)
    bucket_names: dict[str, str | None] = {}
    for candidate_key in sorted(candidates):
        candidate_records = tuple(
            sorted(
                candidates[candidate_key],
                key=lambda item: item.record.provider_message_id,
            )
        )
        name_key = _mergeable_name(candidate_records)
        sender_domains = {record.sender_domain for record in candidate_records}
        mergeable_domain = (
            next(iter(sender_domains))
            if name_key is not None
            and len(sender_domains) == 1
            and None not in sender_domains
            else None
        )
        identity_key = (
            f"authenticated-name-domain\x1f{name_key}\x1f{mergeable_domain}"
            if name_key is not None and mergeable_domain is not None
            else f"isolated\x1f{candidate_key}"
        )
        buckets[identity_key].extend(candidate_records)
        bucket_names[identity_key] = name_key

    groups: list[_SourceGroup] = []
    for identity_key in sorted(buckets):
        grouped_records = tuple(
            sorted(
                buckets[identity_key],
                key=lambda item: item.record.provider_message_id,
            )
        )
        mergeable_name = bucket_names[identity_key]
        addresses = tuple(
            sorted(
                {
                    record.sender_address
                    for record in grouped_records
                    if record.sender_address is not None
                }
            )
        )
        stable_identity = (
            f"sender-anchor\x1f{addresses[0]}"
            if addresses
            else f"missing\x1f{grouped_records[0].record.provider_message_id}"
        )
        identity_descriptor = (
            SourceIdentityDescriptor(
                kind=SourceAnchorKind.SENDERS,
                sender_addresses=addresses,
                isolated_message_id=None,
            )
            if addresses
            else SourceIdentityDescriptor(
                kind=SourceAnchorKind.ISOLATED_MESSAGE,
                sender_addresses=(),
                isolated_message_id=grouped_records[0].record.provider_message_id,
            )
        )
        groups.append(
            _SourceGroup(
                source_id=_stable_id("source", account_key, stable_identity),
                identity_descriptor=identity_descriptor,
                identity_key=identity_key,
                records=grouped_records,
                mergeable_name=mergeable_name,
                identity_evidence=_source_identity_evidence(
                    grouped_records, mergeable_name
                ),
            )
        )
    return tuple(sorted(groups, key=lambda item: item.source_id))


def _authentication_evidence(
    record: _NormalizedRecord,
) -> tuple[ClassificationEvidence, ...]:
    values: list[ClassificationEvidence] = []
    if record.record.dkim_result == "pass":
        values.append(
            _evidence(
                EvidenceCode.AUTH_DKIM_PASSED,
                "DKIM aprobado",
                "La señal DKIM normalizada informa aprobación.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    if record.record.dmarc_result == "pass":
        values.append(
            _evidence(
                EvidenceCode.AUTH_DMARC_PASSED,
                "DMARC aprobado",
                "La señal DMARC normalizada informa aprobación.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    if record.auth_failed:
        values.append(
            _evidence(
                EvidenceCode.AUTH_FAILED,
                "Autenticación fallida",
                "Al menos una señal de autenticación normalizada informa fallo.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    elif not record.auth_passed:
        values.append(
            _evidence(
                EvidenceCode.AUTH_INCOMPLETE,
                "Autenticación incompleta",
                "Las señales disponibles no confirman conjuntamente DKIM y DMARC.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    if record.domain_coherent:
        values.append(
            _evidence(
                EvidenceCode.AUTH_DOMAIN_COHERENT,
                "Dominio técnico coherente",
                "El dominio autenticado es coherente con el dominio remitente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    elif record.domain_conflict:
        values.append(
            _evidence(
                EvidenceCode.AUTH_DOMAIN_CONFLICT,
                "Dominio técnico incompatible",
                "El dominio autenticado no es coherente con el dominio remitente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AUTHENTICATION,
            )
        )
    return _ordered_evidence(values)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    padded = f" {text} "
    return any(f" {term} " in padded for term in terms)


def _infer_rubro(
    records: tuple[_NormalizedRecord, ...],
) -> tuple[Rubro, ClassificationEvidence]:
    searchable = " ".join(
        part
        for record in records
        for part in (
            record.sender_name_key or "",
            _fold_text(record.sender_domain),
            _fold_text(record.authenticated_domain),
            _fold_text(record.list_id),
            record.subject_key,
        )
        if part
    )
    matches = {
        rubro
        for rubro, terms in _RUBRO_RULES
        if _contains_any(searchable, terms)
    }
    if len(matches) == 1:
        return (
            next(iter(matches)),
            _evidence(
                EvidenceCode.RUBRO_GENERIC_SIGNAL,
                "Rubro inferido por regla genérica",
                "Términos genéricos coherentes sostienen el rubro sin usar una marca concreta.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.RECORD,
            ),
        )
    return (
        Rubro.DESCONOCIDO,
        _evidence(
            EvidenceCode.RUBRO_UNKNOWN,
            "Rubro desconocido",
            "No hay una señal genérica única y suficiente para inferir el rubro.",
            EvidenceStrength.WEAK,
            EvidenceOrigin.RECORD,
        ),
    )


def _infer_intent(
    record: _NormalizedRecord,
) -> tuple[Intencion, tuple[ClassificationEvidence, ...]]:
    evidence: list[ClassificationEvidence] = []
    if "spam" in record.labels or record.auth_failed:
        if "spam" in record.labels:
            evidence.append(
                _evidence(
                    EvidenceCode.INTENT_SPAM,
                    "Ubicación en Spam",
                    "La etiqueta normalizada de Spam prevalece sobre señales de contenido.",
                    EvidenceStrength.STRONG,
                    EvidenceOrigin.LABEL,
                )
            )
        if record.auth_failed:
            evidence.extend(_authentication_evidence(record))
        return Intencion.SOSPECHOSO, _ordered_evidence(evidence)

    subject_rules = (
        (
            Intencion.SEGURIDAD,
            _SECURITY_TERMS,
            EvidenceCode.INTENT_SECURITY,
            "Señal de seguridad",
            "El asunto contiene una señal genérica acotada de seguridad.",
            EvidenceStrength.STRONG,
        ),
        (
            Intencion.DOCUMENTO,
            _DOCUMENT_TERMS,
            EvidenceCode.INTENT_DOCUMENT,
            "Señal documental",
            "El asunto contiene una señal genérica de documento o comprobante.",
            EvidenceStrength.STRONG,
        ),
        (
            Intencion.OPERATIVO,
            _OPERATIONAL_TERMS,
            EvidenceCode.INTENT_OPERATIONAL,
            "Señal operativa",
            "El asunto contiene una señal genérica de operación o soporte.",
            EvidenceStrength.MEDIUM,
        ),
        (
            Intencion.PROMOCIONAL,
            _PROMOTIONAL_TERMS,
            EvidenceCode.INTENT_PROMOTIONAL,
            "Señal promocional",
            "El asunto contiene una señal genérica de promoción o venta.",
            EvidenceStrength.MEDIUM,
        ),
        (
            Intencion.EDITORIAL,
            _EDITORIAL_TERMS,
            EvidenceCode.INTENT_EDITORIAL,
            "Señal editorial",
            "El asunto contiene una señal genérica editorial o informativa.",
            EvidenceStrength.MEDIUM,
        ),
        (
            Intencion.NOTIFICACION,
            _NOTIFICATION_TERMS,
            EvidenceCode.INTENT_NOTIFICATION,
            "Señal de notificación",
            "El asunto contiene una señal genérica de notificación.",
            EvidenceStrength.MEDIUM,
        ),
    )
    for intent, terms, code, label, detail, strength in subject_rules:
        if _contains_any(record.subject_key, terms):
            return (
                intent,
                (
                    _evidence(
                        code,
                        label,
                        detail,
                        strength,
                        EvidenceOrigin.SUBJECT,
                    ),
                ),
            )

    has_list_signal = record.list_id is not None or record.unsubscribe_present
    if record.category_key in _PROMOTIONAL_CATEGORIES and has_list_signal:
        evidence.append(
            _evidence(
                EvidenceCode.INTENT_PROVIDER_CATEGORY,
                "Categoría del proveedor",
                "La categoría normalizada aporta un indicio débil y no decide por sí sola.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.CATEGORY,
            )
        )
        evidence.append(
            _evidence(
                EvidenceCode.INTENT_PROMOTIONAL,
                "Señales promocionales coherentes",
                "Categoría, lista o baja sostienen conjuntamente una intención promocional.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.AGGREGATION,
            )
        )
        return Intencion.PROMOCIONAL, _ordered_evidence(evidence)
    if record.category_key in _NOTIFICATION_CATEGORIES and has_list_signal:
        evidence.append(
            _evidence(
                EvidenceCode.INTENT_PROVIDER_CATEGORY,
                "Categoría del proveedor",
                "La categoría normalizada aporta un indicio débil y no decide por sí sola.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.CATEGORY,
            )
        )
        evidence.append(
            _evidence(
                EvidenceCode.INTENT_NOTIFICATION,
                "Señales de notificación coherentes",
                "Categoría y estructura de lista sostienen conjuntamente una notificación.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.AGGREGATION,
            )
        )
        return Intencion.NOTIFICACION, _ordered_evidence(evidence)
    if record.category_key:
        evidence.append(
            _evidence(
                EvidenceCode.INTENT_PROVIDER_CATEGORY,
                "Categoría del proveedor",
                "La categoría normalizada se conserva sólo como indicio débil.",
                EvidenceStrength.WEAK,
                EvidenceOrigin.CATEGORY,
            )
        )
    evidence.append(
        _evidence(
            EvidenceCode.INTENT_UNKNOWN,
            "Intención desconocida",
            "Las señales disponibles no alcanzan para inferir una intención.",
            EvidenceStrength.WEAK,
            EvidenceOrigin.RECORD,
        )
    )
    return Intencion.DESCONOCIDO, _ordered_evidence(evidence)


def _list_evidence(record: _NormalizedRecord) -> tuple[ClassificationEvidence, ...]:
    values: list[ClassificationEvidence] = []
    if record.list_id is not None:
        values.append(
            _evidence(
                EvidenceCode.LIST_ID_PRESENT,
                "Lista estructural identificada",
                "Existe un List-ID normalizado; se usa sólo dentro de la fuente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.LIST,
            )
        )
    elif record.list_untrusted:
        values.append(
            _evidence(
                EvidenceCode.LIST_ID_UNTRUSTED,
                "Lista no confiable",
                "La cabecera de lista no pudo normalizarse de forma confiable.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.LIST,
            )
        )
    if record.unsubscribe_present:
        values.append(
            _evidence(
                EvidenceCode.UNSUBSCRIBE_PRESENT,
                "Mecanismo de baja presente",
                "Existe una señal técnica de baja; no se abre ni se ejecuta.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.UNSUBSCRIBE,
            )
        )
    elif record.unsubscribe_untrusted:
        values.append(
            _evidence(
                EvidenceCode.UNSUBSCRIBE_UNTRUSTED,
                "Mecanismo de baja no confiable",
                "La cabecera de baja no contiene una URI HTTPS o mailto coherente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.UNSUBSCRIBE,
            )
        )
    if record.one_click_post and record.unsubscribe_present:
        values.append(
            _evidence(
                EvidenceCode.UNSUBSCRIBE_ONE_CLICK,
                "Cabecera one-click coherente",
                "La forma normalizada de la cabecera one-click es coherente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.UNSUBSCRIBE,
            )
        )
    return _ordered_evidence(values)


def _subscription(
    record: _NormalizedRecord, intent: Intencion
) -> tuple[Suscripcion, ClassificationEvidence]:
    list_signal = record.list_header_present or record.unsubscribe_present
    conflict = (
        record.list_untrusted
        or record.unsubscribe_untrusted
        or record.unsubscribe_conflict
        or (list_signal and record.auth_failed)
    )
    if conflict:
        return (
            Suscripcion.POSIBLE_INCUMPLIMIENTO,
            _evidence(
                EvidenceCode.SUBSCRIPTION_CONFLICT,
                "Señales de suscripción no confiables",
                "Cabeceras de lista o baja contradicen la autenticación o su forma técnica.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AGGREGATION,
            ),
        )
    authentication_approved = record.auth_passed and not record.domain_conflict
    if (
        record.list_id is not None
        and record.unsubscribe_present
        and authentication_approved
    ):
        return (
            Suscripcion.CONFIRMADA,
            _evidence(
                EvidenceCode.SUBSCRIPTION_CONFIRMED,
                "Suscripción confirmada técnicamente",
                "Lista, mecanismo de baja y autenticación resultan coherentes.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AGGREGATION,
            ),
        )
    if record.list_id is not None or record.unsubscribe_present:
        return (
            Suscripcion.PROBABLE,
            _evidence(
                EvidenceCode.SUBSCRIPTION_PROBABLE,
                "Suscripción probable",
                "Existe una señal parcial y coherente de lista o baja.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.AGGREGATION,
            ),
        )
    if intent in {Intencion.SEGURIDAD, Intencion.DOCUMENTO}:
        return (
            Suscripcion.NO_CORRESPONDE,
            _evidence(
                EvidenceCode.SUBSCRIPTION_NOT_APPLICABLE,
                "Suscripción no aplicable",
                "La intención fuerte y la ausencia de lista indican que no corresponde.",
                EvidenceStrength.MEDIUM,
                EvidenceOrigin.AGGREGATION,
            ),
        )
    return (
        Suscripcion.DESCONOCIDO,
        _evidence(
            EvidenceCode.SUBSCRIPTION_UNKNOWN,
            "Suscripción desconocida",
            "No hay evidencia técnica suficiente para afirmar una suscripción.",
            EvidenceStrength.WEAK,
            EvidenceOrigin.AGGREGATION,
        ),
    )


def _category_intent_conflict(record: _NormalizedRecord, intent: Intencion) -> bool:
    return (
        record.category_key in _PROMOTIONAL_CATEGORIES
        and intent in {Intencion.SEGURIDAD, Intencion.DOCUMENTO}
    )


def _message_confidence(
    record: _NormalizedRecord,
    intent: Intencion,
    rubro: Rubro,
    subscription: Suscripcion,
    *,
    identity_isolated: bool,
) -> Confianza:
    list_signal = record.list_header_present or record.unsubscribe_present
    if (
        record.domain_conflict
        or record.list_untrusted
        or record.unsubscribe_untrusted
        or record.unsubscribe_conflict
        or (list_signal and record.auth_failed)
        or _category_intent_conflict(record, intent)
    ):
        return Confianza.CONTRADICTORIA

    if identity_isolated:
        return Confianza.BAJA

    strong_signals = sum(
        (
            record.auth_passed and record.domain_coherent,
            "spam" in record.labels,
            intent in {Intencion.SEGURIDAD, Intencion.DOCUMENTO},
            record.list_id is not None and record.unsubscribe_present,
        )
    )
    medium_signals = sum(
        (
            intent
            in {
                Intencion.OPERATIVO,
                Intencion.NOTIFICACION,
                Intencion.EDITORIAL,
                Intencion.PROMOCIONAL,
            },
            subscription is Suscripcion.PROBABLE,
            record.unsubscribe_present,
        )
    )
    weak_signals = sum(
        (
            record.sender_name_key is not None,
            record.sender_address is not None,
            bool(record.category_key),
        )
    )
    if strong_signals >= 2:
        confidence = Confianza.ALTA
    elif strong_signals == 1 or medium_signals >= 2 or weak_signals >= 2:
        confidence = Confianza.MEDIA
    else:
        confidence = Confianza.BAJA
    if (
        confidence is Confianza.ALTA
        and intent is Intencion.DESCONOCIDO
        and rubro is Rubro.DESCONOCIDO
        and subscription is Suscripcion.DESCONOCIDO
    ):
        return Confianza.MEDIA
    return confidence


def _conflict_evidence(
    record: _NormalizedRecord, intent: Intencion
) -> tuple[ClassificationEvidence, ...]:
    values: list[ClassificationEvidence] = []
    if _category_intent_conflict(record, intent):
        values.append(
            _evidence(
                EvidenceCode.CONFLICT_CATEGORY_INTENT,
                "Categoría e intención contradictorias",
                (
                    "Una categoría promocional contradice una intención fuerte "
                    "y no se trata como certeza."
                ),
                EvidenceStrength.STRONG,
                EvidenceOrigin.AGGREGATION,
            )
        )
    return _ordered_evidence(values)


def _drafts_for_source(
    group: _SourceGroup,
) -> tuple[_MessageDraft, ...]:
    rubro, rubro_evidence = _infer_rubro(group.records)
    drafts: list[_MessageDraft] = []
    for record in group.records:
        intent, intent_evidence = _infer_intent(record)
        subscription, subscription_evidence = _subscription(record, intent)
        confidence = _message_confidence(
            record,
            intent,
            rubro,
            subscription,
            identity_isolated=group.mergeable_name is None,
        )
        evidence = _ordered_evidence(
            (
                *group.identity_evidence,
                *_authentication_evidence(record),
                rubro_evidence,
                *intent_evidence,
                *_list_evidence(record),
                subscription_evidence,
                *_conflict_evidence(record, intent),
            )
        )
        drafts.append(
            _MessageDraft(
                normalized=record,
                source_id=group.source_id,
                source_identity_descriptor=group.identity_descriptor,
                rubro=rubro,
                intencion=intent,
                suscripcion=subscription,
                confianza=confidence,
                evidence=evidence,
            )
        )
    return tuple(
        sorted(drafts, key=lambda item: item.normalized.record.provider_message_id)
    )


def _flow_identity(
    draft: _MessageDraft,
) -> tuple[str, ClassificationEvidence, FlowIdentityDescriptor]:
    record = draft.normalized
    if draft.confianza is Confianza.CONTRADICTORIA or record.sender_address is None:
        return (
            f"isolated\x1f{record.record.provider_message_id}",
            _evidence(
                EvidenceCode.FLOW_ISOLATED,
                "Flujo aislado",
                "La ausencia de remitente o una contradicción impide agrupar el flujo.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AGGREGATION,
            ),
            FlowIdentityDescriptor(
                kind=FlowAnchorKind.ISOLATED_MESSAGE,
                source=draft.source_identity_descriptor,
                list_id=None,
                sender_address=None,
                automatic_intention=draft.intencion,
                isolated_message_id=record.record.provider_message_id,
            ),
        )
    if record.list_id is not None:
        return (
            f"list\x1f{record.list_id}\x1fintent\x1f{draft.intencion.name}",
            _evidence(
                EvidenceCode.FLOW_LIST_ID,
                "Flujo por List-ID e intención",
                "List-ID e intención forman una identidad de flujo dentro de la fuente.",
                EvidenceStrength.STRONG,
                EvidenceOrigin.AGGREGATION,
            ),
            FlowIdentityDescriptor(
                kind=FlowAnchorKind.LIST_INTENT,
                source=draft.source_identity_descriptor,
                list_id=record.list_id,
                sender_address=None,
                automatic_intention=draft.intencion,
                isolated_message_id=None,
            ),
        )
    return (
        (
            f"sender\x1f{record.sender_address}\x1f"
            f"intent\x1f{draft.intencion.name}"
        ),
        _evidence(
            EvidenceCode.FLOW_SENDER_INTENT,
            "Flujo conservador por remitente e intención",
            "Sin List-ID se agrupa sólo por remitente normalizado e intención.",
            EvidenceStrength.MEDIUM,
            EvidenceOrigin.AGGREGATION,
        ),
        FlowIdentityDescriptor(
            kind=FlowAnchorKind.SENDER_INTENT,
            source=draft.source_identity_descriptor,
            list_id=None,
            sender_address=record.sender_address,
            automatic_intention=draft.intencion,
            isolated_message_id=None,
        ),
    )


def _flow_groups(
    drafts: tuple[_MessageDraft, ...], account_key: str
) -> tuple[_FlowGroup, ...]:
    buckets: dict[tuple[str, str], list[_MessageDraft]] = defaultdict(list)
    identity_evidence: dict[tuple[str, str], ClassificationEvidence] = {}
    identity_descriptors: dict[tuple[str, str], FlowIdentityDescriptor] = {}
    for draft in drafts:
        identity_key, evidence, descriptor = _flow_identity(draft)
        key = (draft.source_id, identity_key)
        previous_descriptor = identity_descriptors.get(key)
        if previous_descriptor is not None and previous_descriptor != descriptor:
            raise ClassificationError(ClassificationErrorCode.INVALID_RECORD)
        buckets[key].append(draft)
        identity_evidence[key] = evidence
        identity_descriptors[key] = descriptor
    groups = [
        _FlowGroup(
            flow_id=_stable_id("flow", account_key, source_id, identity_key),
            source_id=source_id,
            identity_descriptor=identity_descriptors[(source_id, identity_key)],
            drafts=tuple(
                sorted(
                    bucket,
                    key=lambda item: item.normalized.record.provider_message_id,
                )
            ),
            identity_evidence=identity_evidence[(source_id, identity_key)],
        )
        for (source_id, identity_key), bucket in buckets.items()
    ]
    return tuple(sorted(groups, key=lambda item: item.flow_id))


def _worst_confidence(values: Iterable[Confianza]) -> Confianza:
    materialized = tuple(values)
    return max(materialized, key=_CONFIDENCE_ORDER.index)


def _group_authentication_conflict(records: Iterable[_NormalizedRecord]) -> bool:
    materialized = tuple(records)
    for field_name in ("dkim_result", "dmarc_result"):
        values = {getattr(record.record, field_name) for record in materialized}
        if "pass" in values and "fail" in values:
            return True
    return False


def _group_conflict_evidence() -> ClassificationEvidence:
    return _evidence(
        EvidenceCode.CONFLICT_GROUP_AUTHENTICATION,
        "Autenticación agregada contradictoria",
        "Los miembros agrupados contienen señales técnicas materiales incompatibles.",
        EvidenceStrength.STRONG,
        EvidenceOrigin.AGGREGATION,
    )


def _aggregate_subscription(values: Iterable[Suscripcion]) -> Suscripcion:
    materialized = frozenset(values)
    if Suscripcion.POSIBLE_INCUMPLIMIENTO in materialized:
        return Suscripcion.POSIBLE_INCUMPLIMIENTO
    if len(materialized) == 1:
        return next(iter(materialized))
    if materialized <= {Suscripcion.CONFIRMADA, Suscripcion.PROBABLE}:
        return Suscripcion.PROBABLE
    return Suscripcion.DESCONOCIDO


def _classified_flows(
    groups: tuple[_FlowGroup, ...],
) -> tuple[ClassifiedFlow, ...]:
    flows: list[ClassifiedFlow] = []
    for group in groups:
        records = tuple(draft.normalized for draft in group.drafts)
        confidence = _worst_confidence(draft.confianza for draft in group.drafts)
        evidence_values: list[ClassificationEvidence] = [group.identity_evidence]
        evidence_values.extend(
            item for draft in group.drafts for item in draft.evidence
        )
        if _group_authentication_conflict(records):
            confidence = Confianza.CONTRADICTORIA
            evidence_values.append(_group_conflict_evidence())
        intentions = {draft.intencion for draft in group.drafts}
        if len(intentions) != 1:
            raise ClassificationError(ClassificationErrorCode.INVALID_RECORD)
        intent = next(iter(intentions))
        flows.append(
            ClassifiedFlow(
                flow_id=group.flow_id,
                source_id=group.source_id,
                identity_descriptor=group.identity_descriptor,
                display_name=(
                    "Flujo desconocido"
                    if intent is Intencion.DESCONOCIDO
                    else intent.value
                ),
                message_ids=tuple(
                    draft.normalized.record.provider_message_id
                    for draft in group.drafts
                ),
                intencion=intent,
                suscripcion=_aggregate_subscription(
                    draft.suscripcion for draft in group.drafts
                ),
                confianza=confidence,
                evidence=_ordered_evidence(evidence_values),
            )
        )
    return tuple(sorted(flows, key=lambda item: item.flow_id))


def _classified_messages(
    groups: tuple[_FlowGroup, ...],
) -> tuple[ClassifiedMessage, ...]:
    messages: list[ClassifiedMessage] = []
    for group in groups:
        for draft in group.drafts:
            messages.append(
                ClassifiedMessage(
                    provider_message_id=draft.normalized.record.provider_message_id,
                    source_id=draft.source_id,
                    flow_id=group.flow_id,
                    rubro=draft.rubro,
                    intencion=draft.intencion,
                    suscripcion=draft.suscripcion,
                    confianza=draft.confianza,
                    evidence=_ordered_evidence(
                        (*draft.evidence, group.identity_evidence)
                    ),
                )
            )
    return tuple(sorted(messages, key=lambda item: item.provider_message_id))


def _display_name(group: _SourceGroup) -> str:
    if group.mergeable_name is None:
        return "Fuente desconocida"
    names = {
        record.sender_name
        for record in group.records
        if record.sender_name is not None
    }
    if not names:
        return "Fuente desconocida"
    return min(names, key=lambda value: (_fold_text(value), value.casefold(), value))


def _classified_sources(
    source_groups: tuple[_SourceGroup, ...],
    drafts: tuple[_MessageDraft, ...],
    flows: tuple[ClassifiedFlow, ...],
) -> tuple[ClassifiedSource, ...]:
    drafts_by_source: dict[str, list[_MessageDraft]] = defaultdict(list)
    for draft in drafts:
        drafts_by_source[draft.source_id].append(draft)
    flows_by_source: dict[str, list[ClassifiedFlow]] = defaultdict(list)
    for flow in flows:
        flows_by_source[flow.source_id].append(flow)

    sources: list[ClassifiedSource] = []
    for group in source_groups:
        source_drafts = tuple(
            sorted(
                drafts_by_source[group.source_id],
                key=lambda item: item.normalized.record.provider_message_id,
            )
        )
        confidence = _worst_confidence(draft.confianza for draft in source_drafts)
        evidence_values: list[ClassificationEvidence] = list(group.identity_evidence)
        evidence_values.extend(
            evidence
            for draft in source_drafts
            for evidence in draft.evidence
            if evidence.code in _SOURCE_EVIDENCE_CODES
        )
        if _group_authentication_conflict(group.records):
            confidence = Confianza.CONTRADICTORIA
            evidence_values.append(_group_conflict_evidence())
        rubros = {draft.rubro for draft in source_drafts}
        rubro = next(iter(rubros)) if len(rubros) == 1 else Rubro.DESCONOCIDO
        source_flows = tuple(
            sorted(flows_by_source[group.source_id], key=lambda item: item.flow_id)
        )
        addresses = tuple(
            sorted(
                {
                    record.sender_address
                    for record in group.records
                    if record.sender_address is not None
                }
            )
        )
        domains = tuple(
            sorted(
                {
                    domain
                    for record in group.records
                    for domain in (
                        record.sender_domain,
                        record.authenticated_domain,
                    )
                    if domain is not None
                }
            )
        )
        sources.append(
            ClassifiedSource(
                source_id=group.source_id,
                identity_descriptor=group.identity_descriptor,
                display_name=_display_name(group),
                sender_addresses=addresses,
                domains=domains,
                message_ids=tuple(
                    draft.normalized.record.provider_message_id
                    for draft in source_drafts
                ),
                flow_ids=tuple(flow.flow_id for flow in source_flows),
                rubro=rubro,
                confianza=confidence,
                evidence=_ordered_evidence(evidence_values),
            )
        )
    return tuple(sorted(sources, key=lambda item: item.source_id))


def classify_indexed_records(
    records: Iterable[IndexedMessageRecord],
) -> ClassificationResult:
    normalized = _validated_records(records)
    if not normalized:
        return ClassificationResult(account_key=None, messages=(), sources=(), flows=())

    account_key = normalized[0].record.account_key
    source_groups = _source_groups(normalized, account_key)
    drafts = tuple(
        draft
        for source_group in source_groups
        for draft in _drafts_for_source(source_group)
    )
    drafts = tuple(
        sorted(drafts, key=lambda item: item.normalized.record.provider_message_id)
    )
    flow_groups = _flow_groups(drafts, account_key)
    messages = _classified_messages(flow_groups)
    flows = _classified_flows(flow_groups)
    sources = _classified_sources(source_groups, drafts, flows)
    return ClassificationResult(
        account_key=account_key,
        messages=messages,
        sources=sources,
        flows=flows,
    )
