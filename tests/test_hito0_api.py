from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mailmap.api import create_app


def client_at(path: Path) -> TestClient:
    return TestClient(create_app(path / "api.db", serve_frontend=False))


def test_navigation_endpoints_expose_only_synthetic_state(tmp_path: Path) -> None:
    client = client_at(tmp_path)

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "synthetic"
    assert health.json()["gmailConnected"] is False

    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["fixtureCoverage"]["missing"] == []
    assert dashboard["totalMessages"] > 0

    sources = client.get("/api/v1/sources").json()
    assert sources
    detail = client.get(f"/api/v1/sources/{sources[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["evidence"]

    configuration = client.get("/api/v1/configuration").json()
    assert configuration["oauthAvailable"] is False
    assert configuration["permanentDelete"] is False
    assert configuration["remoteAi"] is False


def test_filtered_views_are_source_views_not_independent_data(tmp_path: Path) -> None:
    client = client_at(tmp_path)
    all_sources = {item["id"] for item in client.get("/api/v1/sources").json()}
    subscriptions = {
        item["id"]
        for item in client.get("/api/v1/sources", params={"view": "subscriptions"}).json()
    }
    spam = {item["id"] for item in client.get("/api/v1/sources", params={"view": "spam"}).json()}

    assert subscriptions < all_sources
    assert spam < all_sources
    assert subscriptions.isdisjoint(spam)


def test_plan_preview_cannot_execute_and_rejects_unknown_sources(tmp_path: Path) -> None:
    client = client_at(tmp_path)
    response = client.post(
        "/api/v1/plans/preview",
        json={
            "sourceIds": ["src-diario-horizonte"],
            "beforeDate": "2026-12-31",
            "keepLatest": 1,
            "operations": ["archive", "unsubscribe"],
        },
    )
    assert response.status_code == 201
    assert response.json()["canExecute"] is False
    assert response.json()["messageCount"] == 1

    invalid = client.post(
        "/api/v1/plans/preview",
        json={"sourceIds": ["unknown"], "operations": ["trash"]},
    )
    assert invalid.status_code == 422
