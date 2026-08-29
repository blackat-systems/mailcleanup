from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as CivilDate
from threading import Lock
from typing import Annotated, Literal, TypeAlias, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, FastAPI, Request
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from starlette.datastructures import MutableHeaders, QueryParams
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mailmap.cleanup_plan_domain import (
    build_cleanup_target_catalog,
    cleanup_command_fingerprint,
    compose_cleanup_plan_snapshot,
    effective_plan_state,
)
from mailmap.cleanup_plan_model import (
    AllTemporalFilter,
    BeforeDateTemporalFilter,
    CancelCleanupPlanCommand,
    CleanupDisposition,
    CleanupPlanError,
    CleanupPlanEvent,
    CleanupPlanReceipt,
    CleanupPlanSample,
    CleanupPlanState,
    CleanupReadState,
    CleanupSampleKind,
    CleanupTarget,
    CleanupTargetKind,
    CreateCleanupPlanCommand,
    DateRangeTemporalFilter,
    FlowCatalogItem,
    FlowTargetSnapshot,
    LabelCatalogItem,
    OlderThanDaysTemporalFilter,
    PersistedCleanupPlan,
    RevalidateCleanupPlanCommand,
    SenderCatalogItem,
    SenderTargetSnapshot,
    SourceCatalogItem,
    SourceTargetSnapshot,
)
from mailmap.index_model import SyncState
from mailmap.map_synthetic_gate import SYNTHETIC_MAP_ACCOUNT_KEY
from mailmap.repository import CleanupPlanListingItem, CleanupPlanMemberItem, Repository

CONTRACT_VERSION: Literal[1] = 1
API_PREFIX = "/api/v3/study"
LOCAL_HOST = "127.0.0.1:8765"
LOCAL_ORIGIN = "http://127.0.0.1:8765"
TIME_ZONE: Literal["America/Argentina/Cordoba"] = "America/Argentina/Cordoba"
PLAN_VALIDITY_SECONDS: Literal[86_400] = 86_400
MAX_JSON_BYTES = 64 * 1024
MAX_QUERY_BYTES = 4 * 1024
MAX_CURSOR_CHARS = 1_024

_MAP_REVISION_PATTERN = r"^map-v1-[0-9a-f]{64}$"
_SOURCE_ID_PATTERN = r"^effective-source-v1-[0-9a-f]{24}$"
_FLOW_ID_PATTERN = r"^effective-flow-v1-[0-9a-f]{24}$"
_SENDER_ID_PATTERN = r"^sender-v1-[0-9a-f]{64}$"
_LABEL_ID_PATTERN = r"^label-v1-[0-9a-f]{64}$"
_MESSAGE_ID_PATTERN = r"^message-v1-[0-9a-f]{64}$"
_PLAN_ID_PATTERN = (
    r"^cleanup-plan-v1-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_PLAN_ID = re.compile(_PLAN_ID_PATTERN)

MapRevision: TypeAlias = Annotated[str, Field(pattern=_MAP_REVISION_PATTERN)]
SourceId: TypeAlias = Annotated[str, Field(pattern=_SOURCE_ID_PATTERN)]
FlowId: TypeAlias = Annotated[str, Field(pattern=_FLOW_ID_PATTERN)]
SenderId: TypeAlias = Annotated[str, Field(pattern=_SENDER_ID_PATTERN)]
LabelId: TypeAlias = Annotated[str, Field(pattern=_LABEL_ID_PATTERN)]
MessageId: TypeAlias = Annotated[str, Field(pattern=_MESSAGE_ID_PATTERN)]
PlanId: TypeAlias = Annotated[str, Field(pattern=_PLAN_ID_PATTERN)]


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=False)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<redacted>)"

    def __str__(self) -> str:
        return self.__repr__()


class _ResponseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        alias_generator=_camel_case,
        populate_by_name=True,
    )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<redacted>)"

    def __str__(self) -> str:
        return self.__repr__()


class _Envelope(_ResponseModel):
    contract_version: Literal[1] = CONTRACT_VERSION
    data_mode: Literal["synthetic"] = "synthetic"
    can_execute: Literal[False] = False


def _uuid4_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("commandId must be a string")
    try:
        parsed = UUID(value)
    except ValueError:
        raise ValueError("commandId must be a UUID v4") from None
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("commandId must be a canonical UUID v4")
    return value


def _strict_civil_date(value: object) -> CivilDate:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("civil dates must use YYYY-MM-DD")
    try:
        return CivilDate.fromisoformat(value)
    except ValueError:
        raise ValueError("civil date is invalid") from None


class SourceTargetRequest(_StrictModel):
    kind: Literal["source"]
    target_id: SourceId = Field(alias="targetId")


class FlowTargetRequest(_StrictModel):
    kind: Literal["flow"]
    target_id: FlowId = Field(alias="targetId")


class SenderTargetRequest(_StrictModel):
    kind: Literal["sender"]
    target_id: SenderId = Field(alias="targetId")


TargetRequest: TypeAlias = Annotated[
    SourceTargetRequest | FlowTargetRequest | SenderTargetRequest,
    Field(discriminator="kind"),
]


class AllTemporalRequest(_StrictModel):
    kind: Literal["all"]


class BeforeDateTemporalRequest(_StrictModel):
    kind: Literal["beforeDate"]
    date: CivilDate

    @field_validator("date", mode="before")
    @classmethod
    def _closed_date(cls, value: object) -> CivilDate:
        return _strict_civil_date(value)


class DateRangeTemporalRequest(_StrictModel):
    kind: Literal["dateRange"]
    on_or_after_date: CivilDate = Field(alias="onOrAfterDate")
    before_date: CivilDate = Field(alias="beforeDate")

    @field_validator("on_or_after_date", "before_date", mode="before")
    @classmethod
    def _closed_dates(cls, value: object) -> CivilDate:
        return _strict_civil_date(value)

    @model_validator(mode="after")
    def _ordered_range(self) -> DateRangeTemporalRequest:
        if self.on_or_after_date >= self.before_date:
            raise ValueError("date range must be ordered")
        return self


class OlderThanDaysTemporalRequest(_StrictModel):
    kind: Literal["olderThanDays"]
    days: StrictInt = Field(ge=1, le=36_500)


TemporalRequest: TypeAlias = Annotated[
    AllTemporalRequest
    | BeforeDateTemporalRequest
    | DateRangeTemporalRequest
    | OlderThanDaysTemporalRequest,
    Field(discriminator="kind"),
]


_TARGET_KIND_ORDER = {"source": 0, "flow": 1, "sender": 2}


class CreatePlanRequest(_StrictModel):
    command_id: str = Field(alias="commandId")
    expected_map_revision: MapRevision = Field(alias="expectedMapRevision")
    expected_policy_revision: StrictInt = Field(alias="expectedPolicyRevision", ge=0)
    disposition: Literal["archive", "trash"]
    targets: tuple[TargetRequest, ...] = Field(min_length=1, max_length=100)
    temporal_filter: TemporalRequest = Field(alias="temporalFilter")
    read_state: Literal["any", "read", "unread"] = Field(alias="readState")
    excluded_label_ids: tuple[LabelId, ...] = Field(alias="excludedLabelIds", max_length=100)
    keep_latest_per_flow: StrictInt = Field(alias="keepLatestPerFlow", ge=0, le=10_000)

    @field_validator("command_id")
    @classmethod
    def _command_uuid(cls, value: str) -> str:
        return _uuid4_text(value)

    @model_validator(mode="after")
    def _canonical_collections(self) -> CreatePlanRequest:
        target_keys = tuple((item.kind, item.target_id) for item in self.targets)
        if len(target_keys) != len(set(target_keys)):
            raise ValueError("targets must be unique")
        label_ids = tuple(self.excluded_label_ids)
        if len(label_ids) != len(set(label_ids)):
            raise ValueError("excludedLabelIds must be unique")
        canonical_targets = tuple(
            sorted(
                self.targets,
                key=lambda item: (_TARGET_KIND_ORDER[item.kind], item.target_id),
            )
        )
        object.__setattr__(self, "targets", canonical_targets)
        object.__setattr__(self, "excluded_label_ids", tuple(sorted(label_ids)))
        return self


class RevalidatePlanRequest(_StrictModel):
    command_id: str = Field(alias="commandId")
    expected_plan_revision: StrictInt = Field(alias="expectedPlanRevision", ge=1)
    expected_map_revision: MapRevision = Field(alias="expectedMapRevision")
    expected_policy_revision: StrictInt = Field(alias="expectedPolicyRevision", ge=0)

    @field_validator("command_id")
    @classmethod
    def _command_uuid(cls, value: str) -> str:
        return _uuid4_text(value)


class CancelPlanRequest(_StrictModel):
    command_id: str = Field(alias="commandId")
    expected_plan_revision: StrictInt = Field(alias="expectedPlanRevision", ge=1)

    @field_validator("command_id")
    @classmethod
    def _command_uuid(cls, value: str) -> str:
        return _uuid4_text(value)


_CREATE_ADAPTER = TypeAdapter(CreatePlanRequest)
_REVALIDATE_ADAPTER = TypeAdapter(RevalidatePlanRequest)
_CANCEL_ADAPTER = TypeAdapter(CancelPlanRequest)


class LimitsResponse(_ResponseModel):
    max_targets: Literal[100] = 100
    max_excluded_labels: Literal[100] = 100
    max_considered_messages: Literal[100_000] = 100_000
    max_keep_latest_per_flow: Literal[10_000] = 10_000
    max_message_size_estimate_bytes: Literal[2_147_483_647] = 2_147_483_647
    max_aggregate_size_estimate_bytes: Literal[214_748_364_700_000] = 214_748_364_700_000
    max_target_page_size: Literal[100] = 100
    max_plan_page_size: Literal[100] = 100
    max_message_page_size: Literal[500] = 500
    max_event_page_size: Literal[100] = 100
    max_cursor_chars: Literal[1_024] = 1_024
    max_query_string_bytes: Literal[4_096] = 4_096
    max_visible_metadata_bytes: Literal[16_384] = 16_384
    max_request_body_bytes: Literal[65_536] = 65_536
    max_included_samples: Literal[5] = 5
    max_excluded_samples: Literal[5] = 5


class CapabilitiesResponse(_ResponseModel):
    study_read: Literal[True] = True
    target_read: Literal[True] = True
    plan_create: Literal[True] = True
    plan_revalidate: Literal[True] = True
    plan_cancel: Literal[True] = True
    system_label_filter: Literal[True] = True
    custom_label_filter: Literal[False] = False
    gmail_connection: Literal[False] = False
    oauth: Literal[False] = False
    external_network: Literal[False] = False
    real_data: Literal[False] = False
    message_mutation: Literal[False] = False
    unsubscribe: Literal[False] = False
    execute: Literal[False] = False


InventoryStateValue: TypeAlias = Literal[
    "not_started",
    "running",
    "paused",
    "completed",
    "requires_full_resync",
    "failed",
]


class AvailabilityResponse(_ResponseModel):
    account_available: bool
    inventory_state: InventoryStateValue | None
    complete_snapshot_available: bool
    current_map_revision: MapRevision | None
    current_policy_revision: int | None
    target_read_available: bool
    plan_create_available: bool
    plan_revalidate_available: bool
    blocker_codes: tuple[
        Literal["account_unavailable", "inventory_incomplete", "study_unavailable"], ...
    ]


class ContextResponse(_Envelope):
    time_zone: Literal["America/Argentina/Cordoba"] = TIME_ZONE
    plan_validity_seconds: Literal[86_400] = PLAN_VALIDITY_SECONDS
    limits: LimitsResponse = Field(default_factory=LimitsResponse)
    capabilities: CapabilitiesResponse = Field(default_factory=CapabilitiesResponse)
    availability: AvailabilityResponse


class SourceTargetResponse(_ResponseModel):
    kind: Literal["source"]
    target_id: SourceId
    display_name: str
    message_count: int


class FlowTargetResponse(_ResponseModel):
    kind: Literal["flow"]
    target_id: FlowId
    source_id: SourceId
    display_name: str
    message_count: int


class SenderTargetResponse(_ResponseModel):
    kind: Literal["sender"]
    target_id: SenderId
    display_address: str
    message_count: int


class LabelTargetResponse(_ResponseModel):
    kind: Literal["label"]
    target_id: LabelId
    display_name: str
    message_count: int


TargetResponse: TypeAlias = Annotated[
    SourceTargetResponse | FlowTargetResponse | SenderTargetResponse | LabelTargetResponse,
    Field(discriminator="kind"),
]


class TargetsResponse(_Envelope):
    map_revision: MapRevision
    policy_revision: int
    kind: Literal["source", "flow", "sender", "label"] | None
    items: tuple[TargetResponse, ...]
    next_cursor: str | None


class SelectionTargetResponse(_ResponseModel):
    kind: Literal["source", "flow", "sender"]
    target_id: str


class SourceTargetSnapshotResponse(_ResponseModel):
    kind: Literal["source"]
    target_id: SourceId
    display_name: str


class FlowTargetSnapshotResponse(_ResponseModel):
    kind: Literal["flow"]
    target_id: FlowId
    display_name: str


class SenderTargetSnapshotResponse(_ResponseModel):
    kind: Literal["sender"]
    target_id: SenderId
    display_address: str


TargetSnapshotResponse: TypeAlias = Annotated[
    SourceTargetSnapshotResponse | FlowTargetSnapshotResponse | SenderTargetSnapshotResponse,
    Field(discriminator="kind"),
]


class LabelSnapshotResponse(_ResponseModel):
    label_id: LabelId
    display_name: str


class AllTemporalResponse(_ResponseModel):
    kind: Literal["all"]


class BeforeDateTemporalResponse(_ResponseModel):
    kind: Literal["beforeDate"]
    date: CivilDate


class DateRangeTemporalResponse(_ResponseModel):
    kind: Literal["dateRange"]
    on_or_after_date: CivilDate
    before_date: CivilDate


class OlderThanDaysTemporalResponse(_ResponseModel):
    kind: Literal["olderThanDays"]
    days: int


TemporalResponse: TypeAlias = Annotated[
    AllTemporalResponse
    | BeforeDateTemporalResponse
    | DateRangeTemporalResponse
    | OlderThanDaysTemporalResponse,
    Field(discriminator="kind"),
]


class SelectionResponse(_ResponseModel):
    disposition: Literal["archive", "trash"]
    targets: tuple[SelectionTargetResponse, ...]
    target_snapshots: tuple[TargetSnapshotResponse, ...]
    temporal_filter_requested: TemporalResponse
    resolved_on_or_after_utc: datetime | None
    resolved_before_utc: datetime | None
    time_zone: Literal["America/Argentina/Cordoba"]
    read_state: Literal["any", "read", "unread"]
    excluded_label_ids: tuple[LabelId, ...]
    excluded_label_snapshots: tuple[LabelSnapshotResponse, ...]
    keep_latest_per_flow: int


class PlanSummaryResponse(_ResponseModel):
    plan_id: PlanId
    plan_revision: int
    state: Literal["frozen", "reduced", "invalidated", "cancelled", "expired"]
    created_at: datetime
    expires_at: datetime
    last_revalidated_at: datetime | None
    disposition: Literal["archive", "trash"]
    selected_at_creation_count: int
    selected_at_creation_size_estimate_bytes: int
    excluded_at_creation_count: int
    excluded_at_creation_size_estimate_bytes: int
    current_eligible_count: int
    current_eligible_size_estimate_bytes: int
    storage_effect: Literal["none", "not_guaranteed"]
    effective_freed_bytes: None = None
    can_execute: Literal[False] = False


class SampleResponse(_ResponseModel):
    message_id: MessageId
    received_at: datetime
    sender_name: str | None
    sender_address: str | None
    subject: str | None
    size_estimate_bytes: int
    source_id: SourceId
    flow_id: FlowId
    read_state: Literal["read", "unread"]
    exclusion_reasons: tuple[str, ...]


class EventResponse(_ResponseModel):
    revision: int
    type: Literal["created", "revalidated", "reduced", "invalidated", "cancelled"]
    recorded_at: datetime
    state: Literal["frozen", "reduced", "invalidated", "cancelled"]
    observed_map_revision: MapRevision | None
    observed_policy_revision: int | None
    removed_count: int
    remaining_count: int


class PlanDetailResponse(_Envelope):
    plan_id: PlanId
    plan_revision: int
    state: Literal["frozen", "reduced", "invalidated", "cancelled", "expired"]
    created_at: datetime
    expires_at: datetime
    last_revalidated_at: datetime | None
    disposition: Literal["archive", "trash"]
    selected_at_creation_count: int
    selected_at_creation_size_estimate_bytes: int
    excluded_at_creation_count: int
    excluded_at_creation_size_estimate_bytes: int
    current_eligible_count: int
    current_eligible_size_estimate_bytes: int
    storage_effect: Literal["none", "not_guaranteed"]
    effective_freed_bytes: None = None
    selection: SelectionResponse
    created_from_map_revision: MapRevision
    created_from_policy_revision: int
    current_map_revision: MapRevision | None
    current_policy_revision: int | None
    included_samples: tuple[SampleResponse, ...]
    excluded_samples: tuple[SampleResponse, ...]
    event_count: int
    recent_events: tuple[EventResponse, ...]
    warnings: tuple[
        Literal[
            "current_snapshot_unavailable",
            "map_changed_since_creation",
            "policy_changed_since_creation",
            "selection_reduced",
        ],
        ...,
    ]


class PlansResponse(_Envelope):
    listing_as_of: datetime
    catalog_revision: int
    state: Literal["frozen", "reduced", "invalidated", "cancelled", "expired"] | None
    items: tuple[PlanSummaryResponse, ...]
    next_cursor: str | None


class MemberResponse(_ResponseModel):
    message_id: MessageId
    initial_state: Literal["selected", "excluded"]
    current_state: Literal["eligible", "excluded", "removed"]
    received_at: datetime
    size_estimate_bytes: int
    reason_codes: tuple[str, ...]


class MessagesResponse(_Envelope):
    plan_id: PlanId
    plan_revision: int
    state: Literal["all", "selected", "eligible", "excluded", "removed"]
    items: tuple[MemberResponse, ...]
    next_cursor: str | None


class EventsResponse(_Envelope):
    plan_id: PlanId
    plan_revision: int
    items: tuple[EventResponse, ...]
    next_cursor: str | None


class CreateReceiptResponse(_Envelope):
    status: Literal["created"]
    replayed: bool
    command_revision: int
    plan_id: PlanId


class RevalidateReceiptResponse(_Envelope):
    status: Literal["revalidated"]
    replayed: bool
    command_revision: int
    removed_count: int
    plan_id: PlanId


class CancelReceiptResponse(_Envelope):
    status: Literal["cancelled"]
    replayed: bool
    command_revision: int
    plan_id: PlanId


class ErrorBody(_StrictModel):
    code: str
    message: str


class ErrorResponse(_Envelope):
    error: ErrorBody


_ERRORS: dict[str, tuple[int, str]] = {
    "invalid_request": (400, "El pedido no es válido."),
    "invalid_cursor": (400, "El cursor no es válido."),
    "invalid_local_origin": (403, "El origen local no está permitido."),
    "route_not_found": (404, "La ruta solicitada no existe."),
    "target_not_found": (404, "El objetivo no existe en la vista actual."),
    "plan_not_found": (404, "El plan solicitado no existe."),
    "method_not_allowed": (405, "El método no está permitido para esta ruta."),
    "map_revision_conflict": (409, "El mapa cambió. Actualizá la vista antes de reintentar."),
    "policy_revision_conflict": (
        409,
        "Las decisiones cambiaron. Actualizá la vista antes de reintentar.",
    ),
    "plan_revision_conflict": (409, "El plan cambió. Actualizá la vista antes de reintentar."),
    "command_id_conflict": (409, "El identificador del comando ya fue utilizado."),
    "cursor_stale": (409, "La página cambió. Reiniciá la consulta."),
    "invalid_transition": (409, "La transición solicitada no está permitida."),
    "plan_expired": (409, "El plan venció. Creá uno nuevo."),
    "payload_too_large": (413, "El pedido supera el tamaño permitido."),
    "plan_too_large": (413, "El plan supera el límite de mensajes permitido."),
    "json_required": (415, "Se requiere un cuerpo JSON."),
    "unsupported_target": (422, "El tipo de objetivo no está permitido."),
    "invalid_filter": (422, "El filtro solicitado no es válido."),
    "study_unavailable": (503, "El Estudio de Limpieza no está disponible."),
    "inventory_incomplete": (503, "El inventario todavía no está completo."),
    "account_unavailable": (503, "La cuenta sintética no está disponible."),
    "internal_error": (500, "No se pudo completar la operación."),
}


def _error_response(code: str) -> JSONResponse:
    public_code = code if code in _ERRORS else "internal_error"
    status_code, message = _ERRORS[public_code]
    body = ErrorResponse(error=ErrorBody(code=public_code, message=message))
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(by_alias=True, mode="json"),
        headers={"Cache-Control": "no-store"},
    )


def _json_model(value: BaseModel) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=value.model_dump(by_alias=True, mode="json"),
        headers={"Cache-Control": "no-store"},
    )


def _header_values(scope: Scope, name: bytes) -> tuple[str, ...]:
    return tuple(
        value.decode("latin-1") for key, value in scope.get("headers", ()) if key.lower() == name
    )


@dataclass(frozen=True, slots=True)
class _RouteRule:
    methods: frozenset[str]
    query_names: frozenset[str]


_STATIC_RULES = {
    f"{API_PREFIX}/context": _RouteRule(frozenset({"GET"}), frozenset()),
    f"{API_PREFIX}/targets": _RouteRule(frozenset({"GET"}), frozenset({"kind", "cursor", "limit"})),
    f"{API_PREFIX}/plans": _RouteRule(
        frozenset({"GET", "POST"}), frozenset({"state", "cursor", "limit"})
    ),
}


def _route_rule(path: str) -> _RouteRule | None:
    static = _STATIC_RULES.get(path)
    if static is not None:
        return static
    prefix = f"{API_PREFIX}/plans/"
    if not path.startswith(prefix):
        return None
    suffix = path[len(prefix) :]
    parts = suffix.split("/")
    if not parts[0] or len(parts[0]) > 96:
        return None
    if len(parts) == 1:
        return _RouteRule(frozenset({"GET"}), frozenset())
    if len(parts) != 2:
        return None
    if parts[1] == "messages":
        return _RouteRule(frozenset({"GET"}), frozenset({"state", "cursor", "limit"}))
    if parts[1] == "events":
        return _RouteRule(frozenset({"GET"}), frozenset({"cursor", "limit"}))
    if parts[1] in {"revalidate", "cancel"}:
        return _RouteRule(frozenset({"POST"}), frozenset())
    return None


def _is_json_content_type(value: str) -> bool:
    media_type, separator, parameters = value.casefold().partition(";")
    if media_type.strip() != "application/json":
        return False
    if not separator:
        return True
    return parameters.strip() in {"charset=utf-8", 'charset="utf-8"'}


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


class StudyV3SecurityMiddleware:
    """Deny-by-default boundary for exactly the nine local study routes."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        if scope["type"] != "http" or not path.startswith(API_PREFIX):
            await self._app(scope, receive, send)
            return

        rule = _route_rule(path)
        if rule is None:
            await _error_response("route_not_found")(scope, receive, send)
            return
        method = str(scope.get("method", "")).upper()
        if method not in rule.methods:
            await _error_response("method_not_allowed")(scope, receive, send)
            return
        if _header_values(scope, b"host") != (LOCAL_HOST,):
            await _error_response("invalid_local_origin")(scope, receive, send)
            return
        if _header_values(scope, b"cookie"):
            await _error_response("invalid_local_origin")(scope, receive, send)
            return

        raw_query = bytes(scope.get("query_string", b""))
        if len(raw_query) > MAX_QUERY_BYTES:
            await _error_response("invalid_request")(scope, receive, send)
            return
        try:
            query = QueryParams(raw_query.decode("ascii"))
        except UnicodeDecodeError:
            await _error_response("invalid_request")(scope, receive, send)
            return
        names = tuple(name for name, _value in query.multi_items())
        if len(names) != len(set(names)) or any(name not in rule.query_names for name in names):
            await _error_response("invalid_request")(scope, receive, send)
            return
        if method == "POST" and names:
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
            lengths = _header_values(scope, b"content-length")
            if len(lengths) > 1:
                await _error_response("invalid_request")(scope, receive, send)
                return
            if lengths:
                try:
                    length = int(lengths[0])
                except ValueError:
                    await _error_response("invalid_request")(scope, receive, send)
                    return
                if length < 0:
                    await _error_response("invalid_request")(scope, receive, send)
                    return
                if length > MAX_JSON_BYTES:
                    await _error_response("payload_too_large")(scope, receive, send)
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


class _DuplicateJsonKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey
        result[key] = value
    return result


class _InvalidPublicRequest(RuntimeError):
    __slots__ = ()


class _PublicApiError(RuntimeError):
    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_BodyAdapter: TypeAlias = (
    TypeAdapter[CreatePlanRequest]
    | TypeAdapter[RevalidatePlanRequest]
    | TypeAdapter[CancelPlanRequest]
)


async def _validated_body(
    request: Request,
    adapter: _BodyAdapter,
) -> CreatePlanRequest | RevalidatePlanRequest | CancelPlanRequest:
    try:
        raw = await request.body()
        decoded = raw.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=_unique_object)
        if not isinstance(value, dict):
            raise ValueError
        targets = value.get("targets")
        if isinstance(targets, list) and any(
            isinstance(item, dict) and item.get("kind") == "label" for item in targets
        ):
            raise _PublicApiError("unsupported_target")
        return adapter.validate_python(value)
    except _PublicApiError:
        raise
    except ValidationError as error:
        if any(
            issue.get("loc") and str(issue["loc"][0]) in {"temporalFilter", "temporal_filter"}
            for issue in error.errors()
        ):
            raise _PublicApiError("invalid_filter") from None
        raise _InvalidPublicRequest from None
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJsonKey,
        ValueError,
        RecursionError,
    ):
        raise _InvalidPublicRequest from None


@dataclass(frozen=True, slots=True, repr=False)
class _CursorBinding:
    route: str
    filter_value: str | None
    limit: int
    revision: str
    offset: int
    listing_as_of: datetime | None = None

    def __repr__(self) -> str:
        return "_CursorBinding(<redacted>)"


class _CursorStore:
    def __init__(self, capacity: int = 2_048) -> None:
        self._capacity = capacity
        self._items: dict[str, _CursorBinding] = {}
        self._lock = Lock()

    def issue(self, binding: _CursorBinding) -> str:
        with self._lock:
            token = uuid4().hex + uuid4().hex
            self._items[token] = binding
            while len(self._items) > self._capacity:
                del self._items[next(iter(self._items))]
        return token

    def resolve_request(
        self,
        token: str,
        *,
        route: str,
        filter_value: str | None,
        limit: int,
    ) -> _CursorBinding:
        if (
            not isinstance(token, str)
            or not token
            or len(token) > MAX_CURSOR_CHARS
            or not token.isascii()
        ):
            raise _PublicApiError("invalid_cursor")
        with self._lock:
            binding = self._items.get(token)
        if binding is None:
            raise _PublicApiError("invalid_cursor")
        if (
            binding.route != route
            or binding.filter_value != filter_value
            or binding.limit != limit
        ):
            raise _PublicApiError("cursor_stale")
        return binding

    def resolve(
        self,
        token: str,
        *,
        route: str,
        filter_value: str | None,
        limit: int,
        revision: str,
    ) -> _CursorBinding:
        binding = self.resolve_request(
            token,
            route=route,
            filter_value=filter_value,
            limit=limit,
        )
        if binding.revision != revision:
            raise _PublicApiError("cursor_stale")
        return binding


def _page(
    values: tuple[object, ...],
    *,
    cursor: str | None,
    route: str,
    filter_value: str | None,
    limit: int,
    revision: str,
    cursors: _CursorStore,
) -> tuple[tuple[object, ...], str | None]:
    offset = (
        0
        if cursor is None
        else cursors.resolve(
            cursor,
            route=route,
            filter_value=filter_value,
            limit=limit,
            revision=revision,
        ).offset
    )
    if offset < 0 or offset > len(values):
        raise _PublicApiError("cursor_stale")
    items = values[offset : offset + limit]
    next_offset = offset + len(items)
    next_cursor = None
    if next_offset < len(values):
        next_cursor = cursors.issue(
            _CursorBinding(
                route=route,
                filter_value=filter_value,
                limit=limit,
                revision=revision,
                offset=next_offset,
            )
        )
    return items, next_cursor


def _query_value(request: Request, name: str) -> str | None:
    return request.query_params.get(name)


def _limit(request: Request, *, default: int, maximum: int) -> int:
    raw = _query_value(request, "limit")
    if raw is None:
        return default
    if not raw.isascii() or not raw.isdecimal():
        raise _PublicApiError("invalid_request")
    value = int(raw)
    if not 1 <= value <= maximum:
        raise _PublicApiError("invalid_request")
    return value


def _plan_id(value: str) -> str:
    if _PLAN_ID.fullmatch(value) is None:
        raise _PublicApiError("plan_not_found")
    return value


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _clock(app: FastAPI) -> Callable[[], datetime]:
    candidate = getattr(app.state, "cleanup_plan_clock", None)
    if candidate is None:
        return _default_clock
    if not callable(candidate):
        raise _PublicApiError("internal_error")
    return cast(Callable[[], datetime], candidate)


def _read_now(app: FastAPI) -> datetime:
    value = _clock(app)()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise _PublicApiError("internal_error")
    return value.astimezone(UTC)


def _target_command(value: TargetRequest) -> CleanupTarget:
    return CleanupTarget(
        kind=CleanupTargetKind(value.kind),
        target_id=value.target_id,
    )


def _temporal_command(
    value: TemporalRequest,
) -> (
    AllTemporalFilter
    | BeforeDateTemporalFilter
    | DateRangeTemporalFilter
    | OlderThanDaysTemporalFilter
):
    if isinstance(value, AllTemporalRequest):
        return AllTemporalFilter()
    if isinstance(value, BeforeDateTemporalRequest):
        return BeforeDateTemporalFilter(date=value.date)
    if isinstance(value, DateRangeTemporalRequest):
        return DateRangeTemporalFilter(
            on_or_after_date=value.on_or_after_date,
            before_date=value.before_date,
        )
    if isinstance(value, OlderThanDaysTemporalRequest):
        return OlderThanDaysTemporalFilter(days=value.days)
    raise _PublicApiError("invalid_filter")


def _create_command(value: CreatePlanRequest) -> CreateCleanupPlanCommand:
    try:
        return CreateCleanupPlanCommand(
            command_id=value.command_id,
            expected_map_revision=value.expected_map_revision,
            expected_policy_revision=value.expected_policy_revision,
            disposition=CleanupDisposition(value.disposition),
            targets=tuple(_target_command(item) for item in value.targets),
            temporal_filter=_temporal_command(value.temporal_filter),
            read_state=CleanupReadState(value.read_state),
            excluded_label_ids=tuple(value.excluded_label_ids),
            keep_latest_per_flow=value.keep_latest_per_flow,
        )
    except _PublicApiError:
        raise
    except (TypeError, ValueError):
        raise _PublicApiError("invalid_request") from None


def _revalidate_command(value: RevalidatePlanRequest) -> RevalidateCleanupPlanCommand:
    try:
        return RevalidateCleanupPlanCommand(
            command_id=value.command_id,
            expected_plan_revision=value.expected_plan_revision,
            expected_map_revision=value.expected_map_revision,
            expected_policy_revision=value.expected_policy_revision,
        )
    except (TypeError, ValueError):
        raise _PublicApiError("invalid_request") from None


def _cancel_command(value: CancelPlanRequest) -> CancelCleanupPlanCommand:
    try:
        return CancelCleanupPlanCommand(
            command_id=value.command_id,
            expected_plan_revision=value.expected_plan_revision,
        )
    except (TypeError, ValueError):
        raise _PublicApiError("invalid_request") from None


def _temporal_response(
    value: AllTemporalFilter
    | BeforeDateTemporalFilter
    | DateRangeTemporalFilter
    | OlderThanDaysTemporalFilter,
) -> TemporalResponse:
    if isinstance(value, AllTemporalFilter):
        return AllTemporalResponse(kind="all")
    if isinstance(value, BeforeDateTemporalFilter):
        return BeforeDateTemporalResponse(kind="beforeDate", date=value.date)
    if isinstance(value, DateRangeTemporalFilter):
        return DateRangeTemporalResponse(
            kind="dateRange",
            on_or_after_date=value.on_or_after_date,
            before_date=value.before_date,
        )
    if isinstance(value, OlderThanDaysTemporalFilter):
        return OlderThanDaysTemporalResponse(kind="olderThanDays", days=value.days)
    raise _PublicApiError("internal_error")


def _selection_response(plan: PersistedCleanupPlan) -> SelectionResponse:
    snapshots: list[TargetSnapshotResponse] = []
    for snapshot in plan.selection.target_snapshots:
        if isinstance(snapshot, SourceTargetSnapshot):
            snapshots.append(
                SourceTargetSnapshotResponse(
                    kind="source",
                    target_id=snapshot.target_id,
                    display_name=snapshot.display_name,
                )
            )
        elif isinstance(snapshot, FlowTargetSnapshot):
            snapshots.append(
                FlowTargetSnapshotResponse(
                    kind="flow",
                    target_id=snapshot.target_id,
                    display_name=snapshot.display_name,
                )
            )
        elif isinstance(snapshot, SenderTargetSnapshot):
            snapshots.append(
                SenderTargetSnapshotResponse(
                    kind="sender",
                    target_id=snapshot.target_id,
                    display_address=snapshot.display_address,
                )
            )
        else:
            raise _PublicApiError("internal_error")
    temporal = plan.selection.temporal_filter
    return SelectionResponse(
        disposition=plan.selection.disposition.value,
        targets=tuple(
            SelectionTargetResponse(
                kind=cast(Literal["source", "flow", "sender"], item.kind.value),
                target_id=item.target_id,
            )
            for item in plan.selection.targets
        ),
        target_snapshots=tuple(snapshots),
        temporal_filter_requested=_temporal_response(temporal.requested),
        resolved_on_or_after_utc=temporal.resolved_on_or_after_utc,
        resolved_before_utc=temporal.resolved_before_utc,
        time_zone=cast(Literal["America/Argentina/Cordoba"], temporal.time_zone),
        read_state=plan.selection.read_state.value,
        excluded_label_ids=plan.selection.excluded_label_ids,
        excluded_label_snapshots=tuple(
            LabelSnapshotResponse(
                label_id=item.label_id,
                display_name=item.display_name,
            )
            for item in plan.selection.excluded_label_snapshots
        ),
        keep_latest_per_flow=plan.selection.keep_latest_per_flow,
    )


def _summary_response(
    plan: PersistedCleanupPlan,
    listing_as_of: datetime,
) -> PlanSummaryResponse:
    return PlanSummaryResponse(
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        state=effective_plan_state(plan, listing_as_of).value,
        created_at=plan.created_at,
        expires_at=plan.expires_at,
        last_revalidated_at=plan.last_revalidated_at,
        disposition=plan.selection.disposition.value,
        selected_at_creation_count=plan.selected_at_creation_count,
        selected_at_creation_size_estimate_bytes=(plan.selected_at_creation_size_estimate_bytes),
        excluded_at_creation_count=plan.excluded_at_creation_count,
        excluded_at_creation_size_estimate_bytes=(plan.excluded_at_creation_size_estimate_bytes),
        current_eligible_count=plan.current_eligible_count,
        current_eligible_size_estimate_bytes=plan.current_eligible_size_estimate_bytes,
        storage_effect=plan.storage_effect.value,
        effective_freed_bytes=None,
        can_execute=False,
    )


def _listing_summary_response(plan: CleanupPlanListingItem) -> PlanSummaryResponse:
    return PlanSummaryResponse(
        plan_id=plan.plan_id,
        plan_revision=plan.plan_revision,
        state=plan.state.value,
        created_at=plan.created_at,
        expires_at=plan.expires_at,
        last_revalidated_at=plan.last_revalidated_at,
        disposition=plan.disposition.value,
        selected_at_creation_count=plan.selected_at_creation_count,
        selected_at_creation_size_estimate_bytes=(
            plan.selected_at_creation_size_estimate_bytes
        ),
        excluded_at_creation_count=plan.excluded_at_creation_count,
        excluded_at_creation_size_estimate_bytes=(
            plan.excluded_at_creation_size_estimate_bytes
        ),
        current_eligible_count=plan.current_eligible_count,
        current_eligible_size_estimate_bytes=plan.current_eligible_size_estimate_bytes,
        storage_effect=plan.storage_effect.value,
        effective_freed_bytes=None,
        can_execute=False,
    )


def _event_response(value: CleanupPlanEvent) -> EventResponse:
    return EventResponse(
        revision=value.revision,
        type=value.type.value,
        recorded_at=value.recorded_at,
        state=cast(
            Literal["frozen", "reduced", "invalidated", "cancelled"],
            value.state.value,
        ),
        observed_map_revision=value.observed_map_revision,
        observed_policy_revision=value.observed_policy_revision,
        removed_count=value.removed_count,
        remaining_count=value.remaining_count,
    )


def _sample_response(value: CleanupPlanSample) -> SampleResponse:
    return SampleResponse(
        message_id=value.message_id,
        received_at=value.received_at,
        sender_name=value.sender_name,
        sender_address=value.sender_address,
        subject=value.subject,
        size_estimate_bytes=value.size_estimate_bytes,
        source_id=value.source_id,
        flow_id=value.flow_id,
        read_state=cast(Literal["read", "unread"], value.read_state.value),
        exclusion_reasons=tuple(item.value for item in value.exclusion_reasons),
    )


def _target_response(value: object) -> TargetResponse:
    if isinstance(value, SourceCatalogItem):
        return SourceTargetResponse(
            kind="source",
            target_id=value.target_id,
            display_name=value.display_name,
            message_count=value.message_count,
        )
    if isinstance(value, FlowCatalogItem):
        return FlowTargetResponse(
            kind="flow",
            target_id=value.target_id,
            source_id=value.source_id,
            display_name=value.display_name,
            message_count=value.message_count,
        )
    if isinstance(value, SenderCatalogItem):
        return SenderTargetResponse(
            kind="sender",
            target_id=value.target_id,
            display_address=value.display_address,
            message_count=value.message_count,
        )
    if isinstance(value, LabelCatalogItem):
        return LabelTargetResponse(
            kind="label",
            target_id=value.target_id,
            display_name=value.display_name,
            message_count=value.message_count,
        )
    raise _PublicApiError("internal_error")


def _receipt_response(
    value: CleanupPlanReceipt,
) -> CreateReceiptResponse | RevalidateReceiptResponse | CancelReceiptResponse:
    if value.status.value == "created":
        return CreateReceiptResponse(
            status="created",
            replayed=value.replayed,
            command_revision=value.command_revision,
            plan_id=value.plan_id,
        )
    if value.status.value == "revalidated" and value.removed_count is not None:
        return RevalidateReceiptResponse(
            status="revalidated",
            replayed=value.replayed,
            command_revision=value.command_revision,
            removed_count=value.removed_count,
            plan_id=value.plan_id,
        )
    if value.status.value == "cancelled":
        return CancelReceiptResponse(
            status="cancelled",
            replayed=value.replayed,
            command_revision=value.command_revision,
            plan_id=value.plan_id,
        )
    raise _PublicApiError("internal_error")


def _availability(repository: Repository) -> AvailabilityResponse:
    snapshot = repository.cleanup_plan_context(SYNTHETIC_MAP_ACCOUNT_KEY)
    if not snapshot.account_exists:
        return AvailabilityResponse(
            account_available=False,
            inventory_state=None,
            complete_snapshot_available=False,
            current_map_revision=None,
            current_policy_revision=None,
            target_read_available=False,
            plan_create_available=False,
            plan_revalidate_available=False,
            blocker_codes=("account_unavailable",),
        )
    inventory_state: InventoryStateValue = (
        snapshot.checkpoint.state.value
        if snapshot.checkpoint is not None
        else SyncState.NOT_STARTED.value
    )
    if snapshot.checkpoint is None or snapshot.checkpoint.state is not SyncState.COMPLETED:
        return AvailabilityResponse(
            account_available=True,
            inventory_state=inventory_state,
            complete_snapshot_available=False,
            current_map_revision=None,
            current_policy_revision=None,
            target_read_available=False,
            plan_create_available=False,
            plan_revalidate_available=False,
            blocker_codes=("inventory_incomplete",),
        )
    try:
        composition = compose_cleanup_plan_snapshot(snapshot)
    except CleanupPlanError:
        return AvailabilityResponse(
            account_available=True,
            inventory_state=inventory_state,
            complete_snapshot_available=False,
            current_map_revision=None,
            current_policy_revision=None,
            target_read_available=False,
            plan_create_available=False,
            plan_revalidate_available=False,
            blocker_codes=("study_unavailable",),
        )
    return AvailabilityResponse(
        account_available=True,
        inventory_state=inventory_state,
        complete_snapshot_available=True,
        current_map_revision=composition.projection.map_revision,
        current_policy_revision=composition.projection.policy_revision,
        target_read_available=True,
        plan_create_available=True,
        plan_revalidate_available=True,
        blocker_codes=(),
    )


def _context_response(repository: Repository) -> ContextResponse:
    return ContextResponse(availability=_availability(repository))


def _targets_response(
    request: Request,
    repository: Repository,
    cursors: _CursorStore,
) -> TargetsResponse:
    raw_kind = _query_value(request, "kind")
    allowed_kinds = {"source", "flow", "sender", "label"}
    if raw_kind is not None and raw_kind not in allowed_kinds:
        raise _PublicApiError("invalid_request")
    limit = _limit(request, default=50, maximum=100)
    cursor = _query_value(request, "cursor")
    composition = repository.cleanup_plan_targets(SYNTHETIC_MAP_ACCOUNT_KEY)
    catalog = build_cleanup_target_catalog(composition)
    if raw_kind is not None:
        catalog = tuple(item for item in catalog if item.kind.value == raw_kind)
    revision = (
        composition.projection.map_revision + ":" + str(composition.projection.policy_revision)
    )
    page, next_cursor = _page(
        cast(tuple[object, ...], catalog),
        cursor=cursor,
        route=f"{API_PREFIX}/targets",
        filter_value=raw_kind,
        limit=limit,
        revision=revision,
        cursors=cursors,
    )
    return TargetsResponse(
        map_revision=composition.projection.map_revision,
        policy_revision=composition.projection.policy_revision,
        kind=cast(Literal["source", "flow", "sender", "label"] | None, raw_kind),
        items=tuple(_target_response(item) for item in page),
        next_cursor=next_cursor,
    )


def _plans_response(
    request: Request,
    repository: Repository,
    cursors: _CursorStore,
    clock: Callable[[], datetime],
) -> PlansResponse:
    raw_state = _query_value(request, "state")
    allowed_states = {"frozen", "reduced", "invalidated", "cancelled", "expired"}
    if raw_state is not None and raw_state not in allowed_states:
        raise _PublicApiError("invalid_request")
    limit = _limit(request, default=50, maximum=100)
    cursor = _query_value(request, "cursor")
    route = f"{API_PREFIX}/plans"
    if cursor is None:
        binding = None
        snapshot_clock = clock
        offset = 0
        expected_catalog_revision = None
    else:
        binding = cursors.resolve_request(
            cursor,
            route=route,
            filter_value=raw_state,
            limit=limit,
        )
        if binding.listing_as_of is None:
            raise _PublicApiError("invalid_cursor")
        try:
            expected_catalog_revision = int(binding.revision)
        except ValueError:
            raise _PublicApiError("invalid_cursor") from None
        offset = binding.offset

        def snapshot_clock() -> datetime:
            assert binding is not None and binding.listing_as_of is not None
            return binding.listing_as_of

    page = repository.cleanup_plan_listing_page(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        state=CleanupPlanState(raw_state) if raw_state is not None else None,
        limit=limit,
        offset=offset,
        expected_catalog_revision=expected_catalog_revision,
        clock=snapshot_clock,
    )
    if binding is not None and offset > 0 and not page.items:
        raise _PublicApiError("cursor_stale")
    revision = str(page.catalog_revision)
    next_offset = offset + len(page.items)
    next_cursor = None
    if page.has_more:
        next_cursor = cursors.issue(
            _CursorBinding(
                route=route,
                filter_value=raw_state,
                limit=limit,
                revision=revision,
                offset=next_offset,
                listing_as_of=page.listing_as_of,
            )
        )
    return PlansResponse(
        listing_as_of=page.listing_as_of,
        catalog_revision=page.catalog_revision,
        state=cast(
            Literal["frozen", "reduced", "invalidated", "cancelled", "expired"] | None,
            raw_state,
        ),
        items=tuple(_listing_summary_response(item) for item in page.items),
        next_cursor=next_cursor,
    )


def _current_revisions(
    repository: Repository,
) -> tuple[str | None, int | None]:
    try:
        snapshot = repository.cleanup_plan_context(SYNTHETIC_MAP_ACCOUNT_KEY)
        if (
            not snapshot.account_exists
            or snapshot.checkpoint is None
            or snapshot.checkpoint.state is not SyncState.COMPLETED
        ):
            return None, None
        composition = compose_cleanup_plan_snapshot(snapshot)
    except CleanupPlanError:
        return None, None
    return (
        composition.projection.map_revision,
        composition.projection.policy_revision,
    )


def _detail_response(
    repository: Repository,
    plan: PersistedCleanupPlan,
    now: datetime,
) -> PlanDetailResponse:
    current_map_revision, current_policy_revision = _current_revisions(repository)
    warnings: list[str] = []
    if current_map_revision is None:
        warnings.append("current_snapshot_unavailable")
    else:
        if current_map_revision != plan.created_from_map_revision:
            warnings.append("map_changed_since_creation")
        if current_policy_revision != plan.created_from_policy_revision:
            warnings.append("policy_changed_since_creation")
    if plan.removals:
        warnings.append("selection_reduced")
    summary = _summary_response(plan, now)
    return PlanDetailResponse(
        **summary.model_dump(),
        selection=_selection_response(plan),
        created_from_map_revision=plan.created_from_map_revision,
        created_from_policy_revision=plan.created_from_policy_revision,
        current_map_revision=current_map_revision,
        current_policy_revision=current_policy_revision,
        included_samples=tuple(
            _sample_response(item)
            for item in plan.samples
            if item.kind is CleanupSampleKind.INCLUDED
        ),
        excluded_samples=tuple(
            _sample_response(item)
            for item in plan.samples
            if item.kind is CleanupSampleKind.EXCLUDED
        ),
        event_count=len(plan.events),
        recent_events=tuple(_event_response(item) for item in reversed(plan.events[-10:])),
        warnings=cast(
            tuple[
                Literal[
                    "current_snapshot_unavailable",
                    "map_changed_since_creation",
                    "policy_changed_since_creation",
                    "selection_reduced",
                ],
                ...,
            ],
            tuple(warnings),
        ),
    )


def _message_response(member: CleanupPlanMemberItem) -> MemberResponse:
    return MemberResponse(
        message_id=member.message_id,
        initial_state=member.initial_state.value,
        current_state=member.current_state.value,
        received_at=member.received_at,
        size_estimate_bytes=member.size_estimate_bytes,
        reason_codes=tuple(item.value for item in member.reason_codes),
    )


def _messages_response(
    request: Request,
    repository: Repository,
    plan_id: str,
    cursors: _CursorStore,
) -> MessagesResponse:
    raw_state = _query_value(request, "state")
    if raw_state is None:
        raw_state = "all"
    allowed_states = {"all", "selected", "eligible", "excluded", "removed"}
    if raw_state not in allowed_states:
        raise _PublicApiError("invalid_request")
    limit = _limit(request, default=100, maximum=500)
    cursor = _query_value(request, "cursor")
    route = f"{API_PREFIX}/plans/{plan_id}/messages"
    if cursor is None:
        binding = None
        offset = 0
        expected_plan_revision = None
    else:
        binding = cursors.resolve_request(
            cursor,
            route=route,
            filter_value=raw_state,
            limit=limit,
        )
        try:
            expected_plan_revision = int(binding.revision)
        except ValueError:
            raise _PublicApiError("invalid_cursor") from None
        offset = binding.offset
    page = repository.cleanup_plan_member_page(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        plan_id,
        state=raw_state,
        limit=limit,
        offset=offset,
        expected_plan_revision=expected_plan_revision,
    )
    if page is None:
        raise _PublicApiError("plan_not_found")
    if binding is not None and offset > 0 and not page.items:
        raise _PublicApiError("cursor_stale")
    next_cursor = None
    if page.has_more:
        next_cursor = cursors.issue(
            _CursorBinding(
                route=route,
                filter_value=raw_state,
                limit=limit,
                revision=str(page.plan_revision),
                offset=offset + len(page.items),
            )
        )
    return MessagesResponse(
        plan_id=page.plan_id,
        plan_revision=page.plan_revision,
        state=cast(Literal["all", "selected", "eligible", "excluded", "removed"], raw_state),
        items=tuple(_message_response(item) for item in page.items),
        next_cursor=next_cursor,
    )


def _events_response(
    request: Request,
    repository: Repository,
    plan_id: str,
    cursors: _CursorStore,
) -> EventsResponse:
    limit = _limit(request, default=50, maximum=100)
    cursor = _query_value(request, "cursor")
    route = f"{API_PREFIX}/plans/{plan_id}/events"
    if cursor is None:
        binding = None
        offset = 0
        expected_plan_revision = None
    else:
        binding = cursors.resolve_request(
            cursor,
            route=route,
            filter_value=None,
            limit=limit,
        )
        try:
            expected_plan_revision = int(binding.revision)
        except ValueError:
            raise _PublicApiError("invalid_cursor") from None
        offset = binding.offset
    page = repository.cleanup_plan_event_page(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        plan_id,
        limit=limit,
        offset=offset,
        expected_plan_revision=expected_plan_revision,
    )
    if page is None:
        raise _PublicApiError("plan_not_found")
    if binding is not None and offset > 0 and not page.items:
        raise _PublicApiError("cursor_stale")
    next_cursor = None
    if page.has_more:
        next_cursor = cursors.issue(
            _CursorBinding(
                route=route,
                filter_value=None,
                limit=limit,
                revision=str(page.plan_revision),
                offset=offset + len(page.items),
            )
        )
    return EventsResponse(
        plan_id=page.plan_id,
        plan_revision=page.plan_revision,
        items=tuple(_event_response(item) for item in page.items),
        next_cursor=next_cursor,
    )


def _result(action: Callable[[], BaseModel]) -> Response:
    try:
        return _json_model(action())
    except _PublicApiError as error:
        return _error_response(error.code)
    except CleanupPlanError as error:
        return _error_response(error.code.value)
    except (TypeError, ValueError):
        return _error_response("internal_error")
    except Exception:
        return _error_response("internal_error")


def _request_error(error: BaseException) -> Response:
    if isinstance(error, _PublicApiError):
        return _error_response(error.code)
    if isinstance(error, _InvalidPublicRequest):
        return _error_response("invalid_request")
    if isinstance(error, CleanupPlanError):
        return _error_response(error.code.value)
    return _error_response("internal_error")


def install_cleanup_plan_api(app: FastAPI, repository: Repository) -> None:
    """Install the deny-by-default, synthetic and non-executable C6 surface."""

    router = APIRouter(prefix=API_PREFIX)
    cursors = _CursorStore()
    app.state.cleanup_plan_cursors = cursors

    @router.get("/context")
    def context() -> Response:
        return _result(lambda: _context_response(repository))

    @router.get("/targets")
    def targets(request: Request) -> Response:
        return _result(lambda: _targets_response(request, repository, cursors))

    @router.post("/plans")
    async def create_plan(request: Request) -> Response:
        try:
            parsed = cast(
                CreatePlanRequest,
                await _validated_body(request, _CREATE_ADAPTER),
            )
            command = _create_command(parsed)
            fingerprint = cleanup_command_fingerprint(command)
            receipt = repository.create_cleanup_plan(
                SYNTHETIC_MAP_ACCOUNT_KEY,
                command,
                request_fingerprint=fingerprint,
                clock=_clock(app),
            )
            return _json_model(_receipt_response(receipt))
        except Exception as error:
            return _request_error(error)

    @router.get("/plans")
    def plans(request: Request) -> Response:
        return _result(
            lambda: _plans_response(
                request,
                repository,
                cursors,
                _clock(app),
            )
        )

    @router.get("/plans/{planId}")
    def plan_detail(planId: str) -> Response:
        def action() -> BaseModel:
            normalized = _plan_id(planId)
            plan = repository.cleanup_plan(SYNTHETIC_MAP_ACCOUNT_KEY, normalized)
            if plan is None:
                raise _PublicApiError("plan_not_found")
            return _detail_response(repository, plan, _read_now(app))

        return _result(action)

    @router.get("/plans/{planId}/messages")
    def plan_messages(planId: str, request: Request) -> Response:
        def action() -> BaseModel:
            normalized = _plan_id(planId)
            return _messages_response(request, repository, normalized, cursors)

        return _result(action)

    @router.get("/plans/{planId}/events")
    def plan_events(planId: str, request: Request) -> Response:
        def action() -> BaseModel:
            normalized = _plan_id(planId)
            return _events_response(request, repository, normalized, cursors)

        return _result(action)

    @router.post("/plans/{planId}/revalidate")
    async def revalidate_plan(planId: str, request: Request) -> Response:
        try:
            normalized = _plan_id(planId)
            parsed = cast(
                RevalidatePlanRequest,
                await _validated_body(request, _REVALIDATE_ADAPTER),
            )
            command = _revalidate_command(parsed)
            fingerprint = cleanup_command_fingerprint(command, plan_id=normalized)
            receipt = repository.revalidate_cleanup_plan(
                SYNTHETIC_MAP_ACCOUNT_KEY,
                normalized,
                command,
                request_fingerprint=fingerprint,
                clock=_clock(app),
            )
            return _json_model(_receipt_response(receipt))
        except Exception as error:
            return _request_error(error)

    @router.post("/plans/{planId}/cancel")
    async def cancel_plan(planId: str, request: Request) -> Response:
        try:
            normalized = _plan_id(planId)
            parsed = cast(
                CancelPlanRequest,
                await _validated_body(request, _CANCEL_ADAPTER),
            )
            command = _cancel_command(parsed)
            fingerprint = cleanup_command_fingerprint(command, plan_id=normalized)
            receipt = repository.cancel_cleanup_plan(
                SYNTHETIC_MAP_ACCOUNT_KEY,
                normalized,
                command,
                request_fingerprint=fingerprint,
                clock=_clock(app),
            )
            return _json_model(_receipt_response(receipt))
        except Exception as error:
            return _request_error(error)

    app.include_router(router)
    app.add_middleware(StudyV3SecurityMiddleware)
