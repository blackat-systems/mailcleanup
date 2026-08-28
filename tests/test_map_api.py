from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mailmap.api import create_app
from mailmap.map_synthetic_gate import SYNTHETIC_MAP_ACCOUNT_KEY

HOST_HEADERS = {"Host": "127.0.0.1:8765"}
POST_HEADERS = {
    **HOST_HEADERS,
    "Origin": "http://127.0.0.1:8765",
}


def _client(path: Path, *, serve_frontend: bool = False) -> TestClient:
    return TestClient(create_app(path / "map-api.db", serve_frontend=serve_frontend))


def _map(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/v2/map", headers=HOST_HEADERS)
    assert response.status_code == 200
    return response.json()


def _new_source_decision(client: TestClient) -> dict[str, object]:
    projection = _map(client)
    history = client.get("/api/v2/decisions", headers=HOST_HEADERS).json()
    previously_observed = {
        event.get("sourceId")
        for event in history["events"]
        if event.get("sourceId") is not None
    }
    source_id = next(
        source["id"]
        for source in projection["sources"]
        if source["id"] not in previously_observed
        and not source["decisionIds"]
        and not source["structuralDecisionIds"]
    )
    return {
        "commandId": "11111111-1111-4111-8111-111111111111",
        "decisionId": "22222222-2222-4222-8222-222222222222",
        "occurredAt": "2026-08-27T22:00:00Z",
        "expectedMapRevision": projection["mapRevision"],
        "expectedPolicyRevision": projection["policyRevision"],
        "type": "setSourceDisplayName",
        "sourceId": source_id,
        "displayName": "Fuente elegida por Joa",
    }


def test_v2_context_is_local_closed_and_v1_remains_compatible(tmp_path: Path) -> None:
    client = _client(tmp_path)

    rejected = client.get("/api/v2/context")
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "invalid_local_origin"

    response = client.get("/api/v2/context", headers=HOST_HEADERS)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in response.headers
    assert response.json() == {
        "contractVersion": 1,
        "dataMode": "synthetic",
        "appVersion": "0.1.0",
        "account": {"state": "synthetic", "displayAddress": None},
        "capabilities": {
            "mapRead": True,
            "policyWrite": True,
            "policyUndo": True,
            "gmailConnection": False,
            "oauth": False,
            "externalNetwork": False,
            "realData": False,
            "syncControl": False,
            "cleanupPlan": False,
            "messageMutation": False,
            "unsubscribe": False,
            "execute": False,
        },
    }

    v1 = client.get("/api/v1/health")
    assert v1.status_code == 200
    assert v1.json()["gmailConnected"] is False
    assert client.get("/api/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/api/openapi.json").status_code == 200


def test_v2_rejects_wrong_origin_queries_and_unknown_routes_before_domain(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, serve_frontend=True)

    wrong_origin = client.get(
        "/api/v2/map",
        headers={**HOST_HEADERS, "Origin": "http://localhost:8765"},
    )
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["error"]["code"] == "invalid_local_origin"

    query = client.get("/api/v2/map?unexpected=1", headers=HOST_HEADERS)
    assert query.status_code == 400
    assert query.json()["error"]["code"] == "invalid_request"

    unknown = client.get("/api/v2/connect", headers=HOST_HEADERS)
    assert unknown.status_code == 400
    assert unknown.headers["content-type"].startswith("application/json")
    assert unknown.json()["error"]["code"] == "invalid_request"

    namespace_root = client.get("/api/v2", headers=HOST_HEADERS)
    assert namespace_root.status_code == 400
    assert namespace_root.headers["content-type"].startswith("application/json")
    assert namespace_root.json()["error"]["code"] == "invalid_request"

    unsupported_method = client.request("TRACE", "/api/v2/map", headers=HOST_HEADERS)
    assert unsupported_method.status_code == 400
    assert unsupported_method.json()["error"]["code"] == "invalid_request"


def test_every_synthetic_v2_claim_is_blocked_if_the_database_gate_changes(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    repository = client.app.state.repository
    snapshot = repository.map_input_snapshot(SYNTHETIC_MAP_ACCOUNT_KEY)
    assert snapshot.checkpoint is not None
    other_account = "unexpected-synthetic-v1"
    repository.save_index_page(
        other_account,
        (
            replace(
                snapshot.records[0],
                account_key=other_account,
                provider_message_id="unexpected-message-v1",
            ),
        ),
        replace(
            snapshot.checkpoint,
            account_key=other_account,
            scan_id="unexpected-scan-v1",
            history_id="unexpected-history-v1",
            processed_count=1,
        ),
    )

    for path in (
        "/api/v2/context",
        "/api/v2/connection",
        "/api/v2/sync",
        "/api/v2/index",
        "/api/v2/map",
        "/api/v2/decisions",
    ):
        response = client.get(path, headers=HOST_HEADERS)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "map_unavailable"
    assert client.get("/api/v1/health").status_code == 200

    reopened = _client(tmp_path)
    assert reopened.get("/api/v1/health").status_code == 200
    unavailable = reopened.get("/api/v2/map", headers=HOST_HEADERS)
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "map_unavailable"


def test_map_index_sync_and_detail_expose_only_the_public_allowlist(tmp_path: Path) -> None:
    client = _client(tmp_path)
    projection = _map(client)

    assert projection["contractVersion"] == 1
    assert projection["dataMode"] == "synthetic"
    assert projection["sync"]["state"] == "completed"
    assert projection["sync"]["partial"] is False
    assert projection["summary"]["messageCount"] > 0
    assert projection["sources"]

    index = client.get("/api/v2/index", headers=HOST_HEADERS)
    sync = client.get("/api/v2/sync", headers=HOST_HEADERS)
    connection = client.get("/api/v2/connection", headers=HOST_HEADERS)
    assert index.status_code == sync.status_code == connection.status_code == 200
    assert index.json()["canDelete"] is False
    assert connection.json()["displayAddress"] is None
    assert sync.json()["partial"] is False

    source_id = projection["sources"][0]["id"]
    detail = client.get(f"/api/v2/map/sources/{source_id}", headers=HOST_HEADERS)
    assert detail.status_code == 200
    assert detail.json()["contractVersion"] == 1
    assert len(detail.json()["recentMessages"]) <= 5

    serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True)
    snapshot = client.app.state.repository.map_input_snapshot(
        SYNTHETIC_MAP_ACCOUNT_KEY
    )
    assert SYNTHETIC_MAP_ACCOUNT_KEY not in serialized
    assert all(record.provider_message_id not in serialized for record in snapshot.records)
    for forbidden in (
        "candidateCount",
        "recommendation",
        "recoverableBytes",
        "canExecute",
        "snippet",
        "mime",
        "bodyHtml",
        "attachments",
        "recipients",
    ):
        assert forbidden not in serialized


def test_post_boundary_rejects_ambient_or_ambiguous_requests(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _new_source_decision(client)

    no_origin = client.post("/api/v2/decisions", headers=HOST_HEADERS, json=body)
    assert no_origin.status_code == 403

    wrong_type = client.post(
        "/api/v2/decisions",
        headers={**POST_HEADERS, "Content-Type": "text/plain"},
        content=json.dumps(body),
    )
    assert wrong_type.status_code == 415
    assert wrong_type.json()["error"]["code"] == "json_required"

    with_cookie = client.post(
        "/api/v2/decisions",
        headers={**POST_HEADERS, "Cookie": "ambient=yes"},
        json=body,
    )
    assert with_cookie.status_code == 403

    oversized = client.post(
        "/api/v2/decisions",
        headers={**POST_HEADERS, "Content-Type": "application/json"},
        content=b" " * (64 * 1024 + 1),
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "payload_too_large"

    duplicate = client.post(
        "/api/v2/decisions",
        headers={**POST_HEADERS, "Content-Type": "application/json"},
        content=b'{"type":"protectTarget","type":"setSourceRubro"}',
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["code"] == "invalid_request"

    deeply_nested = client.post(
        "/api/v2/decisions",
        headers={**POST_HEADERS, "Content-Type": "application/json"},
        content=b'{"unexpected":' + b"[" * 2_000 + b"0" + b"]" * 2_000 + b"}",
    )
    assert deeply_nested.status_code == 400
    assert deeply_nested.json()["error"]["code"] == "invalid_request"

    coerced_revision = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "expectedPolicyRevision": str(body["expectedPolicyRevision"])},
    )
    assert coerced_revision.status_code == 400
    assert coerced_revision.json()["error"]["code"] == "invalid_request"

    numeric_datetime = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "occurredAt": 1_788_040_800},
    )
    assert numeric_datetime.status_code == 400
    assert numeric_datetime.json()["error"]["code"] == "invalid_request"

    snake_case = dict(body)
    snake_case["command_id"] = snake_case.pop("commandId")
    snake_case_request = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json=snake_case,
    )
    assert snake_case_request.status_code == 400
    assert snake_case_request.json()["error"]["code"] == "invalid_request"

    self_supersession = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "supersedesDecisionIds": [body["decisionId"]]},
    )
    assert self_supersession.status_code == 400
    assert self_supersession.json()["error"]["code"] == "invalid_request"

    extra = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "accountKey": "synthetic-map-v1"},
    )
    assert extra.status_code == 400
    assert "accountKey" not in extra.text


def test_policy_write_is_cas_idempotent_and_undo_is_append_only(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _new_source_decision(client)

    applied = client.post("/api/v2/decisions", headers=POST_HEADERS, json=body)
    assert applied.status_code == 200
    assert applied.json()["replayed"] is False
    assert applied.json()["bindingStatus"] == "EXACT"
    assert applied.json()["policyRevision"] == int(body["expectedPolicyRevision"]) + 1

    replay = client.post("/api/v2/decisions", headers=POST_HEADERS, json=body)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True

    collision = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "displayName": "Otro nombre"},
    )
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "command_id_conflict"

    current = _map(client)
    undo_body = {
        "commandId": "33333333-3333-4333-8333-333333333333",
        "occurredAt": "2026-08-27T22:01:00Z",
        "expectedMapRevision": current["mapRevision"],
        "expectedPolicyRevision": current["policyRevision"],
    }
    decision_id = str(body["decisionId"])
    undone = client.post(
        f"/api/v2/decisions/{decision_id}/undo",
        headers=POST_HEADERS,
        json=undo_body,
    )
    assert undone.status_code == 200
    assert undone.json()["bindingStatus"] is None

    replay_after_undo = client.post(
        "/api/v2/decisions", headers=POST_HEADERS, json=body
    )
    assert replay_after_undo.status_code == 200
    assert replay_after_undo.json()["replayed"] is True

    history = client.get("/api/v2/decisions", headers=HOST_HEADERS)
    assert history.status_code == 200
    assert history.json()["policyRevision"] == int(body["expectedPolicyRevision"]) + 2
    assert history.json()["events"][-1]["type"] == "undoPolicy"
    assert history.json()["events"][-1]["targetDecisionId"] == decision_id
    assert history.json()["events"][-2]["active"] is False


def test_stale_revision_and_missing_undo_target_are_closed_errors(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body = _new_source_decision(client)
    stale = client.post(
        "/api/v2/decisions",
        headers=POST_HEADERS,
        json={**body, "expectedMapRevision": "map-v1-" + "0" * 64},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "map_revision_conflict"

    projection = _map(client)
    missing = client.post(
        "/api/v2/decisions/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/undo",
        headers=POST_HEADERS,
        json={
            "commandId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "occurredAt": "2026-08-27T22:02:00Z",
            "expectedMapRevision": projection["mapRevision"],
            "expectedPolicyRevision": projection["policyRevision"],
        },
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "decision_not_found"


def test_partition_command_resolves_public_flow_ids_server_side(tmp_path: Path) -> None:
    client = _client(tmp_path)
    projection = _map(client)
    source = next(item for item in projection["sources"] if len(item["flows"]) >= 2)
    body = {
        "commandId": "44444444-4444-4444-8444-444444444444",
        "decisionId": "55555555-5555-4555-8555-555555555555",
        "occurredAt": "2026-08-27T22:03:00Z",
        "expectedMapRevision": projection["mapRevision"],
        "expectedPolicyRevision": projection["policyRevision"],
        "type": "partitionSource",
        "sourceId": source["id"],
        "groups": [
            {"anchors": [{"kind": "flow", "flowId": flow["id"]}]}
            for flow in source["flows"]
        ],
    }

    response = client.post("/api/v2/decisions", headers=POST_HEADERS, json=body)
    assert response.status_code == 200
    assert response.json()["bindingStatus"] == "EXACT"
    assert "selector" not in response.text.casefold()
    assert "account_key" not in response.text.casefold()


@pytest.mark.parametrize(
    ("command_type", "specific"),
    [
        ("setSourceRubro", {"rubro": "Finanzas"}),
        ("setFlowDisplayName", {"displayName": "Flujo elegido"}),
        ("setFlowIntention", {"intention": "Notificación"}),
        ("mergeSources", {}),
    ],
)
def test_each_correction_shape_resolves_only_public_ids(
    tmp_path: Path,
    command_type: str,
    specific: dict[str, object],
) -> None:
    client = _client(tmp_path / command_type)
    projection = _map(client)
    available = [
        source
        for source in projection["sources"]
        if not source["decisionIds"] and not source["structuralDecisionIds"]
    ]
    common: dict[str, object] = {
        "commandId": "66666666-6666-4666-8666-666666666666",
        "decisionId": "77777777-7777-4777-8777-777777777777",
        "occurredAt": "2026-08-27T22:04:00Z",
        "expectedMapRevision": projection["mapRevision"],
        "expectedPolicyRevision": projection["policyRevision"],
        "type": command_type,
    }
    if command_type == "mergeSources":
        common["sourceIds"] = sorted(source["id"] for source in available[:2])
    elif command_type.startswith("setFlow"):
        common["flowId"] = available[0]["flows"][0]["id"]
    else:
        common["sourceId"] = available[0]["id"]
    body = {**common, **specific}

    response = client.post("/api/v2/decisions", headers=POST_HEADERS, json=body)
    assert response.status_code == 200
    assert response.json()["replayed"] is False
    assert "accountKey" not in response.text
    assert "selector" not in response.text.casefold()


def test_merge_rejects_an_already_effective_merge_as_an_unsupported_target(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    initial = _map(client)
    automatic_sources = [
        source
        for source in initial["sources"]
        if len(source["automaticSourceIds"]) == 1
        and not source["decisionIds"]
        and not source["structuralDecisionIds"]
    ]
    assert len(automatic_sources) >= 3
    first = {
        "commandId": "aaaaaaaa-1111-4111-8111-111111111111",
        "decisionId": "bbbbbbbb-2222-4222-8222-222222222222",
        "occurredAt": "2026-08-27T22:06:00Z",
        "expectedMapRevision": initial["mapRevision"],
        "expectedPolicyRevision": initial["policyRevision"],
        "type": "mergeSources",
        "sourceIds": sorted(source["id"] for source in automatic_sources[:2]),
    }
    assert client.post("/api/v2/decisions", headers=POST_HEADERS, json=first).status_code == 200

    current = _map(client)
    merged = next(source for source in current["sources"] if len(source["automaticSourceIds"]) > 1)
    remaining = next(
        source for source in current["sources"] if len(source["automaticSourceIds"]) == 1
    )
    second = {
        "commandId": "cccccccc-3333-4333-8333-333333333333",
        "decisionId": "dddddddd-4444-4444-8444-444444444444",
        "occurredAt": "2026-08-27T22:07:00Z",
        "expectedMapRevision": current["mapRevision"],
        "expectedPolicyRevision": current["policyRevision"],
        "type": "mergeSources",
        "sourceIds": sorted((merged["id"], remaining["id"])),
    }
    rejected = client.post("/api/v2/decisions", headers=POST_HEADERS, json=second)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "unsupported_target"


@pytest.mark.parametrize("target_kind", ["source", "flow", "message", "sender", "label"])
def test_each_protection_target_is_resolved_server_side(
    tmp_path: Path, target_kind: str
) -> None:
    client = _client(tmp_path / target_kind)
    projection = _map(client)
    source = next(item for item in projection["sources"] if item["senders"])
    detail = client.get(
        f"/api/v2/map/sources/{source['id']}", headers=HOST_HEADERS
    ).json()
    message = detail["recentMessages"][0]
    targets: dict[str, dict[str, str]] = {
        "source": {"kind": "source", "sourceId": source["id"]},
        "flow": {"kind": "flow", "flowId": source["flows"][0]["id"]},
        "message": {"kind": "message", "messageId": message["id"]},
        "sender": {"kind": "sender", "senderAddress": source["senders"][0]},
        "label": {"kind": "label", "labelId": message["labelIds"][0]},
    }
    body = {
        "commandId": "88888888-8888-4888-8888-888888888888",
        "decisionId": "99999999-9999-4999-8999-999999999999",
        "occurredAt": "2026-08-27T22:05:00Z",
        "expectedMapRevision": projection["mapRevision"],
        "expectedPolicyRevision": projection["policyRevision"],
        "type": "protectTarget",
        "target": targets[target_kind],
    }

    response = client.post("/api/v2/decisions", headers=POST_HEADERS, json=body)
    assert response.status_code == 200
    assert response.json()["bindingStatus"] == "EXACT"
