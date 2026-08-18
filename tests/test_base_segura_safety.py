from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from mailmap import main as mailmap_main
from mailmap.api import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PACKAGE = PROJECT_ROOT / "src" / "mailmap"
OAUTH_SESSION_PATH = ACTIVE_PACKAGE / "oauth_session.py"
SESSION_MODEL_PATH = ACTIVE_PACKAGE / "session_model.py"
WINDOWS_SECRET_STORE_PATH = ACTIVE_PACKAGE / "windows_secret_store.py"
GMAIL_READONLY_POLICY_PATH = ACTIVE_PACKAGE / "gmail_readonly_policy.py"
SAFE_STDLIB_URL_IMPORT_ALLOWLIST = {
    OAUTH_SESSION_PATH: {"urllib.parse"},
    GMAIL_READONLY_POLICY_PATH: {"urllib.parse"},
}
FORBIDDEN_IMPORT_PREFIXES = {
    "google",
    "google_auth_oauthlib",
    "googleapiclient",
    "http.client",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "webbrowser",
}
FORBIDDEN_CAPABILITY_MARKERS = {
    "gmail.readonly",
    "gmail.modify",
    "gmail.compose",
    "gmail.send",
    "gmail.settings.",
    "https://mail.google.com/",
    "installedappflow",
    "batchmodify",
    "batchdelete",
    "users.messages.modify",
    "users.messages.trash",
    "users.messages.untrash",
    "credentials.json",
    "token.json",
}
SENSITIVE_VALUE_MARKERS = {
    "-----begin " + "private key-----",
    "ya" + "29.",
    "ai" + "za",
}
PACKAGED_FORBIDDEN_SUFFIXES = {
    ".credential",
    ".db",
    ".json",
    ".pem",
    ".sqlite",
    ".sqlite3",
    ".tmp",
}
EMAIL_LITERAL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+")


def _import_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _matches_forbidden_import(module: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def test_active_package_has_no_external_mail_or_network_clients() -> None:
    findings: list[str] = []
    for path in sorted(ACTIVE_PACKAGE.rglob("*.py")):
        allowed_imports = SAFE_STDLIB_URL_IMPORT_ALLOWLIST.get(path, set())
        forbidden_imports = {
            module
            for module in _import_modules(path)
            if _matches_forbidden_import(module) and module not in allowed_imports
        }
        text = path.read_text(encoding="utf-8").casefold()
        forbidden_markers = {marker for marker in FORBIDDEN_CAPABILITY_MARKERS if marker in text}
        if forbidden_imports or forbidden_markers:
            findings.append(
                f"{path.relative_to(PROJECT_ROOT)}: "
                f"imports={sorted(forbidden_imports)}, markers={sorted(forbidden_markers)}"
            )
    assert findings == []


def test_no_shippable_code_contains_write_scopes_routes_or_credential_files() -> None:
    inspected = [
        *sorted(ACTIVE_PACKAGE.rglob("*.py")),
        *sorted((PROJECT_ROOT / "frontend" / "src").rglob("*")),
        *sorted((PROJECT_ROOT / "scripts").rglob("*.ps1")),
        PROJECT_ROOT / "pyproject.toml",
    ]
    findings: list[str] = []
    for path in inspected:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").casefold()
        markers = {marker for marker in FORBIDDEN_CAPABILITY_MARKERS if marker in text}
        if markers:
            findings.append(f"{path.relative_to(PROJECT_ROOT)}: {sorted(markers)}")
    assert findings == []


def test_d2_allowlist_is_exact_and_contains_no_real_transport_or_browser() -> None:
    assert {
        OAUTH_SESSION_PATH: {"urllib.parse"},
        GMAIL_READONLY_POLICY_PATH: {"urllib.parse"},
    } == SAFE_STDLIB_URL_IMPORT_ALLOWLIST
    oauth_imports = _import_modules(OAUTH_SESSION_PATH)
    assert "urllib.parse" in oauth_imports
    assert all(
        not _matches_forbidden_import(module) or module == "urllib.parse"
        for module in oauth_imports
    )
    oauth_text = OAUTH_SESSION_PATH.read_text(encoding="utf-8").casefold()
    assert all(
        marker not in oauth_text
        for marker in (
            "class googleoauth",
            "class realoauth",
            "socket.",
            "urlopen(",
            "webbrowser.",
            "requests.",
            "httpx.",
        )
    )


def test_metadata_scope_and_dpapi_are_confined_to_exact_d2_files() -> None:
    metadata_files: list[Path] = []
    dpapi_files: list[Path] = []
    for path in sorted(ACTIVE_PACKAGE.rglob("*.py")):
        text = path.read_text(encoding="utf-8").casefold()
        if "gmail.metadata" in text:
            metadata_files.append(path)
        if "cryptprotectdata" in text or "cryptunprotectdata" in text:
            dpapi_files.append(path)
    assert metadata_files == [SESSION_MODEL_PATH]
    assert dpapi_files == [WINDOWS_SECRET_STORE_PATH]


def test_packaged_files_and_tests_have_no_private_addresses_or_secret_shapes() -> None:
    inspected = [
        *sorted(ACTIVE_PACKAGE.rglob("*")),
        *sorted((PROJECT_ROOT / "tests").rglob("*.py")),
    ]
    findings: list[str] = []
    for path in inspected:
        if not path.is_file():
            continue
        if (
            path.is_relative_to(ACTIVE_PACKAGE)
            and path.suffix.casefold() in PACKAGED_FORBIDDEN_SUFFIXES
        ):
            findings.append(f"packaged artifact: {path.relative_to(PROJECT_ROOT)}")
            continue
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        sensitive = {marker for marker in SENSITIVE_VALUE_MARKERS if marker in lowered}
        private_addresses = {
            match.group(0)
            for match in EMAIL_LITERAL.finditer(text)
            if not match.group(0).casefold().endswith(".example")
        }
        if sensitive or private_addresses:
            findings.append(
                f"{path.relative_to(PROJECT_ROOT)}: "
                f"sensitive={sorted(sensitive)}, addresses={sorted(private_addresses)}"
            )
    assert findings == []


def test_legacy_gmail_package_is_not_in_the_active_tree_or_build_config() -> None:
    assert not (PROJECT_ROOT / "src" / "gmail_cleaner").exists()
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gmail-future" not in pyproject
    assert 'include = ["mailmap*"]' in pyproject


def test_base_segura_api_exposes_no_connection_or_execution_routes(tmp_path: Path) -> None:
    app = create_app(tmp_path / "safety.db", serve_frontend=False)
    assert app.state.service.configuration()["oauthAvailable"] is False
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
