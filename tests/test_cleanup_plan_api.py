from __future__ import annotations

import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import mailmap.cleanup_plan_api as cleanup_api
from mailmap.api import create_app
from mailmap.cleanup_plan_model import (
    CleanupEventType,
    CleanupMemberInitialState,
    CleanupPlanError,
    CleanupPlanErrorCode,
    CleanupPlanEvent,
    CleanupPlanMember,
)
from mailmap.index_model import SyncState
from mailmap.map_fixtures import canonical_synthetic_map_fixture
from mailmap.map_synthetic_gate import SYNTHETIC_MAP_ACCOUNT_KEY

HOST_HEADERS = {"Host": "127.0.0.1:8765"}
POST_HEADERS = {
    **HOST_HEADERS,
    "Origin": "http://127.0.0.1:8765",
}
COMMON_KEYS = {"contractVersion", "dataMode", "canExecute"}
SUMMARY_KEYS = {
    "planId",
    "planRevision",
    "state",
    "createdAt",
    "expiresAt",
    "lastRevalidatedAt",
    "disposition",
    "selectedAtCreationCount",
    "selectedAtCreationSizeEstimateBytes",
    "excludedAtCreationCount",
    "excludedAtCreationSizeEstimateBytes",
    "currentEligibleCount",
    "currentEligibleSizeEstimateBytes",
    "storageEffect",
    "effectiveFreedBytes",
    "canExecute",
}
SAMPLE_KEYS = {
    "messageId",
    "receivedAt",
    "senderName",
    "senderAddress",
    "subject",
    "sizeEstimateBytes",
    "sourceId",
    "flowId",
    "readState",
    "exclusionReasons",
}
EVENT_KEYS = {
    "revision",
    "type",
    "recordedAt",
    "state",
    "observedMapRevision",
    "observedPolicyRevision",
    "removedCount",
    "remainingCount",
}
MEMBER_KEYS = {
    "messageId",
    "initialState",
    "currentState",
    "receivedAt",
    "sizeEstimateBytes",
    "reasonCodes",
}
ERROR_MESSAGES = {
    "invalid_request": "El pedido no es válido.",
    "invalid_cursor": "El cursor no es válido.",
    "invalid_local_origin": "El origen local no está permitido.",
    "route_not_found": "La ruta solicitada no existe.",
    "target_not_found": "El objetivo no existe en la vista actual.",
    "plan_not_found": "El plan solicitado no existe.",
    "method_not_allowed": "El método no está permitido para esta ruta.",
    "map_revision_conflict": "El mapa cambió. Actualizá la vista antes de reintentar.",
    "policy_revision_conflict": (
        "Las decisiones cambiaron. Actualizá la vista antes de reintentar."
    ),
    "plan_revision_conflict": "El plan cambió. Actualizá la vista antes de reintentar.",
    "command_id_conflict": "El identificador del comando ya fue utilizado.",
    "cursor_stale": "La página cambió. Reiniciá la consulta.",
    "invalid_transition": "La transición solicitada no está permitida.",
    "plan_expired": "El plan venció. Creá uno nuevo.",
    "payload_too_large": "El pedido supera el tamaño permitido.",
    "plan_too_large": "El plan supera el límite de mensajes permitido.",
    "json_required": "Se requiere un cuerpo JSON.",
    "unsupported_target": "El tipo de objetivo no está permitido.",
    "invalid_filter": "El filtro solicitado no es válido.",
    "study_unavailable": "El Estudio de Limpieza no está disponible.",
    "inventory_incomplete": "El inventario todavía no está completo.",
    "account_unavailable": "La cuenta sintética no está disponible.",
    "internal_error": "No se pudo completar la operación.",
}
TARGET_ID_PATTERNS = {
    "source": re.compile(r"^effective-source-v1-[0-9a-f]{24}$"),
    "flow": re.compile(r"^effective-flow-v1-[0-9a-f]{24}$"),
    "sender": re.compile(r"^sender-v1-[0-9a-f]{64}$"),
    "label": re.compile(r"^label-v1-[0-9a-f]{64}$"),
}
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _client(path: Path) -> TestClient:
    return TestClient(create_app(path / "cleanup-plan-api.db", serve_frontend=False))


def _command_id(value: int) -> str:
    return f"{value:08x}-0000-4000-8000-{value:012x}"


def _success(response: Any) -> dict[str, Any]:
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in response.headers
    body = response.json()
    assert body["contractVersion"] == 1
    assert body["dataMode"] == "synthetic"
    assert body["canExecute"] is False
    return body


def _error(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in response.headers
    body = response.json()
    assert set(body) == {*COMMON_KEYS, "error"}
    assert body["contractVersion"] == 1
    assert body["dataMode"] == "synthetic"
    assert body["canExecute"] is False
    assert body["error"] == {"code": code, "message": ERROR_MESSAGES[code]}
    return body


def _context(client: TestClient) -> dict[str, Any]:
    return _success(client.get("/api/v3/study/context", headers=HOST_HEADERS))


def _targets(
    client: TestClient,
    *,
    kind: str | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> dict[str, Any]:
    params: dict[str, object] = {"limit": limit}
    if kind is not None:
        params["kind"] = kind
    if cursor is not None:
        params["cursor"] = cursor
    return _success(client.get("/api/v3/study/targets", headers=HOST_HEADERS, params=params))


def _create_body(
    catalog: dict[str, Any],
    targets: list[dict[str, str]],
    *,
    command: int,
    disposition: str = "archive",
    temporal_filter: dict[str, object] | None = None,
    read_state: str = "any",
    excluded_label_ids: list[str] | None = None,
    keep_latest_per_flow: int = 0,
) -> dict[str, object]:
    return {
        "commandId": _command_id(command),
        "expectedMapRevision": catalog["mapRevision"],
        "expectedPolicyRevision": catalog["policyRevision"],
        "disposition": disposition,
        "targets": targets,
        "temporalFilter": temporal_filter or {"kind": "all"},
        "readState": read_state,
        "excludedLabelIds": excluded_label_ids or [],
        "keepLatestPerFlow": keep_latest_per_flow,
    }


def _post_create(client: TestClient, body: dict[str, object]) -> dict[str, Any]:
    response = _success(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=body)
    )
    assert set(response) == {
        *COMMON_KEYS,
        "status",
        "replayed",
        "commandRevision",
        "planId",
    }
    assert response["status"] == "created"
    assert response["commandRevision"] == 1
    assert response["replayed"] is False
    return response


def _detail(client: TestClient, plan_id: str) -> dict[str, Any]:
    return _success(
        client.get(f"/api/v3/study/plans/{plan_id}", headers=HOST_HEADERS)
    )


def _open_plan(
    client: TestClient,
    *,
    first_command: int = 100,
) -> tuple[dict[str, object], dict[str, Any], dict[str, Any]]:
    catalog = _targets(client)
    selectable = [item for item in catalog["items"] if item["kind"] != "label"]
    assert selectable
    for offset, item in enumerate(selectable):
        body = _create_body(
            catalog,
            [{"kind": item["kind"], "targetId": item["targetId"]}],
            command=first_command + offset,
        )
        receipt = _post_create(client, body)
        detail = _detail(client, receipt["planId"])
        if detail["state"] in {"frozen", "reduced"}:
            return body, receipt, detail
    raise AssertionError("the canonical synthetic fixture must expose an eligible target")


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def _assert_utc_timestamp(value: object) -> None:
    assert isinstance(value, str)
    assert UTC_TIMESTAMP.fullmatch(value)


def _mark_inventory_running(client: TestClient) -> None:
    fixture = canonical_synthetic_map_fixture()
    running = replace(
        fixture.checkpoint,
        scan_id="synthetic-study-running-scan",
        state=SyncState.RUNNING,
        page_token=None,
        history_id="synthetic-study-running-history",
        processed_count=0,
    )
    client.app.state.repository.start_full_index(SYNTHETIC_MAP_ACCOUNT_KEY, running)


def test_v3_registers_exactly_nine_routes_without_effect_routes(tmp_path: Path) -> None:
    client = _client(tmp_path)
    expanded_routes = [
        nested
        for route in client.app.routes
        for nested in (
            getattr(getattr(route, "original_router", None), "routes", None)
            or (route,)
        )
    ]
    actual = {
        (method, route.path)
        for route in expanded_routes
        if str(getattr(route, "path", "")).startswith("/api/v3/study")
        for method in getattr(route, "methods", set())
        if method in {"GET", "POST"}
    }
    assert actual == {
        ("GET", "/api/v3/study/context"),
        ("GET", "/api/v3/study/targets"),
        ("POST", "/api/v3/study/plans"),
        ("GET", "/api/v3/study/plans"),
        ("GET", "/api/v3/study/plans/{planId}"),
        ("GET", "/api/v3/study/plans/{planId}/messages"),
        ("GET", "/api/v3/study/plans/{planId}/events"),
        ("POST", "/api/v3/study/plans/{planId}/revalidate"),
        ("POST", "/api/v3/study/plans/{planId}/cancel"),
    }
    assert all(
        marker not in path.casefold()
        for _method, path in actual
        for marker in ("approve", "execute", "archive", "trash", "unsubscribe", "gmail")
    )

    schema = client.get("/api/openapi.json").json()
    v3_operations = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        if path.startswith("/api/v3/study")
        for method in operations
        if method in {"get", "post"}
    }
    assert v3_operations == actual
    assert client.get("/api/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_validation_and_cursor_objects_redact_identifiers_from_repr_and_str() -> None:
    target_id = "effective-source-v1-" + ("a" * 24)
    request = cleanup_api.SourceTargetRequest(kind="source", targetId=target_id)
    binding = cleanup_api._CursorBinding(
        route="/api/v3/study/plans/cleanup-plan-v1-private/messages",
        filter_value="private-filter",
        limit=1,
        revision="private-revision",
        offset=1,
        listing_as_of=datetime(2026, 8, 29, tzinfo=UTC),
    )

    for rendered in (repr(request), str(request), repr(binding), str(binding)):
        assert "<redacted>" in rendered
        assert target_id not in rendered
        assert "private" not in rendered


def test_cursor_store_is_thread_safe_while_issuing_and_pruning() -> None:
    store = cleanup_api._CursorStore(capacity=4)

    def issue(index: int) -> str:
        return store.issue(
            cleanup_api._CursorBinding(
                route="/api/v3/study/targets",
                filter_value=None,
                limit=1,
                revision="map-v1-test:0",
                offset=index,
            )
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        tokens = tuple(executor.map(issue, range(256)))

    assert len(set(tokens)) == len(tokens)
    assert len(store._items) == 4
    for token, binding in tuple(store._items.items()):
        assert store.resolve(
            token,
            route=binding.route,
            filter_value=binding.filter_value,
            limit=binding.limit,
            revision=binding.revision,
        ) == binding


def test_context_is_exact_dynamic_and_keeps_v2_cleanup_plan_false(tmp_path: Path) -> None:
    client = _client(tmp_path)
    context = _context(client)

    assert set(context) == {
        *COMMON_KEYS,
        "timeZone",
        "planValiditySeconds",
        "limits",
        "capabilities",
        "availability",
    }
    assert context["timeZone"] == "America/Argentina/Cordoba"
    assert context["planValiditySeconds"] == 86_400
    assert context["limits"] == {
        "maxTargets": 100,
        "maxExcludedLabels": 100,
        "maxConsideredMessages": 100_000,
        "maxKeepLatestPerFlow": 10_000,
        "maxMessageSizeEstimateBytes": 2_147_483_647,
        "maxAggregateSizeEstimateBytes": 214_748_364_700_000,
        "maxTargetPageSize": 100,
        "maxPlanPageSize": 100,
        "maxMessagePageSize": 500,
        "maxEventPageSize": 100,
        "maxCursorChars": 1_024,
        "maxQueryStringBytes": 4_096,
        "maxVisibleMetadataBytes": 16_384,
        "maxRequestBodyBytes": 65_536,
        "maxIncludedSamples": 5,
        "maxExcludedSamples": 5,
    }
    assert context["capabilities"] == {
        "studyRead": True,
        "targetRead": True,
        "planCreate": True,
        "planRevalidate": True,
        "planCancel": True,
        "systemLabelFilter": True,
        "customLabelFilter": False,
        "gmailConnection": False,
        "oauth": False,
        "externalNetwork": False,
        "realData": False,
        "messageMutation": False,
        "unsubscribe": False,
        "execute": False,
    }
    availability = context["availability"]
    assert set(availability) == {
        "accountAvailable",
        "inventoryState",
        "completeSnapshotAvailable",
        "currentMapRevision",
        "currentPolicyRevision",
        "targetReadAvailable",
        "planCreateAvailable",
        "planRevalidateAvailable",
        "blockerCodes",
    }
    assert availability["accountAvailable"] is True
    assert availability["inventoryState"] == "completed"
    assert availability["completeSnapshotAvailable"] is True
    assert availability["currentMapRevision"].startswith("map-v1-")
    assert availability["currentPolicyRevision"] == 4
    assert availability["targetReadAvailable"] is True
    assert availability["planCreateAvailable"] is True
    assert availability["planRevalidateAvailable"] is True
    assert availability["blockerCodes"] == []

    v2_response = client.get("/api/v2/context", headers=HOST_HEADERS)
    assert v2_response.status_code == 200
    assert v2_response.headers["cache-control"] == "no-store"
    v2 = v2_response.json()
    assert v2["contractVersion"] == 1
    assert v2["dataMode"] == "synthetic"
    assert v2["capabilities"]["cleanupPlan"] is False


def test_targets_are_closed_ordered_opaque_and_cursor_bound(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    assert set(catalog) == {
        *COMMON_KEYS,
        "mapRevision",
        "policyRevision",
        "kind",
        "items",
        "nextCursor",
    }
    assert catalog["kind"] is None
    assert catalog["items"]
    ranks = {"source": 0, "flow": 1, "sender": 2, "label": 3}
    order = tuple(
        (
            ranks[item["kind"]],
            item.get("displayName", item.get("displayAddress")).casefold(),
            item["targetId"],
        )
        for item in catalog["items"]
    )
    assert order == tuple(sorted(order))

    expected_keys = {
        "source": {"kind", "targetId", "displayName", "messageCount"},
        "flow": {"kind", "targetId", "sourceId", "displayName", "messageCount"},
        "sender": {"kind", "targetId", "displayAddress", "messageCount"},
        "label": {"kind", "targetId", "displayName", "messageCount"},
    }
    for item in catalog["items"]:
        assert set(item) == expected_keys[item["kind"]]
        assert TARGET_ID_PATTERNS[item["kind"]].fullmatch(item["targetId"])
        assert item["messageCount"] > 0
    labels = [item for item in catalog["items"] if item["kind"] == "label"]
    assert {item["displayName"] for item in labels} <= {
        "Recibidos",
        "Principal",
        "Social",
        "Promociones",
        "Actualizaciones",
        "Foros",
    }
    serialized = json.dumps(catalog, ensure_ascii=False, sort_keys=True)
    assert SYNTHETIC_MAP_ACCOUNT_KEY not in serialized
    assert {"accountKey", "providerMessageId", "selector"}.isdisjoint(
        _all_keys(catalog)
    )

    first = _targets(client, limit=1)
    assert len(first["items"]) == 1
    assert first["nextCursor"] is not None
    second = _targets(client, limit=1, cursor=first["nextCursor"])
    assert len(second["items"]) == 1
    assert second["items"][0]["targetId"] != first["items"][0]["targetId"]
    _error(
        client.get(
            "/api/v3/study/targets",
            headers=HOST_HEADERS,
            params={"limit": 2, "cursor": first["nextCursor"]},
        ),
        409,
        "cursor_stale",
    )
    _error(
        client.get(
            "/api/v3/study/targets",
            headers=HOST_HEADERS,
            params={"limit": 1, "kind": "source", "cursor": first["nextCursor"]},
        ),
        409,
        "cursor_stale",
    )
    _error(
        client.get(
            "/api/v3/study/targets",
            headers=HOST_HEADERS,
            params={"cursor": "not-issued"},
        ),
        400,
        "invalid_cursor",
    )
    _error(
        client.get(
            "/api/v3/study/targets",
            headers=HOST_HEADERS,
            params={"cursor": "a" * 1_025},
        ),
        400,
        "invalid_cursor",
    )


def test_create_list_detail_and_member_views_are_exact_and_redacted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    targets = [
        {"kind": item["kind"], "targetId": item["targetId"]}
        for item in catalog["items"]
        if item["kind"] != "label"
    ]
    body = _create_body(
        catalog,
        list(reversed(targets)),
        command=200,
        disposition="trash",
    )
    receipt = _post_create(client, body)
    plan_id = receipt["planId"]

    history = _success(client.get("/api/v3/study/plans", headers=HOST_HEADERS))
    assert set(history) == {
        *COMMON_KEYS,
        "listingAsOf",
        "catalogRevision",
        "state",
        "items",
        "nextCursor",
    }
    assert history["catalogRevision"] == 1
    assert history["state"] is None
    summary = next(item for item in history["items"] if item["planId"] == plan_id)
    assert set(summary) == SUMMARY_KEYS
    assert summary["storageEffect"] == "not_guaranteed"
    assert summary["effectiveFreedBytes"] is None
    assert summary["canExecute"] is False
    _assert_utc_timestamp(summary["createdAt"])
    _assert_utc_timestamp(summary["expiresAt"])

    detail = _detail(client, plan_id)
    assert set(detail) == {
        *COMMON_KEYS,
        *(SUMMARY_KEYS - {"canExecute"}),
        "selection",
        "createdFromMapRevision",
        "createdFromPolicyRevision",
        "currentMapRevision",
        "currentPolicyRevision",
        "includedSamples",
        "excludedSamples",
        "eventCount",
        "recentEvents",
        "warnings",
    }
    assert detail["selection"]["disposition"] == "trash"
    assert {key: detail[key] for key in SUMMARY_KEYS} == summary
    assert set(detail["selection"]) == {
        "disposition",
        "targets",
        "targetSnapshots",
        "temporalFilterRequested",
        "resolvedOnOrAfterUtc",
        "resolvedBeforeUtc",
        "timeZone",
        "readState",
        "excludedLabelIds",
        "excludedLabelSnapshots",
        "keepLatestPerFlow",
    }
    assert detail["selection"]["timeZone"] == "America/Argentina/Cordoba"
    assert detail["selection"]["temporalFilterRequested"] == {"kind": "all"}
    selection_order = tuple(
        (item["kind"], item["targetId"]) for item in detail["selection"]["targets"]
    )
    ranks = {"source": 0, "flow": 1, "sender": 2}
    assert selection_order == tuple(
        sorted(selection_order, key=lambda item: (ranks[item[0]], item[1]))
    )
    assert tuple(
        (item["kind"], item["targetId"])
        for item in detail["selection"]["targetSnapshots"]
    ) == selection_order
    assert all(
        set(item)
        == {
            "source": {"kind", "targetId", "displayName"},
            "flow": {"kind", "targetId", "displayName"},
            "sender": {"kind", "targetId", "displayAddress"},
        }[item["kind"]]
        for item in detail["selection"]["targetSnapshots"]
    )
    assert detail["selection"]["excludedLabelSnapshots"] == []
    assert detail["selectedAtCreationCount"] + detail["excludedAtCreationCount"] == 9
    assert detail["effectiveFreedBytes"] is None
    assert len(detail["includedSamples"]) <= 5
    assert len(detail["excludedSamples"]) <= 5
    assert all(set(sample) == SAMPLE_KEYS for sample in detail["includedSamples"])
    assert all(set(sample) == SAMPLE_KEYS for sample in detail["excludedSamples"])
    assert all(set(event) == EVENT_KEYS for event in detail["recentEvents"])
    assert detail["eventCount"] == 1
    _assert_utc_timestamp(detail["createdAt"])
    _assert_utc_timestamp(detail["expiresAt"])
    for sample in (*detail["includedSamples"], *detail["excludedSamples"]):
        _assert_utc_timestamp(sample["receivedAt"])
    for event in detail["recentEvents"]:
        _assert_utc_timestamp(event["recordedAt"])

    views: dict[str, set[str]] = {}
    member_pages: list[dict[str, Any]] = []
    for state in ("all", "selected", "eligible", "excluded", "removed"):
        page = _success(
            client.get(
                f"/api/v3/study/plans/{plan_id}/messages",
                headers=HOST_HEADERS,
                params={"state": state, "limit": 500},
            )
        )
        assert set(page) == {
            *COMMON_KEYS,
            "planId",
            "planRevision",
            "state",
            "items",
            "nextCursor",
        }
        assert page["state"] == state
        assert all(set(member) == MEMBER_KEYS for member in page["items"])
        member_pages.append(page)
        views[state] = {member["messageId"] for member in page["items"]}
    assert len(views["all"]) == 9
    assert views["all"] == views["selected"] | views["excluded"]
    assert views["selected"].isdisjoint(views["excluded"])
    assert views["eligible"] <= views["selected"]
    assert views["removed"] <= views["selected"]
    assert views["eligible"].isdisjoint(views["removed"])
    assert {"accountKey", "providerMessageId", "threadId"}.isdisjoint(
        _all_keys({"detail": detail, "memberPages": member_pages})
    )
    _error(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": ""},
        ),
        400,
        "invalid_request",
    )

    first = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "all", "limit": 1},
        )
    )
    assert first["nextCursor"] is not None
    second = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "all", "limit": 1, "cursor": first["nextCursor"]},
        )
    )
    assert second["items"][0]["messageId"] != first["items"][0]["messageId"]
    _error(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "selected", "limit": 1, "cursor": first["nextCursor"]},
        ),
        409,
        "cursor_stale",
    )


def test_message_cursor_becomes_stale_after_plan_revision_changes(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    targets = [
        {"kind": item["kind"], "targetId": item["targetId"]}
        for item in catalog["items"]
        if item["kind"] != "label"
    ]
    receipt = _post_create(
        client,
        _create_body(catalog, targets, command=290),
    )
    plan_id = receipt["planId"]
    first = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "all", "limit": 1},
        )
    )
    assert first["nextCursor"] is not None

    detail = _detail(client, plan_id)
    context = _context(client)["availability"]
    _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json={
                "commandId": _command_id(291),
                "expectedPlanRevision": detail["planRevision"],
                "expectedMapRevision": context["currentMapRevision"],
                "expectedPolicyRevision": context["currentPolicyRevision"],
            },
        )
    )
    _error(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={
                "state": "all",
                "limit": 1,
                "cursor": first["nextCursor"],
            },
        ),
        409,
        "cursor_stale",
    )


def test_revalidate_cancel_replay_conflict_and_event_cursor(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_request, receipt, detail = _open_plan(client, first_command=300)
    plan_id = receipt["planId"]
    context = _context(client)["availability"]
    revalidate_body = {
        "commandId": _command_id(380),
        "expectedPlanRevision": detail["planRevision"],
        "expectedMapRevision": context["currentMapRevision"],
        "expectedPolicyRevision": context["currentPolicyRevision"],
    }

    _error(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json={
                **revalidate_body,
                "commandId": _command_id(379),
                "expectedPlanRevision": detail["planRevision"] + 1,
            },
        ),
        409,
        "plan_revision_conflict",
    )

    revalidated = _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json=revalidate_body,
        )
    )
    assert set(revalidated) == {
        *COMMON_KEYS,
        "status",
        "replayed",
        "commandRevision",
        "removedCount",
        "planId",
    }
    assert revalidated["status"] == "revalidated"
    assert revalidated["replayed"] is False
    assert revalidated["removedCount"] == 0
    assert revalidated["commandRevision"] == detail["planRevision"] + 1
    replay = _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json=revalidate_body,
        )
    )
    assert replay == {**revalidated, "replayed": True}

    current = _detail(client, plan_id)
    pre_cancel_events = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1},
        )
    )
    assert pre_cancel_events["nextCursor"] is not None
    conflicting_cancel = {
        "commandId": revalidate_body["commandId"],
        "expectedPlanRevision": current["planRevision"],
    }
    _error(
        client.post(
            f"/api/v3/study/plans/{plan_id}/cancel",
            headers=POST_HEADERS,
            json=conflicting_cancel,
        ),
        409,
        "command_id_conflict",
    )

    cancel_body = {
        "commandId": _command_id(381),
        "expectedPlanRevision": current["planRevision"],
    }
    cancelled = _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/cancel",
            headers=POST_HEADERS,
            json=cancel_body,
        )
    )
    assert set(cancelled) == {
        *COMMON_KEYS,
        "status",
        "replayed",
        "commandRevision",
        "planId",
    }
    assert cancelled["status"] == "cancelled"
    assert cancelled["replayed"] is False
    cancel_replay = _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/cancel",
            headers=POST_HEADERS,
            json=cancel_body,
        )
    )
    assert cancel_replay == {**cancelled, "replayed": True}
    _error(
        client.get(
            f"/api/v3/study/plans/{plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1, "cursor": pre_cancel_events["nextCursor"]},
        ),
        409,
        "cursor_stale",
    )

    _other_request, other_receipt, other_detail = _open_plan(
        client,
        first_command=390,
    )
    _error(
        client.post(
            f"/api/v3/study/plans/{other_receipt['planId']}/cancel",
            headers=POST_HEADERS,
            json={
                "commandId": cancel_body["commandId"],
                "expectedPlanRevision": other_detail["planRevision"],
            },
        ),
        409,
        "command_id_conflict",
    )

    terminal = _detail(client, plan_id)
    assert terminal["state"] == "cancelled"
    invalid_revalidate = {
        **revalidate_body,
        "commandId": _command_id(382),
        "expectedPlanRevision": terminal["planRevision"],
    }
    _error(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json=invalid_revalidate,
        ),
        409,
        "invalid_transition",
    )

    first = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1},
        )
    )
    assert set(first) == {
        *COMMON_KEYS,
        "planId",
        "planRevision",
        "items",
        "nextCursor",
    }
    assert first["items"][0]["type"] == "created"
    assert first["nextCursor"] is not None
    second = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1, "cursor": first["nextCursor"]},
        )
    )
    assert second["items"][0]["type"] == "revalidated"
    assert all(set(event) == EVENT_KEYS for event in (*first["items"], *second["items"]))
    events = _success(
        client.get(f"/api/v3/study/plans/{plan_id}/events", headers=HOST_HEADERS)
    )
    assert [event["type"] for event in events["items"]] == [
        "created",
        "revalidated",
        "cancelled",
    ]


def test_inventory_incomplete_preserves_reads_replay_and_cancel(tmp_path: Path) -> None:
    client = _client(tmp_path)
    create_body, receipt, initial = _open_plan(client, first_command=400)
    plan_id = receipt["planId"]
    _mark_inventory_running(client)

    context = _context(client)
    assert context["availability"] == {
        "accountAvailable": True,
        "inventoryState": "running",
        "completeSnapshotAvailable": False,
        "currentMapRevision": None,
        "currentPolicyRevision": None,
        "targetReadAvailable": False,
        "planCreateAvailable": False,
        "planRevalidateAvailable": False,
        "blockerCodes": ["inventory_incomplete"],
    }
    _error(
        client.get("/api/v3/study/targets", headers=HOST_HEADERS),
        503,
        "inventory_incomplete",
    )

    detail = _detail(client, plan_id)
    assert detail["currentMapRevision"] is None
    assert detail["currentPolicyRevision"] is None
    assert "current_snapshot_unavailable" in detail["warnings"]
    assert _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages", headers=HOST_HEADERS
        )
    )["planRevision"] == initial["planRevision"]
    assert _success(
        client.get(f"/api/v3/study/plans/{plan_id}/events", headers=HOST_HEADERS)
    )["planRevision"] == initial["planRevision"]

    replay = _success(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=create_body)
    )
    assert replay == {**receipt, "replayed": True}
    new_create = {**create_body, "commandId": _command_id(490)}
    _error(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=new_create),
        503,
        "inventory_incomplete",
    )
    revalidate = {
        "commandId": _command_id(491),
        "expectedPlanRevision": initial["planRevision"],
        "expectedMapRevision": create_body["expectedMapRevision"],
        "expectedPolicyRevision": create_body["expectedPolicyRevision"],
    }
    _error(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json=revalidate,
        ),
        503,
        "inventory_incomplete",
    )

    cancel = {
        "commandId": _command_id(492),
        "expectedPlanRevision": initial["planRevision"],
    }
    result = _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/cancel",
            headers=POST_HEADERS,
            json=cancel,
        )
    )
    assert result["status"] == "cancelled"
    assert _detail(client, plan_id)["state"] == "cancelled"


def test_collection_routes_never_reconstruct_full_plan_aggregates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    targets = [
        {"kind": item["kind"], "targetId": item["targetId"]}
        for item in catalog["items"]
        if item["kind"] != "label"
    ]
    receipt = _post_create(
        client,
        _create_body(catalog, targets, command=495),
    )
    plan_id = receipt["planId"]
    detail = _detail(client, plan_id)
    context = _context(client)["availability"]
    _success(
        client.post(
            f"/api/v3/study/plans/{plan_id}/revalidate",
            headers=POST_HEADERS,
            json={
                "commandId": _command_id(1_495),
                "expectedPlanRevision": detail["planRevision"],
                "expectedMapRevision": context["currentMapRevision"],
                "expectedPolicyRevision": context["currentPolicyRevision"],
            },
        )
    )
    _open_plan(client, first_command=1_500)

    def forbidden_full_hydration(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("collection routes must use bounded SQL projections")

    repository = client.app.state.repository
    monkeypatch.setattr(repository, "cleanup_plan_listing_snapshot", forbidden_full_hydration)
    monkeypatch.setattr(repository, "cleanup_plan", forbidden_full_hydration)
    monkeypatch.setattr(repository, "_cleanup_plans_conn", forbidden_full_hydration)
    monkeypatch.setattr(repository, "_cleanup_plan_conn", forbidden_full_hydration)

    plans = _success(
        client.get(
            "/api/v3/study/plans",
            headers=HOST_HEADERS,
            params={"limit": 1},
        )
    )
    messages = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "all", "limit": 1},
        )
    )
    events = _success(
        client.get(
            f"/api/v3/study/plans/{plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1},
        )
    )

    assert len(plans["items"]) == 1
    assert plans["nextCursor"] is not None
    assert len(messages["items"]) == 1
    assert messages["nextCursor"] is not None
    assert len(events["items"]) == 1
    assert events["nextCursor"] is not None


def test_collection_routes_reject_hidden_surplus_rows_with_limit_one(
    tmp_path: Path,
) -> None:
    member_client = _client(tmp_path / "surplus-member")
    _request, member_receipt, _detail_body = _open_plan(
        member_client,
        first_command=1_600,
    )
    member_repository = member_client.app.state.repository
    member_plan = member_repository.cleanup_plan(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        member_receipt["planId"],
    )
    assert member_plan is not None
    oldest_member = min(
        member_plan.members,
        key=lambda item: (item.received_at, item.message_id),
    )
    surplus_member = CleanupPlanMember(
        provider_message_id="synthetic-api-surplus-provider-member",
        message_id="message-v1-" + ("e" * 64),
        initial_state=CleanupMemberInitialState.SELECTED,
        received_at=oldest_member.received_at - timedelta(microseconds=1),
        size_estimate_bytes=oldest_member.size_estimate_bytes,
        source_id=oldest_member.source_id,
        flow_id=oldest_member.flow_id,
        read_state=oldest_member.read_state,
        reason_codes=(),
    )
    with sqlite3.connect(member_repository.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO cleanup_plan_members("
            "account_key, plan_id, provider_message_id, message_id, member_version, "
            "record_version, initial_state, received_at, size_estimate_bytes, "
            "initial_read_state, frozen_source_id, frozen_flow_id) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
            (
                SYNTHETIC_MAP_ACCOUNT_KEY,
                member_plan.plan_id,
                surplus_member.provider_message_id,
                surplus_member.message_id,
                surplus_member.version,
                surplus_member.initial_state.value,
                surplus_member.received_at.isoformat(),
                surplus_member.size_estimate_bytes,
                surplus_member.read_state.value,
                surplus_member.source_id,
                surplus_member.flow_id,
            ),
        )
    _error(
        member_client.get(
            f"/api/v3/study/plans/{member_plan.plan_id}/messages",
            headers=HOST_HEADERS,
            params={"state": "all", "limit": 1},
        ),
        503,
        "study_unavailable",
    )

    event_client = _client(tmp_path / "surplus-event")
    _request, event_receipt, _detail_body = _open_plan(
        event_client,
        first_command=1_700,
    )
    event_repository = event_client.app.state.repository
    event_plan = event_repository.cleanup_plan(
        SYNTHETIC_MAP_ACCOUNT_KEY,
        event_receipt["planId"],
    )
    assert event_plan is not None
    surplus_event = CleanupPlanEvent(
        revision=event_plan.plan_revision + 1,
        type=CleanupEventType.REVALIDATED,
        recorded_at=event_plan.created_at + timedelta(microseconds=1),
        state=event_plan.persisted_state,
        observed_map_revision=event_plan.created_from_map_revision,
        observed_policy_revision=event_plan.created_from_policy_revision,
        removed_count=0,
        remaining_count=event_plan.current_eligible_count,
    )
    with sqlite3.connect(event_repository.path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO cleanup_plan_events("
            "account_key, plan_id, revision, event_version, event_type, state, "
            "recorded_at, observed_map_revision, observed_policy_revision, "
            "removed_count, remaining_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                SYNTHETIC_MAP_ACCOUNT_KEY,
                event_plan.plan_id,
                surplus_event.revision,
                surplus_event.version,
                surplus_event.type.value,
                surplus_event.state.value,
                surplus_event.recorded_at.isoformat(),
                surplus_event.observed_map_revision,
                surplus_event.observed_policy_revision,
                surplus_event.removed_count,
                surplus_event.remaining_count,
            ),
        )
    _error(
        event_client.get(
            f"/api/v3/study/plans/{event_plan.plan_id}/events",
            headers=HOST_HEADERS,
            params={"limit": 1},
        ),
        503,
        "study_unavailable",
    )


def test_plan_catalog_cursor_rejects_mixed_revisions(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    public_target = {"kind": target["kind"], "targetId": target["targetId"]}
    for command in (500, 501):
        _post_create(
            client,
            _create_body(catalog, [public_target], command=command),
        )

    first = _success(
        client.get(
            "/api/v3/study/plans", headers=HOST_HEADERS, params={"limit": 1}
        )
    )
    assert first["catalogRevision"] == 2
    assert first["nextCursor"] is not None
    listing_as_of = first["listingAsOf"]
    clock_reads = 0

    def unexpected_clock() -> datetime:
        nonlocal clock_reads
        clock_reads += 1
        raise AssertionError("a continuation must reuse its bound listingAsOf")

    client.app.state.cleanup_plan_clock = unexpected_clock
    second = _success(
        client.get(
            "/api/v3/study/plans",
            headers=HOST_HEADERS,
            params={"limit": 1, "cursor": first["nextCursor"]},
        )
    )
    assert second["listingAsOf"] == listing_as_of
    assert second["catalogRevision"] == first["catalogRevision"]
    assert clock_reads == 0
    del client.app.state.cleanup_plan_clock

    _post_create(client, _create_body(catalog, [public_target], command=502))
    _error(
        client.get(
            "/api/v3/study/plans",
            headers=HOST_HEADERS,
            params={"limit": 1, "cursor": first["nextCursor"]},
        ),
        409,
        "cursor_stale",
    )


def test_http_boundary_denies_before_domain_and_never_enables_cors(tmp_path: Path) -> None:
    client = _client(tmp_path)

    _error(client.get("/api/v3/study/context"), 403, "invalid_local_origin")
    _error(
        client.get(
            "/api/v3/study/context",
            headers={**HOST_HEADERS, "Origin": "http://localhost:8765"},
        ),
        403,
        "invalid_local_origin",
    )
    _error(
        client.get(
            "/api/v3/study/context",
            headers={**HOST_HEADERS, "Cookie": "ambient=yes"},
        ),
        403,
        "invalid_local_origin",
    )
    _error(
        client.get("/api/v3/study/connect", headers=HOST_HEADERS),
        404,
        "route_not_found",
    )
    _error(
        client.request("PUT", "/api/v3/study/context", headers=HOST_HEADERS),
        405,
        "method_not_allowed",
    )
    _error(
        client.get("/api/v3/study/context?unexpected=1", headers=HOST_HEADERS),
        400,
        "invalid_request",
    )
    _error(
        client.get("/api/v3/study/targets?limit=1&limit=1", headers=HOST_HEADERS),
        400,
        "invalid_request",
    )
    _error(
        client.get(
            "/api/v3/study/targets?cursor=" + "a" * 4_097,
            headers=HOST_HEADERS,
        ),
        400,
        "invalid_request",
    )
    _error(
        client.post("/api/v3/study/plans", headers=HOST_HEADERS, json={}),
        403,
        "invalid_local_origin",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers={**POST_HEADERS, "Content-Type": "text/plain"},
            content="{}",
        ),
        415,
        "json_required",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers={**POST_HEADERS, "Cookie": "ambient=yes"},
            json={},
        ),
        403,
        "invalid_local_origin",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers={**POST_HEADERS, "Content-Type": "application/json"},
            content=b" " * (64 * 1024 + 1),
        ),
        413,
        "payload_too_large",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers={**POST_HEADERS, "Content-Type": "application/json"},
            content=(
                b'{"commandId":"00000001-0000-4000-8000-000000000001",'
                b'"commandId":"00000002-0000-4000-8000-000000000002"}'
            ),
        ),
        400,
        "invalid_request",
    )


def test_closed_requests_conflicts_and_not_found_errors(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    public_target = {"kind": target["kind"], "targetId": target["targetId"]}
    valid = _create_body(catalog, [public_target], command=600)

    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**valid, "accountKey": SYNTHETIC_MAP_ACCOUNT_KEY},
        ),
        400,
        "invalid_request",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**valid, "expectedPolicyRevision": True},
        ),
        400,
        "invalid_request",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**valid, "targets": [public_target, public_target]},
        ),
        400,
        "invalid_request",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={
                **valid,
                "temporalFilter": {
                    "kind": "dateRange",
                    "onOrAfterDate": "2026-08-20",
                    "beforeDate": "2026-08-20",
                },
            },
        ),
        422,
        "invalid_filter",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={
                **valid,
                "targets": [{"kind": "label", "targetId": "label-v1-" + "0" * 64}],
            },
        ),
        422,
        "unsupported_target",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**valid, "expectedMapRevision": "map-v1-" + "0" * 64},
        ),
        409,
        "map_revision_conflict",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**valid, "expectedPolicyRevision": catalog["policyRevision"] + 1},
        ),
        409,
        "policy_revision_conflict",
    )
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={
                **valid,
                "targets": [
                    {
                        "kind": "source",
                        "targetId": "effective-source-v1-" + "0" * 24,
                    }
                ],
            },
        ),
        404,
        "target_not_found",
    )

    missing_plan = "cleanup-plan-v1-00000000-0000-4000-8000-000000000001"
    _error(
        client.get(f"/api/v3/study/plans/{missing_plan}", headers=HOST_HEADERS),
        404,
        "plan_not_found",
    )


@pytest.mark.parametrize(
    "temporal_filter",
    (
        {"kind": "beforeDate", "date": "2026-8-20"},
        {"kind": "beforeDate", "date": "2026-08-20T00:00:00"},
        {"kind": "beforeDate", "date": 0},
        {
            "kind": "dateRange",
            "onOrAfterDate": "2026-8-01",
            "beforeDate": "2026-08-20",
        },
    ),
)
def test_civil_dates_require_exact_ascii_yyyy_mm_dd(
    tmp_path: Path,
    temporal_filter: dict[str, object],
) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    body = _create_body(
        catalog,
        [{"kind": target["kind"], "targetId": target["targetId"]}],
        command=650,
        temporal_filter=temporal_filter,
    )

    _error(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=body),
        422,
        "invalid_filter",
    )


@pytest.mark.parametrize(
    ("temporal_filter", "expected_on_or_after", "expected_before"),
    (
        (
            {"kind": "beforeDate", "date": "2026-08-30"},
            None,
            "2026-08-30T03:00:00Z",
        ),
        (
            {
                "kind": "dateRange",
                "onOrAfterDate": "2026-08-01",
                "beforeDate": "2026-08-30",
            },
            "2026-08-01T03:00:00Z",
            "2026-08-30T03:00:00Z",
        ),
        (
            {"kind": "olderThanDays", "days": 10},
            None,
            "2026-08-19T03:00:00Z",
        ),
    ),
)
def test_temporal_variants_preserve_request_and_resolve_cordoba_midnight(
    tmp_path: Path,
    temporal_filter: dict[str, object],
    expected_on_or_after: str | None,
    expected_before: str | None,
) -> None:
    client = _client(tmp_path)
    client.app.state.cleanup_plan_clock = lambda: datetime(
        2026,
        8,
        29,
        15,
        30,
        tzinfo=UTC,
    )
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    receipt = _post_create(
        client,
        _create_body(
            catalog,
            [{"kind": target["kind"], "targetId": target["targetId"]}],
            command=660,
            temporal_filter=temporal_filter,
        ),
    )

    selection = _detail(client, receipt["planId"])["selection"]
    assert selection["temporalFilterRequested"] == temporal_filter
    assert selection["resolvedOnOrAfterUtc"] == expected_on_or_after
    assert selection["resolvedBeforeUtc"] == expected_before


def test_exact_expiry_maps_to_plan_expired_without_appending_an_event(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created_at = datetime(2026, 8, 29, 15, 30, tzinfo=UTC)
    client.app.state.cleanup_plan_clock = lambda: created_at
    _request, receipt, detail = _open_plan(client, first_command=680)
    plan_id = receipt["planId"]
    client.app.state.cleanup_plan_clock = lambda: created_at + timedelta(days=1)

    _error(
        client.post(
            f"/api/v3/study/plans/{plan_id}/cancel",
            headers=POST_HEADERS,
            json={
                "commandId": _command_id(690),
                "expectedPlanRevision": detail["planRevision"],
            },
        ),
        409,
        "plan_expired",
    )
    expired = _detail(client, plan_id)
    assert expired["state"] == "expired"
    assert expired["planRevision"] == detail["planRevision"]
    assert expired["eventCount"] == detail["eventCount"]


@pytest.mark.parametrize(
    ("error_code", "status"),
    (
        (CleanupPlanErrorCode.PLAN_TOO_LARGE, 413),
        (CleanupPlanErrorCode.STUDY_UNAVAILABLE, 503),
        (CleanupPlanErrorCode.ACCOUNT_UNAVAILABLE, 503),
    ),
)
def test_repository_failures_use_fixed_public_error_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_code: CleanupPlanErrorCode,
    status: int,
) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    body = _create_body(
        catalog,
        [{"kind": target["kind"], "targetId": target["targetId"]}],
        command=695,
    )

    def fail_create(*_args: object, **_kwargs: object) -> None:
        raise CleanupPlanError(error_code)

    monkeypatch.setattr(client.app.state.repository, "create_cleanup_plan", fail_create)
    _error(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=body),
        status,
        error_code.value,
    )


def test_invalid_listing_clock_is_a_fixed_internal_error(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.cleanup_plan_clock = lambda: datetime(2026, 8, 29, 15, 30)
    _error(
        client.get("/api/v3/study/plans", headers=HOST_HEADERS),
        500,
        "internal_error",
    )


def test_unknown_internal_error_code_is_normalized_to_the_closed_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    body = _create_body(
        catalog,
        [{"kind": target["kind"], "targetId": target["targetId"]}],
        command=696,
    )

    def fail_create(*_args: object, **_kwargs: object) -> None:
        raise cleanup_api._PublicApiError("private_internal_detail")

    monkeypatch.setattr(client.app.state.repository, "create_cleanup_plan", fail_create)
    _error(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=body),
        500,
        "internal_error",
    )


def test_command_id_conflicts_across_create_bodies(tmp_path: Path) -> None:
    client = _client(tmp_path)
    catalog = _targets(client)
    target = next(item for item in catalog["items"] if item["kind"] != "label")
    public_target = {"kind": target["kind"], "targetId": target["targetId"]}
    body = _create_body(catalog, [public_target], command=700)
    receipt = _post_create(client, body)

    replay = _success(
        client.post("/api/v3/study/plans", headers=POST_HEADERS, json=body)
    )
    assert replay == {**receipt, "replayed": True}
    _error(
        client.post(
            "/api/v3/study/plans",
            headers=POST_HEADERS,
            json={**body, "disposition": "trash"},
        ),
        409,
        "command_id_conflict",
    )
