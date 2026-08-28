from __future__ import annotations

from dataclasses import replace

import pytest

from mailmap.map_fixtures import canonical_synthetic_map_fixture
from mailmap.map_synthetic_gate import (
    SYNTHETIC_MAP_ACCOUNT_KEY,
    SYNTHETIC_MAP_FIXTURE_VERSION,
    SyntheticMapGateError,
    assert_synthetic_fixture_payload,
    assert_synthetic_map_snapshot,
)


def test_canonical_fixture_passes_the_shared_gate() -> None:
    fixture = canonical_synthetic_map_fixture()

    assert_synthetic_fixture_payload(
        account_key=fixture.account_key,
        fixture_version=fixture.fixture_version,
        records=fixture.records,
        checkpoint=fixture.checkpoint,
        policy_events=fixture.policy_events,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sender_address", "persona@" + "outside.invalid"),
        ("authenticated_domain", "outside.invalid"),
        ("list_id", "boletin.outside.invalid"),
        ("subject", "Revisá https://outside.invalid/private"),
        ("list_unsubscribe", "ftp://outside.invalid/private"),
        ("list_unsubscribe", "//outside.invalid/private"),
        ("sender_name", "Contacto persona@" + "outside.invalid"),
    ),
)
def test_shared_gate_rejects_non_example_metadata(field: str, value: str) -> None:
    fixture = canonical_synthetic_map_fixture()
    records = (replace(fixture.records[0], **{field: value}), *fixture.records[1:])

    with pytest.raises(SyntheticMapGateError):
        assert_synthetic_fixture_payload(
            account_key=fixture.account_key,
            fixture_version=fixture.fixture_version,
            records=records,
            checkpoint=fixture.checkpoint,
            policy_events=fixture.policy_events,
        )


def test_shared_gate_rejects_arbitrary_account_and_marker() -> None:
    fixture = canonical_synthetic_map_fixture()
    for account_key, fixture_version in (
        ("another-synthetic-account", fixture.fixture_version),
        (fixture.account_key, "another-fixture-version"),
    ):
        with pytest.raises(SyntheticMapGateError):
            assert_synthetic_fixture_payload(
                account_key=account_key,
                fixture_version=fixture_version,
                records=fixture.records,
                checkpoint=fixture.checkpoint,
                policy_events=fixture.policy_events,
            )


def test_snapshot_gate_rejects_an_extra_account() -> None:
    fixture = canonical_synthetic_map_fixture()
    with pytest.raises(SyntheticMapGateError):
        assert_synthetic_map_snapshot(
            account_key=SYNTHETIC_MAP_ACCOUNT_KEY,
            account_exists=True,
            indexed_account_keys=(SYNTHETIC_MAP_ACCOUNT_KEY, "synthetic-other"),
            fixture_version=SYNTHETIC_MAP_FIXTURE_VERSION,
            records=fixture.records,
            checkpoint=fixture.checkpoint,
            policy_history=fixture.policy_events,
            active_policies=(),
        )
