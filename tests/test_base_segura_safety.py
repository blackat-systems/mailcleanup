from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from mailmap import main as mailmap_main
from mailmap.api import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PACKAGE = PROJECT_ROOT / "src" / "mailmap"
FORBIDDEN_IMPORT_ROOTS = {
    "google",
    "google_auth_oauthlib",
    "googleapiclient",
    "httpx",
    "requests",
    "socket",
    "urllib",
}
FORBIDDEN_CAPABILITY_MARKERS = {
    "gmail.modify",
    "installedappflow",
    "batchmodify",
    "credentials.json",
    "token.json",
}


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.partition(".")[0])
    return roots


def test_active_package_has_no_external_mail_or_network_clients() -> None:
    findings: list[str] = []
    for path in sorted(ACTIVE_PACKAGE.rglob("*.py")):
        forbidden_imports = _import_roots(path) & FORBIDDEN_IMPORT_ROOTS
        text = path.read_text(encoding="utf-8").casefold()
        forbidden_markers = {marker for marker in FORBIDDEN_CAPABILITY_MARKERS if marker in text}
        if forbidden_imports or forbidden_markers:
            findings.append(
                f"{path.relative_to(PROJECT_ROOT)}: "
                f"imports={sorted(forbidden_imports)}, markers={sorted(forbidden_markers)}"
            )
    assert findings == []


def test_legacy_gmail_package_is_not_in_the_active_tree_or_build_config() -> None:
    assert not (PROJECT_ROOT / "src" / "gmail_cleaner").exists()
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gmail-future" not in pyproject
    assert 'include = ["mailmap*"]' in pyproject


def test_base_segura_api_exposes_no_connection_or_execution_routes(tmp_path: Path) -> None:
    app = create_app(tmp_path / "safety.db", serve_frontend=False)
    routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    post_routes = {path for method, path in routes if method == "POST"}
    assert post_routes == {
        "/api/v1/plans/preview",
        "/api/v1/plans/{plan_id}/revalidate",
    }
    assert all(
        blocked not in path.casefold()
        for _method, path in routes
        for blocked in ("oauth", "gmail", "execute", "disconnect")
    )


def test_server_entrypoint_is_fixed_to_loopback(monkeypatch: Any) -> None:
    invocation: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        invocation.update({"app": app, **kwargs})

    monkeypatch.setattr(mailmap_main.uvicorn, "run", fake_run)
    mailmap_main.run()

    assert invocation == {
        "app": "mailmap.api:app",
        "host": "127.0.0.1",
        "port": 8765,
        "reload": False,
    }
