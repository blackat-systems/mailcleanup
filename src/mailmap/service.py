from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from mailmap.classifier import assess_messages
from mailmap.fixtures import REQUIRED_FIXTURE_TAGS
from mailmap.model import (
    Confianza,
    MessageAssessment,
    Recomendacion,
    Suscripcion,
)
from mailmap.repository import Repository

CORDOBA = ZoneInfo("America/Argentina/Cordoba")
SYNTHETIC_SNAPSHOT_AT = "2026-08-18T00:00:00-03:00"
CONFIDENCE_RANK = {
    Confianza.ALTA: 0,
    Confianza.MEDIA: 1,
    Confianza.BAJA: 2,
    Confianza.CONTRADICTORIA: 3,
}


def _most_common(counter: Counter[str], fallback: str) -> str:
    if not counter:
        return fallback
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


class MailmapService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def assessments(self) -> tuple[MessageAssessment, ...]:
        return assess_messages(self.repository.messages())

    def _source_records(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[MessageAssessment]] = defaultdict(list)
        for item in self.assessments():
            grouped[item.source_id].append(item)

        records: list[dict[str, Any]] = []
        for source_id, items in grouped.items():
            ordered = sorted(items, key=lambda item: item.message.received_at, reverse=True)
            rubros = Counter(item.rubro.value for item in items)
            intents = Counter(item.intencion.value for item in items)
            subscriptions = Counter(item.suscripcion.value for item in items)
            methods = Counter(item.metodo_baja.value for item in items)
            recommendations = Counter(item.recomendacion.value for item in items)
            flows: list[dict[str, Any]] = []
            for intent, count in sorted(intents.items(), key=lambda row: (-row[1], row[0])):
                flow_items = [item for item in items if item.intencion.value == intent]
                flows.append(
                    {
                        "id": f"{source_id}:{hashlib.sha1(intent.encode()).hexdigest()[:8]}",
                        "name": intent,
                        "messageCount": count,
                        "protectedCount": sum(item.protected for item in flow_items),
                        "subscriptionStates": sorted(
                            {item.suscripcion.value for item in flow_items}
                        ),
                    }
                )

            evidence_by_code: dict[str, dict[str, str]] = {}
            for item in ordered:
                for evidence in item.evidence:
                    evidence_by_code.setdefault(evidence.code, evidence.as_dict())

            worst_confidence = max(
                (item.confianza for item in items), key=lambda value: CONFIDENCE_RANK[value]
            )
            candidate_count = sum(
                not item.protected
                and item.recomendacion in {Recomendacion.PAPELERA, Recomendacion.ARCHIVAR}
                for item in items
            )
            records.append(
                {
                    "id": source_id,
                    "name": ordered[0].source_name,
                    "messageCount": len(items),
                    "unreadCount": sum("UNREAD" in item.message.labels for item in items),
                    "protectedCount": sum(item.protected for item in items),
                    "candidateCount": candidate_count,
                    "totalBytes": sum(item.message.size_bytes for item in items),
                    "firstSeen": min(item.message.received_at for item in items).isoformat(),
                    "lastSeen": max(item.message.received_at for item in items).isoformat(),
                    "senders": sorted({item.message.sender_email for item in items}),
                    "domains": sorted(
                        {
                            item.message.authenticated_domain
                            or item.message.sender_email.rpartition("@")[2]
                            for item in items
                        }
                    ),
                    "rubro": _most_common(rubros, "Desconocido"),
                    "rubros": dict(sorted(rubros.items())),
                    "dominantIntent": _most_common(intents, "Desconocido"),
                    "intents": dict(sorted(intents.items())),
                    "subscription": _most_common(subscriptions, "Desconocido"),
                    "subscriptionStates": dict(sorted(subscriptions.items())),
                    "unsubscribeMethods": dict(sorted(methods.items())),
                    "confidence": worst_confidence.value,
                    "ambiguous": any(item.source_ambiguous for item in items),
                    "isSpam": all(item.intencion.value == "Sospechoso" for item in items),
                    "isSubscription": any(
                        item.suscripcion in {Suscripcion.CONFIRMADA, Suscripcion.PROBABLE}
                        for item in items
                    ),
                    "recommendation": _most_common(recommendations, "Revisar"),
                    "flows": flows,
                    "evidence": list(evidence_by_code.values()),
                    "recentMessages": [item.as_dict() for item in ordered[:5]],
                }
            )
        return sorted(records, key=lambda item: (-int(item["messageCount"]), str(item["name"])))

    def sources(
        self,
        *,
        query: str | None = None,
        rubro: str | None = None,
        view: str | None = None,
    ) -> list[dict[str, Any]]:
        records = self._source_records()
        if query:
            needle = query.casefold().strip()
            records = [
                record
                for record in records
                if needle in str(record["name"]).casefold()
                or any(needle in sender.casefold() for sender in record["senders"])
            ]
        if rubro:
            records = [record for record in records if record["rubro"] == rubro]
        if view == "subscriptions":
            records = [record for record in records if record["isSubscription"]]
        elif view == "spam":
            records = [record for record in records if record["isSpam"]]
        elif view == "protected":
            records = [record for record in records if int(record["protectedCount"]) > 0]
        return records

    def source(self, source_id: str) -> dict[str, Any] | None:
        return next((item for item in self._source_records() if item["id"] == source_id), None)

    def dashboard(self) -> dict[str, Any]:
        assessments = self.assessments()
        sources = self._source_records()
        rubros = Counter(item.rubro.value for item in assessments)
        fixture_tags = {tag for item in assessments for tag in item.message.fixture_tags}
        return {
            "mode": "synthetic",
            "snapshotAt": SYNTHETIC_SNAPSHOT_AT,
            "totalMessages": len(assessments),
            "totalSources": len(sources),
            "subscriptionSources": sum(bool(source["isSubscription"]) for source in sources),
            "spamMessages": sum(item.intencion.value == "Sospechoso" for item in assessments),
            "protectedMessages": sum(item.protected for item in assessments),
            "candidateMessages": sum(
                not item.protected
                and item.recomendacion in {Recomendacion.PAPELERA, Recomendacion.ARCHIVAR}
                for item in assessments
            ),
            "totalBytes": sum(item.message.size_bytes for item in assessments),
            "rubros": [
                {"name": name, "count": count}
                for name, count in sorted(rubros.items(), key=lambda item: (-item[1], item[0]))
            ],
            "topSources": sources[:5],
            "fixtureCoverage": {
                "covered": len(REQUIRED_FIXTURE_TAGS & fixture_tags),
                "required": len(REQUIRED_FIXTURE_TAGS),
                "missing": sorted(REQUIRED_FIXTURE_TAGS - fixture_tags),
            },
        }

    def analysis_status(self) -> dict[str, Any]:
        assessments = self.assessments()
        incidents = [
            {
                "messageId": item.message.id,
                "state": item.message.failure_state,
                "resolution": (
                    "Recuperado sin duplicar el registro"
                    if item.message.failure_state == "recovered_after_retry"
                    else "Conservado como parcial y marcado para revisión"
                ),
            }
            for item in assessments
            if item.message.failure_state
        ]
        return {
            "mode": "synthetic",
            "state": "completed_with_warnings" if incidents else "completed",
            "phases": [
                {"name": "Normalización", "state": "completed"},
                {"name": "Identidad de fuentes", "state": "completed"},
                {"name": "Clasificación", "state": "completed"},
                {"name": "Protecciones", "state": "completed"},
            ],
            "incidents": incidents,
        }

    def create_plan(
        self,
        *,
        source_ids: list[str],
        before_date: date | None,
        keep_latest: int,
        operations: list[str],
    ) -> dict[str, Any]:
        assessments = [item for item in self.assessments() if item.source_id in source_ids]
        cutoff = datetime.combine(before_date, time.max, tzinfo=CORDOBA) if before_date else None
        exclusions: list[dict[str, str]] = []
        included: list[MessageAssessment] = []

        by_source: dict[str, list[MessageAssessment]] = defaultdict(list)
        for item in assessments:
            by_source[item.source_id].append(item)

        for _source_id, items in by_source.items():
            ordered = sorted(items, key=lambda item: item.message.received_at, reverse=True)
            kept = {item.message.id for item in ordered[:keep_latest]} if keep_latest else set()
            for item in ordered:
                if item.protected:
                    exclusions.append(
                        {
                            "messageId": item.message.id,
                            "reason": item.proteccion.value,
                        }
                    )
                elif item.message.id in kept:
                    exclusions.append(
                        {"messageId": item.message.id, "reason": "Conservar los últimos"}
                    )
                elif cutoff and item.message.received_at > cutoff:
                    exclusions.append(
                        {"messageId": item.message.id, "reason": "Posterior a la fecha civil"}
                    )
                else:
                    included.append(item)

        canonical_selection = {
            "sourceIds": sorted(set(source_ids)),
            "beforeDate": before_date.isoformat() if before_date else None,
            "timezone": "America/Argentina/Cordoba",
            "keepLatest": keep_latest,
            "operations": sorted(set(operations)),
        }
        snapshot_messages = [
            {
                "id": item.message.id,
                "revision": item.message.revision,
                "sourceId": item.source_id,
                "receivedAt": item.message.received_at.isoformat(),
            }
            for item in sorted(included, key=lambda item: item.message.id)
        ]
        plan_hash_input = json.dumps(
            {"selection": canonical_selection, "messages": snapshot_messages},
            sort_keys=True,
            ensure_ascii=False,
        )
        plan_id = "plan-" + hashlib.sha256(plan_hash_input.encode("utf-8")).hexdigest()[:12]
        created_at = datetime.now(CORDOBA).isoformat()
        warnings = [
            "Simulación local: este plan no puede modificar Gmail.",
            "Desuscribir y disponer del historial son decisiones independientes.",
        ]
        if any(operation == "unsubscribe" for operation in operations):
            warnings.append("La baja aparece sólo como intención; no se enviará ninguna solicitud.")
        snapshot = {
            "messageCount": len(snapshot_messages),
            "messages": snapshot_messages,
            "excludedCount": len(exclusions),
            "totalBytes": sum(item.message.size_bytes for item in included),
        }
        self.repository.save_plan(
            plan_id=plan_id,
            created_at=created_at,
            selection=canonical_selection,
            snapshot=snapshot,
        )
        return {
            "id": plan_id,
            "createdAt": created_at,
            "status": "simulated",
            "selection": canonical_selection,
            "sourceCount": len(set(source_ids)),
            "messageCount": len(snapshot_messages),
            "totalBytes": snapshot["totalBytes"],
            "excludedCount": len(exclusions),
            "exclusions": exclusions,
            "sample": [item.as_dict() for item in included[:5]],
            "warnings": warnings,
            "canExecute": False,
        }

    def revalidate_plan(self, plan_id: str) -> dict[str, Any] | None:
        plan = self.repository.plan(plan_id)
        if not plan:
            return None
        current = {item.message.id: item for item in self.assessments()}
        stale: list[dict[str, str]] = []
        valid: list[str] = []
        for snapshot in plan["snapshot"]["messages"]:
            item = current.get(str(snapshot["id"]))
            if item is None:
                stale.append({"messageId": str(snapshot["id"]), "reason": "Ya no existe"})
            elif item.message.revision != int(snapshot["revision"]):
                stale.append(
                    {"messageId": item.message.id, "reason": "Cambió desde la vista previa"}
                )
            elif item.protected:
                stale.append({"messageId": item.message.id, "reason": item.proteccion.value})
            else:
                valid.append(item.message.id)
        return {
            "id": plan_id,
            "status": "stale" if stale else "valid",
            "validMessageIds": valid,
            "excluded": stale,
            "canExecute": False,
        }

    def history(self) -> list[dict[str, Any]]:
        return self.repository.plans()

    def configuration(self) -> dict[str, Any]:
        return {
            "mode": "synthetic",
            "platform": "Windows",
            "experience": "Aplicación web local",
            "timezone": "America/Argentina/Cordoba",
            "protectedLabels": ["STARRED", "IMPORTANT", "Trabajo", "Familia", "Pagos"],
            "schemaVersion": self.repository.schema_version(),
            "gmailConnected": False,
            "oauthAvailable": False,
            "remoteAi": False,
            "permanentDelete": False,
        }
