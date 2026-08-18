from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
import socket
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit


ALWAYS_PROTECTED_LABELS = {"STARRED", "IMPORTANT", "SENT", "DRAFT"}
YES_VALUES = {"si", "sí", "s", "yes", "y"}
UNSUBSCRIBE_HEADER_RE = re.compile(r"<([^>]+)>")


@dataclass(frozen=True)
class Candidate:
    message_id: str
    thread_id: str
    sender_name: str
    sender_email: str
    subject: str
    date: str
    labels: tuple[str, ...]
    reason: str
    one_click_url: str | None


@dataclass(frozen=True)
class SenderGroup:
    key: str
    sender_name: str
    sender_email: str
    count: int
    reasons: tuple[str, ...]
    subjects: tuple[str, ...]
    message_ids: tuple[str, ...]
    one_click_url: str | None


def header_map(headers: Sequence[Mapping[str, str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for header in headers:
        name = header.get("name", "").strip().lower()
        if name:
            result[name].append(header.get("value", "").strip())
    return dict(result)


def normalize_sender(value: str) -> tuple[str, str]:
    name, address = parseaddr(value)
    return name.strip(), address.strip().casefold()


def is_protected_sender(address: str, protected: Iterable[str]) -> bool:
    normalized = address.casefold()
    for item in protected:
        rule = item.strip().casefold()
        if not rule:
            continue
        if rule.startswith("@") and normalized.endswith(rule):
            return True
        if normalized == rule:
            return True
    return False


def extract_one_click_url(headers: Mapping[str, Sequence[str]]) -> str | None:
    posts = ",".join(headers.get("list-unsubscribe-post", ())).casefold()
    if "list-unsubscribe=one-click" not in posts:
        return None

    auth_results = " ".join(headers.get("authentication-results", ())).casefold()
    if "dkim=pass" not in auth_results:
        return None

    signatures = headers.get("dkim-signature", ())
    covered = False
    for signature in signatures:
        match = re.search(r"(?:^|;)\s*h=([^;]+)", signature, flags=re.IGNORECASE)
        if not match:
            continue
        names = {part.strip().casefold() for part in match.group(1).split(":")}
        if {"list-unsubscribe", "list-unsubscribe-post"} <= names:
            covered = True
            break
    if not covered:
        return None

    for value in headers.get("list-unsubscribe", ()):
        for raw_url in UNSUBSCRIBE_HEADER_RE.findall(value):
            url = raw_url.strip()
            parsed = urlsplit(url)
            if parsed.scheme.casefold() == "https" and parsed.hostname:
                return url
    return None


def reason_for(labels: set[str], has_unsubscribe: bool) -> str | None:
    if "SPAM" in labels:
        return "spam"
    if "CATEGORY_PROMOTIONS" in labels and has_unsubscribe:
        return "promocion_con_baja"
    if "CATEGORY_PROMOTIONS" in labels:
        return "promocion"
    if "CATEGORY_UPDATES" in labels and has_unsubscribe:
        return "newsletter_o_actualizacion"
    if has_unsubscribe:
        return "newsletter"
    return None


def candidate_from_message(
    message: Mapping[str, Any],
    *,
    protected_label_ids: set[str],
    protected_senders: Iterable[str],
) -> Candidate | None:
    labels = {str(item) for item in message.get("labelIds", ())}
    if labels & (ALWAYS_PROTECTED_LABELS | protected_label_ids):
        return None

    headers = header_map(message.get("payload", {}).get("headers", ()))
    sender_name, sender_email = normalize_sender(
        next(iter(headers.get("from", ())), "")
    )
    if not sender_email or is_protected_sender(sender_email, protected_senders):
        return None

    one_click_url = extract_one_click_url(headers)
    has_unsubscribe = bool(headers.get("list-unsubscribe"))
    reason = reason_for(labels, has_unsubscribe)
    if reason is None:
        return None

    return Candidate(
        message_id=str(message["id"]),
        thread_id=str(message.get("threadId", "")),
        sender_name=sender_name,
        sender_email=sender_email,
        subject=next(iter(headers.get("subject", ())), "(sin asunto)"),
        date=next(iter(headers.get("date", ())), ""),
        labels=tuple(sorted(labels)),
        reason=reason,
        one_click_url=one_click_url,
    )


def group_candidates(candidates: Iterable[Candidate]) -> list[SenderGroup]:
    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.sender_email].append(candidate)

    result: list[SenderGroup] = []
    for sender, items in grouped.items():
        newest_first = list(reversed(items))
        url = next((item.one_click_url for item in newest_first if item.one_click_url), None)
        key = hashlib.sha256(sender.encode("utf-8")).hexdigest()[:12]
        result.append(
            SenderGroup(
                key=key,
                sender_name=next((x.sender_name for x in items if x.sender_name), ""),
                sender_email=sender,
                count=len(items),
                reasons=tuple(sorted({x.reason for x in items})),
                subjects=tuple(dict.fromkeys(x.subject for x in newest_first[:3])),
                message_ids=tuple(x.message_id for x in items),
                one_click_url=url,
            )
        )
    return sorted(result, key=lambda group: (-group.count, group.sender_email))


def write_plan(
    path: Path,
    *,
    account: str,
    query: str,
    groups: Sequence[SenderGroup],
) -> str:
    payload = {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "account": account,
        "query": query,
        "groups": [asdict(group) for group in groups],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    plan_id = hashlib.sha256(canonical).hexdigest()[:16]
    payload["plan_id"] = plan_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan_id


def write_review_csv(path: Path, groups: Sequence[SenderGroup]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "aprobar_papelera",
                "aprobar_baja",
                "clave",
                "cantidad",
                "remitente",
                "email",
                "motivos",
                "baja_un_click_disponible",
                "asuntos_de_ejemplo",
            ],
        )
        writer.writeheader()
        for group in groups:
            writer.writerow(
                {
                    "aprobar_papelera": "",
                    "aprobar_baja": "",
                    "clave": group.key,
                    "cantidad": group.count,
                    "remitente": group.sender_name,
                    "email": group.sender_email,
                    "motivos": ", ".join(group.reasons),
                    "baja_un_click_disponible": "SI" if group.one_click_url else "NO",
                    "asuntos_de_ejemplo": " | ".join(group.subjects),
                }
            )


def read_approvals(path: Path) -> dict[str, tuple[bool, bool]]:
    approvals: dict[str, tuple[bool, bool]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row.get("clave") or "").strip()
            if not key:
                continue
            trash = (row.get("aprobar_papelera") or "").strip().casefold() in YES_VALUES
            unsubscribe = (row.get("aprobar_baja") or "").strip().casefold() in YES_VALUES
            approvals[key] = (trash, unsubscribe)
    return approvals


def load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("groups"), list):
        raise ValueError("El archivo no es un plan compatible (versión 1).")
    return data


def validate_public_https_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ValueError("La baja no usa una URL HTTPS válida.")
    if parsed.username or parsed.password:
        raise ValueError("La URL de baja contiene credenciales y fue bloqueada.")
    if parsed.port not in (None, 443):
        raise ValueError("La URL de baja usa un puerto no permitido.")

    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443)}
    except socket.gaierror as exc:
        raise ValueError("No se pudo resolver el dominio de baja.") from exc
    if not addresses:
        raise ValueError("El dominio de baja no devolvió direcciones.")
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise ValueError("La URL de baja apunta a una red no pública.")
    return url
