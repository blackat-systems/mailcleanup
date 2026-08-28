from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias, TypeVar, cast
from uuid import UUID

from fastapi import APIRouter, FastAPI, Path, Request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mailmap import __version__
from mailmap.classification_model import EvidenceOrigin, EvidenceStrength
from mailmap.index_model import SyncMode, SyncState
from mailmap.map_composition import MapCompositionResult, compose_map
from mailmap.map_model import MapCompositionError, MapCompositionErrorCode
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SYNTHETIC_MAP_FIXTURE_VERSION,
)
from mailmap.model import Confianza, Intencion, Proteccion, Rubro, Suscripcion
from mailmap.policy_model import (
    EffectiveFlowSelector,
    EffectiveSourceKind,
    EffectiveSourceSelector,
    LabelSelector,
    MergeSources,
    MessageSelector,
    PartitionAnchor,
    PartitionGroup,
    PartitionSource,
    PolicyBindingStatus,
    PolicyError,
    PolicyErrorCode,
    PolicyEvidenceCode,
    PolicyProtectionReason,
    ProtectTarget,
    SenderSelector,
    SetFlowDisplayName,
    SetFlowIntention,
    SetSourceDisplayName,
    SetSourceRubro,
    UndoPolicy,
    is_policy_decision_command,
)
from mailmap.repository import (
    MapInputSnapshot,
    MapPolicyWriteResult,
    MapRepositoryError,
    MapRepositoryErrorCode,
    Repository,
)

CONTRACT_VERSION = 1
API_PREFIX = "/api/v2"
LOCAL_HOST = "127.0.0.1:8765"
LOCAL_ORIGIN = "http://127.0.0.1:8765"
MAX_JSON_BYTES = 64 * 1024

_MAP_REVISION_PATTERN = r"^map-v1-[0-9a-f]{64}$"
_SOURCE_ID_PATTERN = r"^effective-source-v1-[0-9a-f]{24}$"
_FLOW_ID_PATTERN = r"^effective-flow-v1-[0-9a-f]{24}$"
_MESSAGE_ID_PATTERN = r"^message-v1-[0-9a-f]{64}$"

SourceId: TypeAlias = Annotated[str, Field(pattern=_SOURCE_ID_PATTERN)]
FlowId: TypeAlias = Annotated[str, Field(pattern=_FLOW_ID_PATTERN)]
MessageId: TypeAlias = Annotated[str, Field(pattern=_MESSAGE_ID_PATTERN)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class _ResponseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        alias_generator=_camel_case,
        populate_by_name=True,
    )


class ClassificationEvidenceResponse(_ResponseModel):
    kind: Literal["classification"]
    code: str
    label: str
    detail: str
    strength: EvidenceStrength
    origin: EvidenceOrigin


class PolicyEvidenceResponse(_ResponseModel):
    kind: Literal["policy"]
    code: PolicyEvidenceCode
    decision_id: str


EvidenceResponse: TypeAlias = Annotated[
    ClassificationEvidenceResponse | PolicyEvidenceResponse,
    Field(discriminator="kind"),
]


class ProtectionResponse(_ResponseModel):
    automatic: Proteccion
    effective: Proteccion
    protected: bool
    review_required: bool
    hard_excluded: bool
    reasons: tuple[PolicyProtectionReason, ...]


class MonthlyVolumeResponse(_ResponseModel):
    month: str
    message_count: int
    total_bytes: int


class SyncStateResponse(_ResponseModel):
    state: SyncState
    mode: SyncMode | None
    processed_count: int
    started_at: datetime | None
    updated_at: datetime | None
    error_code: str | None
    partial: bool


class SyncResponse(SyncStateResponse):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"


class FlowResponse(_ResponseModel):
    id: str
    source_id: str
    automatic_flow_id: str
    automatic_display_name: str
    effective_display_name: str
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    message_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime
    last_seen: datetime
    protection: ProtectionResponse
    automatic_evidence: tuple[ClassificationEvidenceResponse, ...]
    effective_evidence: tuple[EvidenceResponse, ...]
    decision_ids: tuple[str, ...]
    structural_decision_ids: tuple[str, ...]


class SourceResponse(_ResponseModel):
    id: str
    automatic_source_ids: tuple[str, ...]
    automatic_display_name: str
    effective_display_name: str
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_confidence: Confianza
    effective_confidence: Confianza
    message_count: int
    flow_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime
    last_seen: datetime
    senders: tuple[str, ...]
    domains: tuple[str, ...]
    monthly_volume: tuple[MonthlyVolumeResponse, ...]
    protection: ProtectionResponse
    automatic_evidence: tuple[ClassificationEvidenceResponse, ...]
    effective_evidence: tuple[EvidenceResponse, ...]
    decision_ids: tuple[str, ...]
    structural_decision_ids: tuple[str, ...]
    flows: tuple[FlowResponse, ...]


class SummaryResponse(_ResponseModel):
    message_count: int
    source_count: int
    flow_count: int
    protected_message_count: int
    review_required_message_count: int
    hard_excluded_message_count: int
    total_bytes: int
    first_seen: datetime | None
    last_seen: datetime | None


class PolicyReviewBindingResponse(_ResponseModel):
    decision_id: str
    status: PolicyBindingStatus
    current_effective_ids: tuple[str, ...]


class PolicyReviewResponse(_ResponseModel):
    total: int
    bindings: tuple[PolicyReviewBindingResponse, ...]


class MapResponse(_ResponseModel):
    contract_version: Literal[1]
    data_mode: Literal["synthetic"]
    map_revision: str
    policy_revision: int
    sync: SyncStateResponse
    summary: SummaryResponse
    policy_review: PolicyReviewResponse
    sources: tuple[SourceResponse, ...]


class MessageSampleResponse(_ResponseModel):
    id: str
    received_at: datetime
    sender_name: str | None
    sender_address: str | None
    subject: str | None
    label_ids: tuple[str, ...]
    category: str | None
    size_estimate_bytes: int
    source_id: str
    flow_id: str
    automatic_rubro: Rubro
    effective_rubro: Rubro
    automatic_intention: Intencion
    effective_intention: Intencion
    subscription: Suscripcion
    automatic_confidence: Confianza
    effective_confidence: Confianza
    protection: ProtectionResponse


class SourceDetailResponse(SourceResponse):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    recent_messages: tuple[MessageSampleResponse, ...]


class ContextAccountResponse(_ResponseModel):
    state: Literal["synthetic"] = "synthetic"
    display_address: None = None


class CapabilitiesResponse(_ResponseModel):
    map_read: Literal[True] = True
    policy_write: Literal[True] = True
    policy_undo: Literal[True] = True
    gmail_connection: Literal[False] = False
    oauth: Literal[False] = False
    external_network: Literal[False] = False
    real_data: Literal[False] = False
    sync_control: Literal[False] = False
    cleanup_plan: Literal[False] = False
    message_mutation: Literal[False] = False
    unsubscribe: Literal[False] = False
    execute: Literal[False] = False


class ContextResponse(_ResponseModel):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    app_version: str
    account: ContextAccountResponse
    capabilities: CapabilitiesResponse


class ConnectionCapabilitiesResponse(_ResponseModel):
    gmail_connection: Literal[False] = False
    oauth: Literal[False] = False
    external_network: Literal[False] = False
    real_data: Literal[False] = False


class ConnectionResponse(_ResponseModel):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    state: Literal["synthetic"] = "synthetic"
    display_address: None = None
    capabilities: ConnectionCapabilitiesResponse


class IndexResponse(_ResponseModel):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    state: Literal["synthetic_fixture"] = "synthetic_fixture"
    fixture_version: str
    schema_version: int
    message_count: int
    partial: bool
    can_delete: Literal[False] = False


class WriteResponse(_ResponseModel):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    status: Literal["applied"] = "applied"
    replayed: bool
    decision_id: str
    policy_revision: int
    map_revision: str
    binding_status: PolicyBindingStatus | None


class TargetSummaryResponse(_ResponseModel):
    kind: Literal["source", "flow", "message", "sender", "label"]
    observed_effective_id: str | None
    observed_source_ids: tuple[str, ...]
    observed_flow_ids: tuple[str, ...]


class PartitionGroupSummaryResponse(_ResponseModel):
    group_index: int
    anchor_count: int
    anchor_kinds: tuple[Literal["flow", "message", "sender"], ...]
    observed_source_ids: tuple[str, ...]
    observed_flow_ids: tuple[str, ...]


class _HistoryEventBase(_ResponseModel):
    decision_id: str | None
    command_id: str
    revision: int
    occurred_at: datetime
    active: bool
    undoable: bool
    target_decision_id: str | None = None
    supersedes_decision_ids: tuple[str, ...]
    binding_status: PolicyBindingStatus | None
    current_target_ids: tuple[str, ...]


class SourceDisplayNameEventResponse(_HistoryEventBase):
    type: Literal["setSourceDisplayName"]
    source_id: str
    display_name: str


class SourceRubroEventResponse(_HistoryEventBase):
    type: Literal["setSourceRubro"]
    source_id: str
    rubro: Rubro


class FlowDisplayNameEventResponse(_HistoryEventBase):
    type: Literal["setFlowDisplayName"]
    flow_id: str
    display_name: str


class FlowIntentionEventResponse(_HistoryEventBase):
    type: Literal["setFlowIntention"]
    flow_id: str
    intention: Intencion


class MergeSourcesEventResponse(_HistoryEventBase):
    type: Literal["mergeSources"]
    source_ids: tuple[str, ...]


class PartitionSourceEventResponse(_HistoryEventBase):
    type: Literal["partitionSource"]
    source_id: str
    group_count: int
    groups: tuple[PartitionGroupSummaryResponse, ...]


class ProtectTargetEventResponse(_HistoryEventBase):
    type: Literal["protectTarget"]
    target: TargetSummaryResponse


class UndoEventResponse(_HistoryEventBase):
    type: Literal["undoPolicy"]


HistoryEventResponse: TypeAlias = Annotated[
    SourceDisplayNameEventResponse
    | SourceRubroEventResponse
    | FlowDisplayNameEventResponse
    | FlowIntentionEventResponse
    | MergeSourcesEventResponse
    | PartitionSourceEventResponse
    | ProtectTargetEventResponse
    | UndoEventResponse,
    Field(discriminator="type"),
]


class DecisionListResponse(_ResponseModel):
    contract_version: Literal[1] = 1
    data_mode: Literal["synthetic"] = "synthetic"
    policy_revision: int
    events: tuple[HistoryEventResponse, ...]


def _uuid4(value: UUID) -> UUID:
    if value.version != 4:
        raise ValueError("identifier must be UUID v4")
    return value


def _utc(value: datetime) -> datetime:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValueError("datetime must include UTC timezone information")
    if offset.total_seconds() != 0:
        raise ValueError("datetime must use UTC")
    return value.astimezone(UTC)


def _datetime_text(value: object) -> object:
    if not isinstance(value, str):
        raise ValueError("datetime must be encoded as text")
    return value


def _normalized_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > 120:
        raise ValueError("name must contain between 1 and 120 characters")
    return normalized


_CanonicalItem = TypeVar("_CanonicalItem", str, UUID)


def _canonical_unique(
    values: Sequence[_CanonicalItem], *, minimum: int = 0
) -> tuple[_CanonicalItem, ...]:
    if len(values) < minimum:
        raise ValueError("collection is too short")
    keys = tuple(str(value) for value in values)
    if len(set(keys)) != len(keys):
        raise ValueError("collection must not contain duplicates")
    return tuple(value for _key, value in sorted(zip(keys, values, strict=True)))


class _CommandBase(_StrictModel):
    command_id: UUID = Field(alias="commandId")
    occurred_at: datetime = Field(alias="occurredAt")
    expected_map_revision: str = Field(
        alias="expectedMapRevision", pattern=_MAP_REVISION_PATTERN
    )
    expected_policy_revision: int = Field(
        alias="expectedPolicyRevision",
        ge=0,
        strict=True,
    )

    _validate_command_id = field_validator("command_id")(_uuid4)
    _validate_occurred_at_text = field_validator("occurred_at", mode="before")(
        _datetime_text
    )
    _validate_occurred_at = field_validator("occurred_at")(_utc)


class _DecisionBase(_CommandBase):
    decision_id: UUID = Field(alias="decisionId")
    supersedes_decision_ids: tuple[UUID, ...] = Field(
        default=(), alias="supersedesDecisionIds", max_length=100
    )

    _validate_decision_id = field_validator("decision_id")(_uuid4)

    @field_validator("supersedes_decision_ids")
    @classmethod
    def _validate_supersedes(cls, values: tuple[UUID, ...]) -> tuple[UUID, ...]:
        for value in values:
            _uuid4(value)
        return _canonical_unique(values)

    @model_validator(mode="after")
    def _reject_self_supersession(self) -> _DecisionBase:
        if self.decision_id in self.supersedes_decision_ids:
            raise ValueError("a decision cannot supersede itself")
        return self


class SetSourceDisplayNameRequest(_DecisionBase):
    type: Literal["setSourceDisplayName"]
    source_id: SourceId = Field(alias="sourceId")
    display_name: str = Field(alias="displayName")

    _validate_display_name = field_validator("display_name")(_normalized_name)


class SetSourceRubroRequest(_DecisionBase):
    type: Literal["setSourceRubro"]
    source_id: SourceId = Field(alias="sourceId")
    rubro: Rubro


class SetFlowDisplayNameRequest(_DecisionBase):
    type: Literal["setFlowDisplayName"]
    flow_id: FlowId = Field(alias="flowId")
    display_name: str = Field(alias="displayName")

    _validate_display_name = field_validator("display_name")(_normalized_name)


class SetFlowIntentionRequest(_DecisionBase):
    type: Literal["setFlowIntention"]
    flow_id: FlowId = Field(alias="flowId")
    intention: Intencion


class MergeSourcesRequest(_DecisionBase):
    type: Literal["mergeSources"]
    source_ids: tuple[SourceId, ...] = Field(
        alias="sourceIds",
        min_length=2,
        max_length=100,
    )

    @field_validator("source_ids")
    @classmethod
    def _validate_source_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_unique(values, minimum=2)


class SourceTargetRequest(_StrictModel):
    kind: Literal["source"]
    source_id: SourceId = Field(alias="sourceId")


class FlowTargetRequest(_StrictModel):
    kind: Literal["flow"]
    flow_id: FlowId = Field(alias="flowId")


class MessageTargetRequest(_StrictModel):
    kind: Literal["message"]
    message_id: MessageId = Field(alias="messageId")


class SenderTargetRequest(_StrictModel):
    kind: Literal["sender"]
    sender_address: str = Field(alias="senderAddress", min_length=3, max_length=320)

    @field_validator("sender_address")
    @classmethod
    def _validate_sender(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized != value or value.count("@") != 1 or any(char.isspace() for char in value):
            raise ValueError("sender address must be canonical")
        local, domain = value.rsplit("@", 1)
        if not local or not domain.endswith(".example"):
            raise ValueError("sender address must be synthetic")
        return value


class LabelTargetRequest(_StrictModel):
    kind: Literal["label"]
    label_id: str = Field(alias="labelId", min_length=1, max_length=128)

    @field_validator("label_id")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        if value != value.strip() or any(char.isspace() for char in value):
            raise ValueError("label identifier must be opaque")
        return value


TargetRequest: TypeAlias = Annotated[
    SourceTargetRequest
    | FlowTargetRequest
    | MessageTargetRequest
    | SenderTargetRequest
    | LabelTargetRequest,
    Field(discriminator="kind"),
]


class FlowPartitionAnchorRequest(_StrictModel):
    kind: Literal["flow"]
    flow_id: FlowId = Field(alias="flowId")


class MessagePartitionAnchorRequest(_StrictModel):
    kind: Literal["message"]
    message_id: MessageId = Field(alias="messageId")


class SenderPartitionAnchorRequest(_StrictModel):
    kind: Literal["sender"]
    sender_address: str = Field(alias="senderAddress", min_length=3, max_length=320)

    @field_validator("sender_address")
    @classmethod
    def _validate_sender_address(cls, value: str) -> str:
        return SenderTargetRequest._validate_sender(value)


PartitionAnchorRequest: TypeAlias = Annotated[
    FlowPartitionAnchorRequest
    | MessagePartitionAnchorRequest
    | SenderPartitionAnchorRequest,
    Field(discriminator="kind"),
]


class PartitionGroupRequest(_StrictModel):
    anchors: tuple[PartitionAnchorRequest, ...] = Field(min_length=1, max_length=1000)

    @field_validator("anchors")
    @classmethod
    def _validate_anchors(
        cls, values: tuple[PartitionAnchorRequest, ...]
    ) -> tuple[PartitionAnchorRequest, ...]:
        canonical = tuple(
            sorted(
                values,
                key=lambda item: json.dumps(
                    item.model_dump(by_alias=True, mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        )
        keys = tuple(
            json.dumps(
                item.model_dump(by_alias=True, mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for item in canonical
        )
        if len(set(keys)) != len(keys):
            raise ValueError("partition anchors must be unique")
        return canonical


class PartitionSourceRequest(_DecisionBase):
    type: Literal["partitionSource"]
    source_id: SourceId = Field(alias="sourceId")
    groups: tuple[PartitionGroupRequest, ...] = Field(min_length=2, max_length=100)

    @field_validator("groups")
    @classmethod
    def _validate_groups(
        cls, values: tuple[PartitionGroupRequest, ...]
    ) -> tuple[PartitionGroupRequest, ...]:
        if sum(len(group.anchors) for group in values) > 1000:
            raise ValueError("partition has too many anchors")
        keys = tuple(
            json.dumps(
                group.model_dump(by_alias=True, mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for group in values
        )
        if len(set(keys)) != len(keys):
            raise ValueError("partition groups must be unique")
        return tuple(group for _key, group in sorted(zip(keys, values, strict=True)))


class ProtectTargetRequest(_DecisionBase):
    type: Literal["protectTarget"]
    target: TargetRequest


DecisionRequest: TypeAlias = Annotated[
    SetSourceDisplayNameRequest
    | SetSourceRubroRequest
    | SetFlowDisplayNameRequest
    | SetFlowIntentionRequest
    | MergeSourcesRequest
    | PartitionSourceRequest
    | ProtectTargetRequest,
    Field(discriminator="type"),
]


class UndoRequest(_CommandBase):
    pass


_DECISION_ADAPTER: TypeAdapter[DecisionRequest] = TypeAdapter(DecisionRequest)
_UNDO_ADAPTER: TypeAdapter[UndoRequest] = TypeAdapter(UndoRequest)


class ErrorBody(_StrictModel):
    code: str
    message: str


class ErrorResponse(_StrictModel):
    error: ErrorBody


_ERRORS: dict[str, tuple[int, str]] = {
    "invalid_request": (400, "El pedido no es válido."),
    "invalid_local_origin": (403, "El pedido no proviene de la aplicación local."),
    "source_not_found": (404, "La fuente no existe en la vista actual."),
    "decision_not_found": (404, "La decisión no existe o ya no está activa."),
    "map_revision_conflict": (409, "La vista cambió. Actualizá el mapa antes de reintentar."),
    "policy_revision_conflict": (409, "Las decisiones cambiaron. Actualizá antes de reintentar."),
    "command_id_conflict": (409, "El identificador del comando ya fue utilizado."),
    "policy_conflict": (409, "La decisión entra en conflicto con otra decisión vigente."),
    "invalid_transition": (409, "La transición solicitada no está permitida."),
    "payload_too_large": (413, "El pedido supera el tamaño permitido."),
    "json_required": (415, "Se requiere un cuerpo JSON."),
    "target_not_found": (422, "El objetivo no existe en la vista actual."),
    "unsupported_target": (422, "El objetivo no está permitido."),
    "map_unavailable": (503, "El mapa sintético no está disponible."),
    "account_unavailable": (503, "La cuenta sintética no está disponible."),
    "internal_error": (500, "No se pudo completar la operación."),
}


def _error_response(code: str) -> JSONResponse:
    status_code, message = _ERRORS.get(code, _ERRORS["internal_error"])
    payload = ErrorResponse(error=ErrorBody(code=code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(by_alias=True, mode="json"),
        headers={"Cache-Control": "no-store"},
    )


def _header_values(scope: Scope, name: bytes) -> tuple[str, ...]:
    return tuple(
        value.decode("latin-1")
        for key, value in scope.get("headers", ())
        if key.lower() == name
    )


class MapV2SecurityMiddleware:
    """Deny-by-default HTTP boundary for the local Mapa Total API."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        if scope["type"] != "http" or not path.startswith(API_PREFIX):
            await self._app(scope, receive, send)
            return

        if _header_values(scope, b"host") != (LOCAL_HOST,):
            await _error_response("invalid_local_origin")(scope, receive, send)
            return
        if scope.get("query_string", b""):
            await _error_response("invalid_request")(scope, receive, send)
            return
        if path == API_PREFIX:
            await _error_response("invalid_request")(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        if method not in {"GET", "POST"}:
            await _error_response("invalid_request")(scope, receive, send)
            return
        origins = _header_values(scope, b"origin")
        if method == "POST":
            if origins != (LOCAL_ORIGIN,):
                await _error_response("invalid_local_origin")(scope, receive, send)
                return
            content_types = _header_values(scope, b"content-type")
            if len(content_types) != 1 or not _is_json_content_type(content_types[0]):
                await _error_response("json_required")(scope, receive, send)
                return
            if _header_values(scope, b"cookie"):
                await _error_response("invalid_local_origin")(scope, receive, send)
                return
            lengths = _header_values(scope, b"content-length")
            if len(lengths) > 1:
                await _error_response("invalid_request")(scope, receive, send)
                return
            if lengths:
                try:
                    content_length = int(lengths[0])
                    if content_length < 0:
                        await _error_response("invalid_request")(scope, receive, send)
                        return
                    if content_length > MAX_JSON_BYTES:
                        await _error_response("payload_too_large")(scope, receive, send)
                        return
                except ValueError:
                    await _error_response("invalid_request")(scope, receive, send)
                    return
            body = await _bounded_body(receive)
            if body is None:
                await _error_response("payload_too_large")(scope, receive, send)
                return
            receive = _replay_body(body)
        elif origins and origins != (LOCAL_ORIGIN,):
            await _error_response("invalid_local_origin")(scope, receive, send)
            return

        async def guarded_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                for header in (
                    "access-control-allow-origin",
                    "access-control-allow-credentials",
                ):
                    if header in headers:
                        del headers[header]
            await send(message)

        await self._app(scope, receive, guarded_send)


def _is_json_content_type(value: str) -> bool:
    media_type, separator, parameters = value.casefold().partition(";")
    if media_type.strip() != "application/json":
        return False
    if not separator:
        return True
    return parameters.strip() in {"charset=utf-8", "charset=\"utf-8\""}


async def _bounded_body(receive: Receive) -> bytes | None:
    chunks: list[bytes] = []
    size = 0
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            return b""
        chunk = message.get("body", b"")
        size += len(chunk)
        if size > MAX_JSON_BYTES:
            return None
        chunks.append(chunk)
        more = bool(message.get("more_body", False))
    return b"".join(chunks)


def _replay_body(body: bytes) -> Receive:
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


class _DuplicateJsonKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateJsonKey
        value[key] = item
    return value


async def _validated_body(request: Request, adapter: TypeAdapter[Any]) -> Any:
    try:
        raw = await request.body()
        decoded = raw.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=_unique_object)
        if not isinstance(value, dict):
            raise ValueError
        return adapter.validate_python(value)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJsonKey,
        ValidationError,
        ValueError,
        RecursionError,
    ):
        raise _InvalidPublicRequest from None


class _InvalidPublicRequest(RuntimeError):
    __slots__ = ()


def _canonical_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(by_alias=True, mode="python"))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    raise TypeError("unsupported canonical value")


def _request_fingerprint(method: str, path: str, body: BaseModel) -> str:
    payload = {
        "body": _canonical_value(body),
        "contractVersion": CONTRACT_VERSION,
        "method": method.upper(),
        "path": path,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _PublicApiError(RuntimeError):
    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _json_model(value: BaseModel, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=value.model_dump(by_alias=True, mode="json"),
    )


def _current_map(repository: Repository) -> tuple[MapInputSnapshot, MapCompositionResult]:
    snapshot = repository.map_input_snapshot(SYNTHETIC_MAP_ACCOUNT_KEY)
    return snapshot, compose_map(snapshot)


def _translate_error(error: BaseException) -> JSONResponse:
    if isinstance(error, _PublicApiError):
        return _error_response(error.code)
    if isinstance(error, MapRepositoryError):
        repository_codes: dict[MapRepositoryErrorCode, str] = {
            MapRepositoryErrorCode.INVALID_INPUT: "invalid_request",
            MapRepositoryErrorCode.MAP_REVISION_CONFLICT: "map_revision_conflict",
            MapRepositoryErrorCode.COMMAND_ID_CONFLICT: "command_id_conflict",
            MapRepositoryErrorCode.MAP_UNAVAILABLE: "map_unavailable",
            MapRepositoryErrorCode.RECEIPT_CORRUPT: "internal_error",
        }
        return _error_response(repository_codes.get(error.code, "internal_error"))
    if isinstance(error, PolicyError):
        policy_codes: dict[PolicyErrorCode, str] = {
            PolicyErrorCode.INVALID_INPUT: "invalid_request",
            PolicyErrorCode.MIXED_ACCOUNTS: "invalid_request",
            PolicyErrorCode.UNSUPPORTED_TARGET: "unsupported_target",
            PolicyErrorCode.TARGET_NOT_FOUND: "target_not_found",
            PolicyErrorCode.REVISION_CONFLICT: "policy_revision_conflict",
            PolicyErrorCode.COMMAND_ID_CONFLICT: "command_id_conflict",
            PolicyErrorCode.POLICY_CONFLICT: "policy_conflict",
            PolicyErrorCode.INVALID_TRANSITION: "invalid_transition",
            PolicyErrorCode.UNKNOWN_POLICY_VERSION: "internal_error",
        }
        return _error_response(policy_codes.get(error.code, "internal_error"))
    if isinstance(error, MapCompositionError):
        if error.code is MapCompositionErrorCode.MAP_UNAVAILABLE:
            return _error_response("map_unavailable")
        return _error_response("internal_error")
    return _error_response("internal_error")


def _map_response(composition: MapCompositionResult) -> MapResponse:
    return MapResponse.model_validate(composition.projection)


def _source_detail_response(
    composition: MapCompositionResult, source_id: str
) -> SourceDetailResponse:
    detail = composition.source_detail(source_id)
    if detail is None:
        raise _PublicApiError("source_not_found")
    source = SourceResponse.model_validate(detail.source).model_dump(mode="python")
    source["recent_messages"] = tuple(
        MessageSampleResponse.model_validate(message) for message in detail.recent_messages
    )
    return SourceDetailResponse.model_validate(source)


def _required_source(
    composition: MapCompositionResult, source_id: str
) -> EffectiveSourceSelector:
    selector = composition.resolve_source(source_id)
    if selector is None:
        raise _PublicApiError("target_not_found")
    return selector


def _required_automatic_source(
    composition: MapCompositionResult, source_id: str
) -> EffectiveSourceSelector:
    selector = _required_source(composition, source_id)
    if selector.kind is not EffectiveSourceKind.AUTOMATIC:
        raise _PublicApiError("unsupported_target")
    return selector


def _required_flow(
    composition: MapCompositionResult, flow_id: str
) -> EffectiveFlowSelector:
    selector = composition.resolve_flow(flow_id)
    if selector is None:
        raise _PublicApiError("target_not_found")
    return selector


def _partition_anchor(
    composition: MapCompositionResult,
    source_id: str,
    anchor: PartitionAnchorRequest,
) -> PartitionAnchor:
    result: PartitionAnchor | None
    if isinstance(anchor, FlowPartitionAnchorRequest):
        result = composition.partition_anchor_for_source_flow(source_id, anchor.flow_id)
    elif isinstance(anchor, MessagePartitionAnchorRequest):
        result = composition.partition_anchor_for_source_message(
            source_id, anchor.message_id
        )
    else:
        result = composition.partition_anchor_for_source_sender(
            source_id, anchor.sender_address
        )
    if result is None:
        raise _PublicApiError("target_not_found")
    return result


def _target_selector(
    composition: MapCompositionResult,
    target: TargetRequest,
) -> (
    EffectiveSourceSelector
    | EffectiveFlowSelector
    | MessageSelector
    | SenderSelector
    | LabelSelector
):
    if isinstance(target, SourceTargetRequest):
        return _required_source(composition, target.source_id)
    if isinstance(target, FlowTargetRequest):
        return _required_flow(composition, target.flow_id)
    if isinstance(target, MessageTargetRequest):
        selector: (
            MessageSelector | SenderSelector | LabelSelector | None
        ) = composition.resolve_message(target.message_id)
    elif isinstance(target, SenderTargetRequest):
        selector = composition.resolve_sender(target.sender_address)
    else:
        selector = composition.resolve_label(target.label_id)
    if selector is None:
        raise _PublicApiError("target_not_found")
    return selector


def _policy_command(
    request: DecisionRequest,
    composition: MapCompositionResult,
) -> (
    SetSourceDisplayName
    | SetSourceRubro
    | SetFlowDisplayName
    | SetFlowIntention
    | MergeSources
    | PartitionSource
    | ProtectTarget
):
    command_id = str(request.command_id)
    account_key = SYNTHETIC_MAP_ACCOUNT_KEY
    occurred_at = request.occurred_at
    expected_revision = request.expected_policy_revision
    decision_id = str(request.decision_id)
    supersedes_decision_ids = tuple(
        str(value) for value in request.supersedes_decision_ids
    )
    if isinstance(request, SetSourceDisplayNameRequest):
        return SetSourceDisplayName(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            selector=_required_source(composition, request.source_id),
            display_name=request.display_name,
        )
    if isinstance(request, SetSourceRubroRequest):
        return SetSourceRubro(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            selector=_required_source(composition, request.source_id),
            rubro=request.rubro,
        )
    if isinstance(request, SetFlowDisplayNameRequest):
        return SetFlowDisplayName(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            selector=_required_flow(composition, request.flow_id),
            display_name=request.display_name,
        )
    if isinstance(request, SetFlowIntentionRequest):
        return SetFlowIntention(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            selector=_required_flow(composition, request.flow_id),
            intention=request.intention,
        )
    if isinstance(request, MergeSourcesRequest):
        selectors = tuple(
            sorted(
                (
                    _required_automatic_source(composition, source_id)
                    for source_id in request.source_ids
                ),
                key=lambda item: item.canonical_key,
            )
        )
        return MergeSources(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            source_selectors=selectors,
        )
    if isinstance(request, PartitionSourceRequest):
        source_selector = _required_automatic_source(
            composition,
            request.source_id,
        )
        groups = tuple(
            PartitionGroup(
                anchors=tuple(
                    sorted(
                        (
                            _partition_anchor(composition, request.source_id, anchor)
                            for anchor in group.anchors
                        ),
                        key=lambda item: item.canonical_key,
                    )
                )
            )
            for group in request.groups
        )
        return PartitionSource(
            command_id=command_id,
            account_key=account_key,
            occurred_at=occurred_at,
            expected_revision=expected_revision,
            decision_id=decision_id,
            supersedes_decision_ids=supersedes_decision_ids,
            source_selector=source_selector,
            groups=tuple(sorted(groups, key=lambda item: item.canonical_key)),
        )
    return ProtectTarget(
        command_id=command_id,
        account_key=account_key,
        occurred_at=occurred_at,
        expected_revision=expected_revision,
        decision_id=decision_id,
        supersedes_decision_ids=supersedes_decision_ids,
        selector=_target_selector(composition, request.target),
    )


def _binding_status(
    composition: MapCompositionResult, decision_id: str
) -> PolicyBindingStatus | None:
    binding = next(
        (
            item
            for item in composition.effective.bindings
            if item.decision_id == decision_id
        ),
        None,
    )
    return binding.status if binding is not None else None


def _decision_id(result: MapPolicyWriteResult) -> str:
    command = result.event.command
    if isinstance(command, UndoPolicy):
        return command.target_decision_id
    if is_policy_decision_command(command):
        return command.decision_id
    raise _PublicApiError("internal_error")


def _write_response(
    repository: Repository, result: MapPolicyWriteResult
) -> WriteResponse:
    _snapshot, composition = _current_map(repository)
    decision_id = _decision_id(result)
    return WriteResponse(
        replayed=result.replayed,
        decision_id=decision_id,
        policy_revision=composition.projection.policy_revision,
        map_revision=composition.projection.map_revision,
        binding_status=_binding_status(composition, decision_id),
    )


def _decision_list(composition: MapCompositionResult) -> DecisionListResponse:
    return DecisionListResponse.model_validate(composition.decision_history())


def install_map_api(app: FastAPI, repository: Repository) -> None:
    """Mount the synthetic C5 surface without changing the frozen v1 routes."""

    router = APIRouter(prefix=API_PREFIX)

    @router.get("/context", response_model=ContextResponse)
    def context() -> Response:
        try:
            _current_map(repository)
            return _json_model(
                ContextResponse(
                    app_version=__version__,
                    account=ContextAccountResponse(),
                    capabilities=CapabilitiesResponse(),
                )
            )
        except Exception as error:
            return _translate_error(error)

    @router.get("/connection", response_model=ConnectionResponse)
    def connection() -> Response:
        try:
            _current_map(repository)
            return _json_model(
                ConnectionResponse(capabilities=ConnectionCapabilitiesResponse())
            )
        except Exception as error:
            return _translate_error(error)

    @router.get("/sync", response_model=SyncResponse)
    def sync() -> Response:
        try:
            _snapshot, composition = _current_map(repository)
            return _json_model(SyncResponse.model_validate(composition.projection.sync))
        except Exception as error:
            return _translate_error(error)

    @router.get("/index", response_model=IndexResponse)
    def index() -> Response:
        try:
            snapshot, composition = _current_map(repository)
            if snapshot.fixture_version is None:
                raise _PublicApiError("map_unavailable")
            return _json_model(
                IndexResponse(
                    fixture_version=snapshot.fixture_version,
                    schema_version=repository.schema_version(),
                    message_count=len(snapshot.records),
                    partial=composition.projection.sync.partial,
                )
            )
        except Exception as error:
            return _translate_error(error)

    @router.get("/map", response_model=MapResponse)
    def map_projection() -> Response:
        try:
            _snapshot, composition = _current_map(repository)
            return _json_model(_map_response(composition))
        except Exception as error:
            return _translate_error(error)

    @router.get("/map/sources/{sourceId}", response_model=SourceDetailResponse)
    def source_detail(source_id: Annotated[str, Path(alias="sourceId")]) -> Response:
        try:
            _snapshot, composition = _current_map(repository)
            return _json_model(_source_detail_response(composition, source_id))
        except Exception as error:
            return _translate_error(error)

    @router.get("/decisions", response_model=DecisionListResponse)
    def decisions() -> Response:
        try:
            _snapshot, composition = _current_map(repository)
            return _json_model(_decision_list(composition))
        except Exception as error:
            return _translate_error(error)

    @router.post(
        "/decisions",
        response_model=WriteResponse,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": _DECISION_ADAPTER.json_schema(by_alias=True)
                    }
                },
            }
        },
    )
    async def record_decision(request: Request) -> Response:
        try:
            body = cast(
                DecisionRequest,
                await _validated_body(request, _DECISION_ADAPTER),
            )
            fingerprint = _request_fingerprint("POST", f"{API_PREFIX}/decisions", body)
            replay = repository.map_policy_replay(
                SYNTHETIC_MAP_ACCOUNT_KEY,
                str(body.command_id),
                request_fingerprint=fingerprint,
            )
            if replay is not None:
                return _json_model(_write_response(repository, replay))

            snapshot, composition = _current_map(repository)
            if body.expected_map_revision != composition.projection.map_revision:
                raise _PublicApiError("map_revision_conflict")
            if body.expected_policy_revision != snapshot.policy_revision:
                raise _PublicApiError("policy_revision_conflict")
            command = _policy_command(body, composition)
            prepared = composition.prepare_decision(command)
            result = repository.record_map_policy(
                prepared,
                expected_input_revision=snapshot.input_revision,
                request_fingerprint=fingerprint,
                required_fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
            )
            return _json_model(_write_response(repository, result))
        except _InvalidPublicRequest:
            return _error_response("invalid_request")
        except Exception as error:
            return _translate_error(error)

    @router.post(
        "/decisions/{decisionId}/undo",
        response_model=WriteResponse,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": _UNDO_ADAPTER.json_schema(by_alias=True)
                    }
                },
            }
        },
    )
    async def undo_decision(
        decision_id: Annotated[str, Path(alias="decisionId")],
        request: Request,
    ) -> Response:
        try:
            try:
                target = _uuid4(UUID(decision_id))
            except (ValueError, AttributeError):
                raise _InvalidPublicRequest from None
            body = cast(UndoRequest, await _validated_body(request, _UNDO_ADAPTER))
            path = f"{API_PREFIX}/decisions/{target}/undo"
            fingerprint = _request_fingerprint("POST", path, body)
            replay = repository.map_policy_replay(
                SYNTHETIC_MAP_ACCOUNT_KEY,
                str(body.command_id),
                request_fingerprint=fingerprint,
            )
            if replay is not None:
                return _json_model(_write_response(repository, replay))

            snapshot, composition = _current_map(repository)
            if body.expected_map_revision != composition.projection.map_revision:
                raise _PublicApiError("map_revision_conflict")
            if body.expected_policy_revision != snapshot.policy_revision:
                raise _PublicApiError("policy_revision_conflict")
            target_event = next(
                (
                    event
                    for event in composition.decision_history().events
                    if event.decision_id == str(target)
                ),
                None,
            )
            if target_event is None:
                raise _PublicApiError("decision_not_found")
            if not target_event.active:
                raise _PublicApiError("invalid_transition")
            command = UndoPolicy(
                command_id=str(body.command_id),
                account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
                occurred_at=body.occurred_at,
                expected_revision=body.expected_policy_revision,
                target_decision_id=str(target),
            )
            result = repository.undo_map_policy(
                command,
                expected_input_revision=snapshot.input_revision,
                request_fingerprint=fingerprint,
                required_fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
            )
            return _json_model(_write_response(repository, result))
        except _InvalidPublicRequest:
            return _error_response("invalid_request")
        except Exception as error:
            return _translate_error(error)

    @router.api_route(
        "/{unmatched_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        include_in_schema=False,
    )
    def reject_unmatched(unmatched_path: str) -> Response:
        del unmatched_path
        return _error_response("invalid_request")

    app.include_router(router)
    app.add_middleware(MapV2SecurityMiddleware)
