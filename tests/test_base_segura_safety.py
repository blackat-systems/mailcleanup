from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from mailmap import main as mailmap_main
from mailmap.api import create_app
from mailmap.model import Confianza, Intencion, Rubro, Suscripcion

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PACKAGE = PROJECT_ROOT / "src" / "mailmap"
OAUTH_SESSION_PATH = ACTIVE_PACKAGE / "oauth_session.py"
SESSION_MODEL_PATH = ACTIVE_PACKAGE / "session_model.py"
WINDOWS_SECRET_STORE_PATH = ACTIVE_PACKAGE / "windows_secret_store.py"
GMAIL_READONLY_POLICY_PATH = ACTIVE_PACKAGE / "gmail_readonly_policy.py"
GMAIL_INVENTORY_MODEL_PATH = ACTIVE_PACKAGE / "gmail_inventory_model.py"
GMAIL_INVENTORY_PATH = ACTIVE_PACKAGE / "gmail_inventory.py"
CLASSIFICATION_MODEL_PATH = ACTIVE_PACKAGE / "classification_model.py"
CLASSIFICATION_DOMAIN_PATH = ACTIVE_PACKAGE / "classification_domain.py"
POLICY_MODEL_PATH = ACTIVE_PACKAGE / "policy_model.py"
POLICY_DOMAIN_PATH = ACTIVE_PACKAGE / "policy_domain.py"
REPOSITORY_PATH = ACTIVE_PACKAGE / "repository.py"
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
D4_FORBIDDEN_IMPORT_PREFIXES = {
    *FORBIDDEN_IMPORT_PREFIXES,
    "anthropic",
    "logging",
    "openai",
    "os",
    "pathlib",
    "playwright",
    "random",
    "selenium",
    "sqlite3",
    "time",
}
D4_FORBIDDEN_FIELD_MARKERS = {
    "brand" + "_hint",
    "rubro" + "_hint",
    "flow" + "_hint",
    "personal" + "_signal",
    "fixture" + "_tags",
}
D4_IMPORT_ALLOWLIST = {
    CLASSIFICATION_MODEL_PATH: {
        "__future__",
        "dataclasses",
        "enum",
        "mailmap.model",
        "re",
    },
    CLASSIFICATION_DOMAIN_PATH: {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "hashlib",
        "mailmap.classification_model",
        "mailmap.index_model",
        "mailmap.model",
        "re",
        "unicodedata",
    },
}
D5_IMPORT_ALLOWLIST = {
    POLICY_MODEL_PATH: {
        "__future__",
        "dataclasses",
        "datetime",
        "enum",
        "mailmap.classification_model",
        "mailmap.model",
        "re",
        "typing",
    },
    POLICY_DOMAIN_PATH: {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "hashlib",
        "mailmap.classification_model",
        "mailmap.index_model",
        "mailmap.model",
        "mailmap.policy_model",
    },
}


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


def test_d3_inventory_has_no_external_transport_network_browser_or_scope_literal() -> None:
    for path in (GMAIL_INVENTORY_MODEL_PATH, GMAIL_INVENTORY_PATH):
        imports = _import_modules(path)
        assert all(not _matches_forbidden_import(module) for module in imports)
        text = path.read_text(encoding="utf-8").casefold()
        assert "gmail.metadata" not in text
        assert all(
            marker not in text
            for marker in (
                "socket.",
                "urlopen(",
                "webbrowser.",
                "requests.",
                "httpx.",
                "googleapiclient",
                "installedappflow",
            )
        )


def test_d4_classification_is_local_closed_and_has_no_product_consumer() -> None:
    for path in (CLASSIFICATION_MODEL_PATH, CLASSIFICATION_DOMAIN_PATH):
        imports = _import_modules(path)
        assert imports == D4_IMPORT_ALLOWLIST[path]
        assert all(
            not any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in D4_FORBIDDEN_IMPORT_PREFIXES
            )
            for module in imports
        )
        text = path.read_text(encoding="utf-8").casefold()
        assert all(marker not in text for marker in D4_FORBIDDEN_FIELD_MARKERS)
        assert all(
            marker not in text
            for marker in (
                "fastapi",
                "apirouter",
                "urlopen(",
                "webbrowser.",
                "socket.",
                "requests.",
                "httpx.",
                "print(",
                "basicconfig(",
            )
        )

    consumer_findings: list[str] = []
    for path in sorted(ACTIVE_PACKAGE.rglob("*.py")):
        if path in (
            CLASSIFICATION_MODEL_PATH,
            CLASSIFICATION_DOMAIN_PATH,
            POLICY_MODEL_PATH,
            POLICY_DOMAIN_PATH,
        ):
            continue
        text = path.read_text(encoding="utf-8").casefold()
        if any(
            marker in text
            for marker in (
                "classification_domain",
                "classification_model",
                "classify_indexed_records",
            )
        ):
            consumer_findings.append(str(path.relative_to(PROJECT_ROOT)))
    assert consumer_findings == []


def test_d5_policy_memory_is_local_closed_and_has_only_authorized_consumers() -> None:
    for path in (POLICY_MODEL_PATH, POLICY_DOMAIN_PATH):
        imports = _import_modules(path)
        assert imports == D5_IMPORT_ALLOWLIST[path]
        assert "mailmap.classification_domain" not in imports
        assert all(
            not any(
                module == prefix or module.startswith(f"{prefix}.")
                for prefix in D4_FORBIDDEN_IMPORT_PREFIXES
            )
            for module in imports
        )
        lowered = path.read_text(encoding="utf-8").casefold()
        assert all(marker not in lowered for marker in D4_FORBIDDEN_FIELD_MARKERS)
        assert all(
            marker not in lowered
            for marker in (
                "fastapi",
                "apirouter",
                "classify_indexed_records",
                "urlopen(",
                "webbrowser.",
                "socket.",
                "requests.",
                "httpx.",
                "print(",
                "basicconfig(",
                "payload_json",
                "credentials.json",
                "token.json",
            )
        )

    repository_imports = _import_modules(REPOSITORY_PATH)
    assert "mailmap.policy_model" in repository_imports
    assert "mailmap.policy_domain" not in repository_imports
    assert "mailmap.classification_model" not in repository_imports
    assert "mailmap.classification_domain" not in repository_imports

    policy_model_consumers: list[Path] = []
    policy_domain_consumers: list[Path] = []
    for path in sorted(ACTIVE_PACKAGE.rglob("*.py")):
        if path in (POLICY_MODEL_PATH, POLICY_DOMAIN_PATH):
            continue
        imports = _import_modules(path)
        if "mailmap.policy_model" in imports:
            policy_model_consumers.append(path)
        if "mailmap.policy_domain" in imports:
            policy_domain_consumers.append(path)
    assert policy_model_consumers == [REPOSITORY_PATH]
    assert policy_domain_consumers == []

    repository_tree = ast.parse(
        REPOSITORY_PATH.read_text(encoding="utf-8"), filename=str(REPOSITORY_PATH)
    )
    d5_writers = {
        node.name: ast.unparse(node)
        for node in ast.walk(repository_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"record_policy", "undo_policy"}
    }
    assert set(d5_writers) == {"record_policy", "undo_policy"}
    assert all("_ensure_index_account" not in source for source in d5_writers.values())


def test_d4_does_not_expand_shared_taxonomies() -> None:
    assert tuple((item.name, item.value) for item in Rubro) == (
        ("MEDIOS", "Medios y contenido"),
        ("SOFTWARE", "Software y servicios digitales"),
        ("COMERCIO", "Comercio y compras"),
        ("FINANZAS", "Finanzas"),
        ("TRABAJO", "Trabajo y educación"),
        ("SALUD", "Salud y gobierno"),
        ("VIAJES", "Viajes y entretenimiento"),
        ("SOCIAL", "Social y comunidades"),
        ("DOMESTICOS", "Servicios domésticos"),
        ("PERSONAL", "Personal"),
        ("DESCONOCIDO", "Desconocido"),
    )
    assert tuple((item.name, item.value) for item in Intencion) == (
        ("SEGURIDAD", "Seguridad"),
        ("DOCUMENTO", "Documento o comprobante"),
        ("OPERATIVO", "Operativo o soporte"),
        ("NOTIFICACION", "Notificación"),
        ("EDITORIAL", "Informativo o editorial"),
        ("PROMOCIONAL", "Promocional o venta"),
        ("PERSONAL", "Comunicación personal"),
        ("SOSPECHOSO", "Sospechoso"),
        ("DESCONOCIDO", "Desconocido"),
    )
    assert tuple((item.name, item.value) for item in Suscripcion) == (
        ("CONFIRMADA", "Confirmada"),
        ("PROBABLE", "Probable"),
        ("NO_CORRESPONDE", "No corresponde"),
        ("BAJA_SOLICITADA", "Baja solicitada"),
        ("POSIBLE_INCUMPLIMIENTO", "Posible incumplimiento"),
        ("DESCONOCIDO", "Desconocido"),
    )
    assert tuple((item.name, item.value) for item in Confianza) == (
        ("ALTA", "Alta"),
        ("MEDIA", "Media"),
        ("BAJA", "Baja"),
        ("CONTRADICTORIA", "Contradictoria"),
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
