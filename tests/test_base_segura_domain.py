from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from mailmap.classifier import assess_messages, classify_message
from mailmap.fixtures import REQUIRED_FIXTURE_TAGS, synthetic_messages
from mailmap.model import Confianza, Intencion, Proteccion
from mailmap.repository import Repository
from mailmap.service import MailmapService


def service_at(path: Path) -> MailmapService:
    return MailmapService(Repository(path / "mailmap.db"))


def test_all_required_synthetic_cases_are_present() -> None:
    tags = {tag for message in synthetic_messages() for tag in message.fixture_tags}
    assert tags >= REQUIRED_FIXTURE_TAGS
    assert all(message.sender_email.endswith(".example") for message in synthetic_messages())


def test_source_grouping_is_conservative_and_explainable(tmp_path: Path) -> None:
    sources = {item["id"]: item for item in service_at(tmp_path).sources()}

    nube = sources["src-nube-clara"]
    assert nube["messageCount"] == 4
    assert set(nube["intents"]) == {
        "Seguridad",
        "Documento o comprobante",
        "Promocional o venta",
        "Notificación",
    }
    assert len(nube["domains"]) == 2

    assert "src-cocina-norte" in sources
    assert "src-ruta-viva" in sources
    assert sources["src-cocina-norte"]["senders"] != sources["src-ruta-viva"]["senders"]

    ambiguous = [item for item in sources.values() if item["ambiguous"]]
    ambiguous_senders = {
        sender
        for source in ambiguous
        for sender in source["senders"]
        if "dispatch-compartido" in sender
    }
    assert len(ambiguous_senders) == 2
    assert (
        len(
            {
                source["id"]
                for source in ambiguous
                if any("dispatch-compartido" in sender for sender in source["senders"])
            }
        )
        == 2
    )


def test_intent_precedence_and_protections_are_not_overruled() -> None:
    assessments = {item.message.id: item for item in assess_messages(synthetic_messages())}

    security = assessments["nube-security-01"]
    assert security.intencion is Intencion.SEGURIDAD
    assert security.protected
    assert security.confianza is Confianza.CONTRADICTORIA

    invoice = assessments["nube-invoice-01"]
    assert invoice.intencion is Intencion.DOCUMENTO
    assert invoice.proteccion is Proteccion.USUARIO
    assert invoice.protected

    spoof = assessments["faro-spoof-01"]
    assert spoof.intencion is Intencion.SOSPECHOSO
    assert spoof.source_ambiguous
    assert spoof.confianza is Confianza.CONTRADICTORIA

    personal = assessments["nora-personal-01"]
    assert personal.intencion is Intencion.PERSONAL
    assert personal.protected

    assert assessments["orbit-thread-01"].protected
    assert assessments["orbit-thread-02"].protected
    assert assessments["orbit-thread-02"].proteccion is Proteccion.REVISION


@pytest.mark.parametrize("label", ["SENT", "DRAFT", "TRASH"])
def test_system_locations_are_always_protected(label: str) -> None:
    template = next(
        message for message in synthetic_messages() if message.id == "obsolete-plan-01"
    )
    assessment = classify_message(
        replace(template, id=f"protected-{label.casefold()}", labels=(label,))
    )

    assert assessment.protected
    assert assessment.proteccion is Proteccion.USUARIO


def test_plan_excludes_protected_and_keeps_actions_independent(tmp_path: Path) -> None:
    service = service_at(tmp_path)
    plan = service.create_plan(
        source_ids=["src-nube-clara"],
        before_date=date(2026, 12, 31),
        keep_latest=0,
        operations=["trash", "unsubscribe"],
    )

    assert not plan["canExecute"]
    assert plan["messageCount"] == 2
    assert plan["excludedCount"] == 2
    excluded = {item["messageId"] for item in plan["exclusions"]}
    assert {"nube-security-01", "nube-invoice-01"} <= excluded
    assert plan["selection"]["operations"] == ["trash", "unsubscribe"]
    assert any("independientes" in warning for warning in plan["warnings"])


def test_cordoba_civil_boundary_is_applied_explicitly(tmp_path: Path) -> None:
    plan = service_at(tmp_path).create_plan(
        source_ids=["src-ciudad-clara"],
        before_date=date(2026, 7, 31),
        keep_latest=0,
        operations=["archive"],
    )

    assert plan["selection"]["timezone"] == "America/Argentina/Cordoba"
    assert plan["messageCount"] == 1
    assert plan["sample"][0]["id"] == "cordoba-boundary-before"
    assert any(
        item["messageId"] == "cordoba-boundary-after"
        and item["reason"] == "Posterior a la fecha civil"
        for item in plan["exclusions"]
    )


def test_obsolete_plan_is_invalidated_by_label_change(tmp_path: Path) -> None:
    service = service_at(tmp_path)
    plan = service.create_plan(
        source_ids=["src-mercado-limon"],
        before_date=None,
        keep_latest=0,
        operations=["trash"],
    )
    assert plan["messageCount"] == 1

    service.repository.update_labels(
        "obsolete-plan-01", ("INBOX", "CATEGORY_PROMOTIONS", "STARRED")
    )
    revalidated = service.revalidate_plan(str(plan["id"]))

    assert revalidated is not None
    assert revalidated["status"] == "stale"
    assert revalidated["validMessageIds"] == []
    assert revalidated["excluded"][0]["reason"] == "Cambió desde la vista previa"


def test_retry_and_partial_metadata_are_visible_without_duplication(tmp_path: Path) -> None:
    service = service_at(tmp_path)
    status = service.analysis_status()
    messages = service.repository.messages()

    assert status["state"] == "completed_with_warnings"
    assert len(status["incidents"]) == 2
    assert len({message.id for message in messages}) == len(messages)
