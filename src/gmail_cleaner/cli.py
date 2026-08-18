from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import requests

from .core import (
    candidate_from_message,
    group_candidates,
    load_plan,
    read_approvals,
    validate_public_https_url,
    write_plan,
    write_review_csv,
)
from .google_api import (
    get_metadata,
    gmail_service,
    iter_message_ids,
    label_ids_by_name,
    trash_messages,
)


CONFIRMATION = "MOVER-A-PAPELERA"


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def paths_and_service(config: dict[str, Any]):
    gmail = config.get("gmail", {})
    credentials = Path(gmail.get("credentials_file", "credentials.json"))
    token = Path(gmail.get("token_file", "token.json"))
    return gmail_service(credentials, token)


def scan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    selection = config.get("selection", {})
    query = str(selection.get("query", "")).strip()
    if not query:
        raise ValueError("selection.query no puede estar vacío.")
    max_messages = int(selection.get("max_messages", 10000))
    if max_messages < 1:
        raise ValueError("selection.max_messages debe ser mayor que cero.")

    service = paths_and_service(config)
    profile = service.users().getProfile(userId="me").execute()
    account = str(profile.get("emailAddress", ""))
    protected_labels = label_ids_by_name(
        service, list(selection.get("protected_labels", []))
    )
    protected_senders = list(selection.get("protected_senders", []))

    candidates = []
    inspected = 0
    for message_id in iter_message_ids(service, query, max_messages):
        inspected += 1
        candidate = candidate_from_message(
            get_metadata(service, message_id),
            protected_label_ids=protected_labels,
            protected_senders=protected_senders,
        )
        if candidate:
            candidates.append(candidate)
        if inspected % 100 == 0:
            print(f"Revisados: {inspected}; candidatos: {len(candidates)}")

    groups = group_candidates(candidates)
    plan_id = write_plan(
        args.plan,
        account=account,
        query=query,
        groups=groups,
    )
    write_review_csv(args.review, groups)
    print(
        f"Plan {plan_id}: {len(candidates)} mensajes de {len(groups)} remitentes.\n"
        f"Plan privado: {args.plan}\nRevisión: {args.review}\n"
        "No se modificó ningún correo. Marcá SI sólo en las filas aprobadas."
    )
    return 0


def one_click_unsubscribe(url: str, timeout: int) -> tuple[bool, str]:
    validate_public_https_url(url)
    with requests.post(
        url,
        data={"List-Unsubscribe": "One-Click"},
        headers={"User-Agent": "limpiar-mails/0.1"},
        timeout=timeout,
        allow_redirects=False,
        stream=True,
    ) as response:
        ok = 200 <= response.status_code < 300
        return ok, f"HTTP {response.status_code}"


def apply(args: argparse.Namespace) -> int:
    if args.confirm != CONFIRMATION:
        raise ValueError(
            f"Confirmación inválida. Para ejecutar usá --confirm {CONFIRMATION}."
        )
    config = load_config(args.config)
    plan = load_plan(args.plan)
    approvals = read_approvals(args.review)
    selected = []
    unsubscribe_groups = []
    for group in plan["groups"]:
        trash, unsubscribe = approvals.get(group["key"], (False, False))
        if trash:
            selected.extend(str(item) for item in group["message_ids"])
        if unsubscribe and group.get("one_click_url"):
            unsubscribe_groups.append(group)

    if not selected and not unsubscribe_groups:
        print("No hay filas aprobadas; no se hizo ningún cambio.")
        return 0

    service = paths_and_service(config)
    current_account = str(
        service.users().getProfile(userId="me").execute().get("emailAddress", "")
    )
    if current_account.casefold() != str(plan.get("account", "")).casefold():
        raise ValueError(
            "La cuenta autenticada no coincide con la cuenta usada para crear el plan."
        )

    unsub_config = config.get("unsubscribe", {})
    unsub_enabled = bool(unsub_config.get("enabled", True)) and not args.skip_unsubscribe
    timeout = int(unsub_config.get("timeout_seconds", 15))
    results: list[dict[str, Any]] = []
    if unsub_enabled:
        for group in unsubscribe_groups:
            try:
                ok, detail = one_click_unsubscribe(group["one_click_url"], timeout)
            except (ValueError, requests.RequestException) as exc:
                ok, detail = False, str(exc)
            results.append(
                {
                    "sender": group["sender_email"],
                    "success": ok,
                    "detail": detail,
                }
            )
            print(f"Baja {group['sender_email']}: {'OK' if ok else 'FALLÓ'} ({detail})")

    if selected:
        trash_messages(service, list(dict.fromkeys(selected)))
        print(f"Movidos a Papelera: {len(set(selected))} mensajes.")

    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(
        json.dumps(
            {
                "plan_id": plan.get("plan_id"),
                "account": current_account,
                "trashed": len(set(selected)),
                "unsubscribe": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Resultado guardado en {args.results}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="limpiar-mails",
        description="Audita newsletters/spam y mueve sólo lo aprobado a Papelera.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Crear un plan sin modificar Gmail")
    scan_parser.add_argument("--config", type=Path, default=Path("config.toml"))
    scan_parser.add_argument("--plan", type=Path, default=Path("planes/plan.json"))
    scan_parser.add_argument("--review", type=Path, default=Path("planes/revision.csv"))
    scan_parser.set_defaults(func=scan)

    apply_parser = subparsers.add_parser("apply", help="Ejecutar sólo las filas aprobadas")
    apply_parser.add_argument("--config", type=Path, default=Path("config.toml"))
    apply_parser.add_argument("--plan", type=Path, default=Path("planes/plan.json"))
    apply_parser.add_argument("--review", type=Path, default=Path("planes/revision.csv"))
    apply_parser.add_argument(
        "--results", type=Path, default=Path("resultados/ultima-ejecucion.json")
    )
    apply_parser.add_argument("--confirm", required=True)
    apply_parser.add_argument("--skip-unsubscribe", action="store_true")
    apply_parser.set_defaults(func=apply)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
