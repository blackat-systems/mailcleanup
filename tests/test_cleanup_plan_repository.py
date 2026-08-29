from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event, Lock

import pytest

import mailmap.cleanup_plan_domain as cleanup_domain
import mailmap.repository as repository_module
from mailmap.cleanup_plan_domain import (
    build_cleanup_target_catalog,
    cleanup_command_fingerprint,
)
from mailmap.cleanup_plan_model import (
    AllTemporalFilter,
    CancelCleanupPlanCommand,
    CleanupCommandStatus,
    CleanupDisposition,
    CleanupEventType,
    CleanupExclusionReason,
    CleanupMemberInitialState,
    CleanupPlanError,
    CleanupPlanErrorCode,
    CleanupPlanEvent,
    CleanupPlanMember,
    CleanupPlanReceipt,
    CleanupPlanState,
    CleanupReadState,
    CleanupTarget,
    CleanupTargetKind,
    CreateCleanupPlanCommand,
    PersistedCleanupPlan,
    RevalidateCleanupPlanCommand,
    cleanup_target_sort_key,
)
from mailmap.index_model import SyncState
from mailmap.map_fixtures import canonical_synthetic_map_fixture
from mailmap.map_synthetic_gate import SYNTHETIC_MAP_ACCOUNT_KEY
from mailmap.repository import (
    MIGRATIONS,
    CleanupPlanListingItem,
    CleanupPlanListingPage,
    Repository,
)

ACCOUNT = SYNTHETIC_MAP_ACCOUNT_KEY
COMMAND_NOW = datetime(2026, 8, 29, 15, 0, tzinfo=UTC)
CLEANUP_TABLES = (
    "cleanup_plans",
    "cleanup_plan_targets",
    "cleanup_plan_members",
    "cleanup_plan_member_reasons",
    "cleanup_plan_samples",
    "cleanup_plan_events",
    "cleanup_plan_member_removals",
    "cleanup_plan_requests",
    "cleanup_plan_catalog_state",
)
CLEANUP_INDEXES = {
    "idx_cleanup_plans_listing",
    "idx_cleanup_plans_state_listing",
    "idx_cleanup_plan_members_page",
    "idx_cleanup_plan_members_initial_state_page",
    "idx_cleanup_plan_member_reasons_removal",
    "idx_cleanup_plan_member_removals_event",
    "idx_cleanup_plan_requests_plan",
}


class _InjectedFailure(RuntimeError):
    pass


def _command_id(value: int) -> str:
    return f"{value:08x}-0000-4000-8000-{value:012x}"


def _installed_repository(path: Path) -> Repository:
    repository = Repository(path)
    fixture = canonical_synthetic_map_fixture()
    repository.install_synthetic_map_fixture(
        fixture.account_key,
        fixture.fixture_version,
        fixture.records,
        fixture.checkpoint,
        fixture.policy_events,
    )
    return repository


def _create_command(repository: Repository, *, command_number: int) -> CreateCleanupPlanCommand:
    composition = repository.cleanup_plan_targets(ACCOUNT)
    targets = tuple(
        sorted(
            (
                CleanupTarget(kind=item.kind, target_id=item.target_id)
                for item in build_cleanup_target_catalog(composition)
                if item.kind is not CleanupTargetKind.LABEL
            ),
            key=cleanup_target_sort_key,
        )
    )
    assert targets
    return CreateCleanupPlanCommand(
        command_id=_command_id(command_number),
        expected_map_revision=composition.projection.map_revision,
        expected_policy_revision=composition.projection.policy_revision,
        disposition=CleanupDisposition.ARCHIVE,
        targets=targets,
        temporal_filter=AllTemporalFilter(),
        read_state=CleanupReadState.ANY,
    )


def _create_plan(
    repository: Repository,
    *,
    command_number: int,
    command_now: datetime = COMMAND_NOW,
) -> tuple[CreateCleanupPlanCommand, CleanupPlanReceipt, PersistedCleanupPlan]:
    command = _create_command(repository, command_number=command_number)
    receipt = repository.create_cleanup_plan(
        ACCOUNT,
        command,
        request_fingerprint=cleanup_command_fingerprint(command),
        clock=lambda: command_now,
    )
    plan = repository.cleanup_plan(ACCOUNT, receipt.plan_id)
    assert plan is not None
    assert plan.persisted_state in (CleanupPlanState.FROZEN, CleanupPlanState.REDUCED)
    return command, receipt, plan


def _revalidation_command(
    repository: Repository,
    plan: PersistedCleanupPlan,
    *,
    command_number: int,
) -> RevalidateCleanupPlanCommand:
    composition = repository.cleanup_plan_targets(ACCOUNT)
    return RevalidateCleanupPlanCommand(
        command_id=_command_id(command_number),
        expected_plan_revision=plan.plan_revision,
        expected_map_revision=composition.projection.map_revision,
        expected_policy_revision=composition.projection.policy_revision,
    )


def _cancel_command(
    plan: PersistedCleanupPlan,
    *,
    command_number: int,
) -> CancelCleanupPlanCommand:
    return CancelCleanupPlanCommand(
        command_id=_command_id(command_number),
        expected_plan_revision=plan.plan_revision,
    )


def _never_clock() -> datetime:
    raise AssertionError("an exact replay must not read the clock")


def _cleanup_counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in CLEANUP_TABLES
        }


def _schema_signature(path: Path) -> tuple[tuple[str, str, str], ...]:
    with sqlite3.connect(path) as connection:
        return tuple(
            (str(row[0]), str(row[1]), " ".join(str(row[2]).split()))
            for row in connection.execute(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )
        )


def _table_counts(path: Path, tables: tuple[str, ...]) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def test_v5_fresh_and_exact_v4_upgrade_match_and_preserve_v1_v4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh_path = tmp_path / "fresh-v5.db"
    migrated_path = tmp_path / "migrated-v4.db"
    full_migrations = MIGRATIONS

    monkeypatch.setattr(repository_module, "MIGRATIONS", full_migrations[:4])
    v4_repository = _installed_repository(migrated_path)
    assert v4_repository.schema_version() == 4
    with sqlite3.connect(migrated_path) as connection:
        connection.execute(
            "INSERT INTO app_meta(key, value) VALUES ('v4-preservation-marker', 'kept')"
        )
        old_tables = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations' "
                "ORDER BY name"
            )
        )
    old_counts = _table_counts(migrated_path, old_tables)
    old_schema = set(_schema_signature(migrated_path))

    monkeypatch.setattr(repository_module, "MIGRATIONS", full_migrations)
    migrated = Repository(migrated_path)
    fresh = Repository(fresh_path)

    assert migrated.schema_version() == fresh.schema_version() == 5
    assert _schema_signature(migrated_path) == _schema_signature(fresh_path)
    assert old_schema <= set(_schema_signature(migrated_path))
    assert _table_counts(migrated_path, old_tables) == old_counts
    with sqlite3.connect(migrated_path) as connection:
        assert connection.execute(
            "SELECT value FROM app_meta WHERE key = 'v4-preservation-marker'"
        ).fetchone() == ("kept",)
    assert tuple(version for version, _script in full_migrations) == (1, 2, 3, 4, 5)
    assert tuple(
        hashlib.sha256(script.encode("utf-8")).hexdigest()
        for _version, script in full_migrations[:4]
    ) == (
        "fa566caf70cef0b58bd9397f8444dc8f3c1a9bd6b2a7eb288fab2163089189e6",
        "5a25b39afec02e99333886123551f462f6aa370f72a9db1928fcd905473bbdb7",
        "891874365929b4a57f1f58d39350c8f644f5105a65173411f8a1d4b09b6168b3",
        "a3f9787ebdfebab710471638438c43b4d5ca9128c7dc64ca5fb5a30858ae8d1d",
    )
    assert "begin" not in full_migrations[4][1].casefold()
    assert "commit" not in full_migrations[4][1].casefold()
    assert "rollback" not in full_migrations[4][1].casefold()


def test_v5_schema_is_normalized_constrained_and_cascades_by_account(
    tmp_path: Path,
) -> None:
    path = tmp_path / "schema-cascade.db"
    repository = _installed_repository(path)
    _command, _receipt, plan = _create_plan(repository, command_number=100)

    selected = next(
        member
        for member in plan.members
        if member.initial_state is CleanupMemberInitialState.SELECTED
    )
    original_members = plan.members
    repository.delete_indexed_messages(ACCOUNT, (selected.provider_message_id,))
    changed_plan = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert changed_plan is not None
    assert changed_plan.members == original_members
    revalidate = _revalidation_command(repository, changed_plan, command_number=101)
    repository.revalidate_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=plan.plan_id,
        ),
        clock=lambda: COMMAND_NOW + timedelta(minutes=1),
    )

    with sqlite3.connect(path) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'cleanup_%'"
            )
        }
        indexes = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_cleanup_%'"
            )
        }
        assert tables == set(CLEANUP_TABLES)
        assert indexes == CLEANUP_INDEXES
        for table in CLEANUP_TABLES:
            columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
            assert columns
            assert all("JSON" not in str(row[2]).upper() for row in columns)
            assert all("BLOB" not in str(row[2]).upper() for row in columns)
            assert all("json" not in str(row[1]).casefold() for row in columns)
            foreign_keys = connection.execute(f"PRAGMA foreign_key_list({table})").fetchall()
            assert foreign_keys
            assert all(str(row[6]).upper() == "CASCADE" for row in foreign_keys)
        member_parents = {
            str(row[2])
            for row in connection.execute("PRAGMA foreign_key_list(cleanup_plan_members)")
        }
        assert member_parents == {"cleanup_plans"}
        assert "indexed_messages" not in member_parents

    assert all(value > 0 for value in _cleanup_counts(path).values())
    repository.delete_account_index(ACCOUNT)
    assert _cleanup_counts(path) == {table: 0 for table in CLEANUP_TABLES}


def test_catalog_zero_one_increments_replays_and_gets_never_write(
    tmp_path: Path,
) -> None:
    path = tmp_path / "catalog.db"
    repository = _installed_repository(path)

    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 0
    repository.cleanup_plan_context(ACCOUNT)
    repository.cleanup_plan_targets(ACCOUNT)
    assert repository.cleanup_plans(ACCOUNT) == ()
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 0
    assert _cleanup_counts(path)["cleanup_plan_catalog_state"] == 0

    create, created_receipt, plan = _create_plan(repository, command_number=200)
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 1
    repository.cleanup_plan(ACCOUNT, plan.plan_id)
    repository.cleanup_plan_members(ACCOUNT, plan.plan_id)
    repository.cleanup_plan_events(ACCOUNT, plan.plan_id)
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 1

    revalidate = _revalidation_command(repository, plan, command_number=201)
    revalidated_receipt = repository.revalidate_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=plan.plan_id,
        ),
        clock=lambda: COMMAND_NOW + timedelta(minutes=1),
    )
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 2
    revalidated_plan = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert revalidated_plan is not None
    cancel = _cancel_command(revalidated_plan, command_number=202)
    cancelled_receipt = repository.cancel_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        cancel,
        request_fingerprint=cleanup_command_fingerprint(cancel, plan_id=plan.plan_id),
        clock=lambda: COMMAND_NOW + timedelta(minutes=2),
    )
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 3

    replayed_create = repository.create_cleanup_plan(
        ACCOUNT,
        create,
        request_fingerprint=cleanup_command_fingerprint(create),
        clock=_never_clock,
    )
    replayed_revalidation = repository.revalidate_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=plan.plan_id,
        ),
        clock=_never_clock,
    )
    replayed_cancel = repository.cancel_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        cancel,
        request_fingerprint=cleanup_command_fingerprint(cancel, plan_id=plan.plan_id),
        clock=_never_clock,
    )
    assert replayed_create == replace(created_receipt, replayed=True)
    assert replayed_revalidation == replace(revalidated_receipt, replayed=True)
    assert replayed_cancel == replace(cancelled_receipt, replayed=True)
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 3

    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM cleanup_plan_catalog_state WHERE account_key = ?",
            (ACCOUNT,),
        )
    with pytest.raises(CleanupPlanError) as missing_catalog:
        repository.cleanup_plan_catalog_revision(ACCOUNT)
    assert missing_catalog.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    with pytest.raises(CleanupPlanError) as missing_plan_with_corrupt_catalog:
        repository.cleanup_plan(
            ACCOUNT,
            "cleanup-plan-v1-ffffffff-ffff-4fff-bfff-ffffffffffff",
        )
    assert (
        missing_plan_with_corrupt_catalog.value.code
        is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    )
    for read_operation in (
        repository.cleanup_plan_context,
        repository.cleanup_plan_targets,
    ):
        with pytest.raises(CleanupPlanError) as corrupt_catalog_read:
            read_operation(ACCOUNT)
        assert corrupt_catalog_read.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE

    fixture = canonical_synthetic_map_fixture()
    running = replace(
        fixture.checkpoint,
        scan_id="synthetic-catalog-corruption-running",
        state=SyncState.RUNNING,
        processed_count=0,
        started_at=COMMAND_NOW,
        updated_at=COMMAND_NOW,
    )
    repository.start_full_index(ACCOUNT, running)
    new_create = replace(create, command_id=_command_id(203))
    with pytest.raises(CleanupPlanError) as corrupt_catalog_precedes_inventory:
        repository.create_cleanup_plan(
            ACCOUNT,
            new_create,
            request_fingerprint=cleanup_command_fingerprint(new_create),
            clock=_never_clock,
        )
    assert (
        corrupt_catalog_precedes_inventory.value.code
        is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    )


def test_listing_page_captures_catalog_clock_and_rows_in_one_read_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _installed_repository(tmp_path / "listing-snapshot.db")
    _command, _receipt, plan = _create_plan(repository, command_number=210)
    trace: list[str] = []
    connections: list[sqlite3.Connection] = []
    transaction_states: list[bool] = []
    original_catalog = Repository._cleanup_catalog_revision_conn
    original_listing = Repository._cleanup_listing_item_from_row

    def traced_catalog(connection: sqlite3.Connection, account_key: str) -> int:
        trace.append("catalog")
        connections.append(connection)
        transaction_states.append(connection.in_transaction)
        return original_catalog(connection, account_key)

    def traced_listing(row: sqlite3.Row) -> CleanupPlanListingItem:
        trace.append("page")
        assert connections
        transaction_states.append(connections[0].in_transaction)
        return original_listing(row)

    listing_at = COMMAND_NOW + timedelta(minutes=3)

    def traced_clock() -> datetime:
        trace.append("clock")
        return listing_at

    monkeypatch.setattr(repository, "_cleanup_catalog_revision_conn", traced_catalog)
    monkeypatch.setattr(repository, "_cleanup_listing_item_from_row", traced_listing)
    page = repository.cleanup_plan_listing_page(
        ACCOUNT,
        state=None,
        limit=100,
        offset=0,
        expected_catalog_revision=None,
        clock=traced_clock,
    )

    assert trace == ["catalog", "clock", "page"]
    assert len(connections) == 1
    assert transaction_states == [True, True]
    assert page.listing_as_of == listing_at
    assert page.catalog_revision == 1
    assert tuple(item.plan_id for item in page.items) == (plan.plan_id,)
    assert page.items[0].plan_revision == plan.plan_revision
    assert page.has_more is False


def test_listing_page_serializes_its_clock_with_command_clocks(tmp_path: Path) -> None:
    repository = _installed_repository(tmp_path / "listing-clock-lock.db")
    _command, _receipt, initial_plan = _create_plan(repository, command_number=212)
    next_command = _create_command(repository, command_number=213)
    reader_clock_entered = Event()
    writer_attempting = Event()
    writer_clock_called = Event()
    writer_seen_during_snapshot: list[bool] = []

    def listing_clock() -> datetime:
        reader_clock_entered.set()
        assert writer_attempting.wait(timeout=5)
        writer_seen_during_snapshot.append(writer_clock_called.wait(timeout=1))
        return COMMAND_NOW + timedelta(minutes=2)

    def command_clock() -> datetime:
        writer_clock_called.set()
        return COMMAND_NOW + timedelta(minutes=3)

    def capture_listing() -> CleanupPlanListingPage:
        return repository.cleanup_plan_listing_page(
            ACCOUNT,
            state=None,
            limit=100,
            offset=0,
            expected_catalog_revision=None,
            clock=listing_clock,
        )

    def create_next_plan() -> CleanupPlanReceipt:
        writer_attempting.set()
        return repository.create_cleanup_plan(
            ACCOUNT,
            next_command,
            request_fingerprint=cleanup_command_fingerprint(next_command),
            clock=command_clock,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        listing_future = executor.submit(capture_listing)
        assert reader_clock_entered.wait(timeout=5)
        create_future = executor.submit(create_next_plan)
        page = listing_future.result(timeout=10)
        created = create_future.result(timeout=10)

    assert writer_seen_during_snapshot == [False]
    assert page.listing_as_of == COMMAND_NOW + timedelta(minutes=2)
    assert page.catalog_revision == 1
    assert tuple(item.plan_id for item in page.items) == (initial_plan.plan_id,)
    assert created.replayed is False
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 2


def test_paginated_sql_projections_hydrate_only_the_requested_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _installed_repository(tmp_path / "bounded-pages.db")
    _command, _receipt, plan = _create_plan(repository, command_number=214)
    revalidate = _revalidation_command(repository, plan, command_number=215)
    repository.revalidate_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=plan.plan_id,
        ),
        clock=lambda: COMMAND_NOW + timedelta(minutes=1),
    )
    _create_plan(
        repository,
        command_number=216,
        command_now=COMMAND_NOW + timedelta(minutes=2),
    )
    current = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert current is not None
    assert len(current.members) > 1
    assert len(current.events) > 1

    def forbidden_full_hydration(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a bounded page must not hydrate a full cleanup plan")

    monkeypatch.setattr(repository, "_cleanup_plan_conn", forbidden_full_hydration)
    monkeypatch.setattr(repository, "_cleanup_plans_conn", forbidden_full_hydration)

    hydration_counts = {"listing": 0, "member": 0, "event": 0}
    original_listing = Repository._cleanup_listing_item_from_row
    original_member = Repository._cleanup_member_item_from_row
    original_event = Repository._cleanup_event_from_row

    def listing_item(row: sqlite3.Row) -> object:
        hydration_counts["listing"] += 1
        return original_listing(row)

    def member_item(
        row: sqlite3.Row,
        creation_reasons: dict[str, tuple[CleanupExclusionReason, ...]],
        removal_reasons: dict[tuple[str, int], tuple[CleanupExclusionReason, ...]],
    ) -> object:
        hydration_counts["member"] += 1
        return original_member(row, creation_reasons, removal_reasons)

    def event_item(row: sqlite3.Row) -> object:
        hydration_counts["event"] += 1
        return original_event(row)

    monkeypatch.setattr(repository, "_cleanup_listing_item_from_row", listing_item)
    monkeypatch.setattr(repository, "_cleanup_member_item_from_row", member_item)
    monkeypatch.setattr(repository, "_cleanup_event_from_row", event_item)

    statements: list[str] = []
    original_connect = repository._connect

    @contextmanager
    def traced_connect() -> Iterator[sqlite3.Connection]:
        with original_connect() as connection:
            connection.set_trace_callback(statements.append)
            yield connection

    monkeypatch.setattr(repository, "_connect", traced_connect)

    listing_page = repository.cleanup_plan_listing_page(
        ACCOUNT,
        state=None,
        limit=1,
        offset=0,
        expected_catalog_revision=None,
        clock=lambda: COMMAND_NOW + timedelta(minutes=3),
    )
    member_page = repository.cleanup_plan_member_page(
        ACCOUNT,
        plan.plan_id,
        state="all",
        limit=1,
        offset=0,
        expected_plan_revision=current.plan_revision,
    )
    event_page = repository.cleanup_plan_event_page(
        ACCOUNT,
        plan.plan_id,
        limit=1,
        offset=0,
        expected_plan_revision=current.plan_revision,
    )

    assert len(listing_page.items) == 1
    assert listing_page.has_more is True
    assert member_page is not None
    assert len(member_page.items) == 1
    assert member_page.has_more is True
    assert event_page is not None
    assert len(event_page.items) == 1
    assert event_page.has_more is True
    assert hydration_counts == {"listing": 1, "member": 1, "event": 1}
    normalized_statements = tuple(" ".join(value.split()) for value in statements)
    collection_queries = tuple(
        value
        for value in normalized_statements
        if (
            "SELECT * FROM projected" in value
            or value.startswith("SELECT m.provider_message_id")
            or value.startswith("SELECT revision, event_type")
        )
    )
    assert len(collection_queries) == 3
    assert all("LIMIT 1 OFFSET 0" in value for value in collection_queries)
    assert all("LIMIT 2" not in value for value in normalized_statements)
    exists_queries = tuple(
        value for value in normalized_statements if "SELECT EXISTS" in value
    )
    assert len(exists_queries) == 1
    assert "FROM projected" in exists_queries[0]
    reason_query = next(
        value
        for value in normalized_statements
        if value.startswith("SELECT provider_message_id, reason_context")
    )
    assert "provider_message_id IN (" in reason_query
    reason_ids = reason_query.split("provider_message_id IN (", 1)[1].split(
        ") ORDER BY",
        1,
    )[0]
    assert "," not in reason_ids


def test_paginated_projections_reject_incomplete_member_and_event_ledgers(
    tmp_path: Path,
) -> None:
    member_path = tmp_path / "missing-member-page.db"
    member_repository = _installed_repository(member_path)
    _command, _receipt, member_plan = _create_plan(
        member_repository,
        command_number=217,
    )
    with sqlite3.connect(member_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        deleted = connection.execute(
            "DELETE FROM cleanup_plan_members "
            "WHERE account_key = ? AND plan_id = ? AND message_id = ?",
            (ACCOUNT, member_plan.plan_id, member_plan.members[0].message_id),
        )
        assert deleted.rowcount == 1
    with pytest.raises(CleanupPlanError) as incomplete_members:
        member_repository.cleanup_plan_member_page(
            ACCOUNT,
            member_plan.plan_id,
            state="all",
            limit=500,
            offset=0,
            expected_plan_revision=member_plan.plan_revision,
        )
    assert incomplete_members.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE

    event_path = tmp_path / "missing-event-page.db"
    event_repository = _installed_repository(event_path)
    _command, _receipt, event_plan = _create_plan(
        event_repository,
        command_number=218,
    )
    revalidate = _revalidation_command(event_repository, event_plan, command_number=219)
    event_repository.revalidate_cleanup_plan(
        ACCOUNT,
        event_plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=event_plan.plan_id,
        ),
        clock=lambda: COMMAND_NOW + timedelta(minutes=1),
    )
    current_event_plan = event_repository.cleanup_plan(ACCOUNT, event_plan.plan_id)
    assert current_event_plan is not None
    assert current_event_plan.plan_revision == 2
    with sqlite3.connect(event_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        deleted = connection.execute(
            "DELETE FROM cleanup_plan_events "
            "WHERE account_key = ? AND plan_id = ? AND revision = ?",
            (ACCOUNT, event_plan.plan_id, current_event_plan.plan_revision),
        )
        assert deleted.rowcount == 1
    with pytest.raises(CleanupPlanError) as incomplete_events:
        event_repository.cleanup_plan_event_page(
            ACCOUNT,
            event_plan.plan_id,
            limit=100,
            offset=0,
            expected_plan_revision=current_event_plan.plan_revision,
        )
    assert incomplete_events.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE


def test_paginated_projections_reject_hidden_surplus_member_and_event_ledgers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member_path = tmp_path / "surplus-member-page.db"
    member_repository = _installed_repository(member_path)
    _command, _receipt, member_plan = _create_plan(
        member_repository,
        command_number=222,
    )
    oldest_member = min(
        member_plan.members,
        key=lambda item: (item.received_at, item.message_id),
    )
    surplus_member = CleanupPlanMember(
        provider_message_id="synthetic-surplus-provider-member",
        message_id="message-v1-" + ("f" * 64),
        initial_state=CleanupMemberInitialState.SELECTED,
        received_at=oldest_member.received_at - timedelta(microseconds=1),
        size_estimate_bytes=oldest_member.size_estimate_bytes,
        source_id=oldest_member.source_id,
        flow_id=oldest_member.flow_id,
        read_state=oldest_member.read_state,
        reason_codes=(),
    )
    assert all(
        member.message_id != surplus_member.message_id for member in member_plan.members
    )
    with sqlite3.connect(member_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO cleanup_plan_members("
            "account_key, plan_id, provider_message_id, message_id, member_version, "
            "record_version, initial_state, received_at, size_estimate_bytes, "
            "initial_read_state, frozen_source_id, frozen_flow_id) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
            (
                ACCOUNT,
                member_plan.plan_id,
                surplus_member.provider_message_id,
                surplus_member.message_id,
                surplus_member.version,
                surplus_member.initial_state.value,
                surplus_member.received_at.isoformat(),
                surplus_member.size_estimate_bytes,
                surplus_member.read_state.value,
                surplus_member.source_id,
                surplus_member.flow_id,
            ),
        )
        persisted_member_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM cleanup_plan_members "
                "WHERE account_key = ? AND plan_id = ?",
                (ACCOUNT, member_plan.plan_id),
            ).fetchone()[0]
        )
        header_member_count = int(
            connection.execute(
                "SELECT selected_at_creation_count + excluded_at_creation_count "
                "FROM cleanup_plans WHERE account_key = ? AND plan_id = ?",
                (ACCOUNT, member_plan.plan_id),
            ).fetchone()[0]
        )
    assert persisted_member_count == len(member_plan.members) + 1
    assert header_member_count == len(member_plan.members)
    member_hydration_count = 0
    original_member_mapper = member_repository._cleanup_member_item_from_row

    def count_member_hydration(*args: object, **kwargs: object) -> object:
        nonlocal member_hydration_count
        member_hydration_count += 1
        return original_member_mapper(*args, **kwargs)

    monkeypatch.setattr(
        member_repository,
        "_cleanup_member_item_from_row",
        count_member_hydration,
    )
    with pytest.raises(CleanupPlanError) as surplus_members:
        member_repository.cleanup_plan_member_page(
            ACCOUNT,
            member_plan.plan_id,
            state="all",
            limit=1,
            offset=0,
            expected_plan_revision=member_plan.plan_revision,
        )
    assert surplus_members.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    assert member_hydration_count == 0

    event_path = tmp_path / "surplus-event-page.db"
    event_repository = _installed_repository(event_path)
    _command, _receipt, event_plan = _create_plan(
        event_repository,
        command_number=223,
    )
    surplus_event = CleanupPlanEvent(
        revision=event_plan.plan_revision + 1,
        type=CleanupEventType.REVALIDATED,
        recorded_at=event_plan.created_at + timedelta(microseconds=1),
        state=event_plan.persisted_state,
        observed_map_revision=event_plan.created_from_map_revision,
        observed_policy_revision=event_plan.created_from_policy_revision,
        removed_count=0,
        remaining_count=event_plan.current_eligible_count,
    )
    with sqlite3.connect(event_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO cleanup_plan_events("
            "account_key, plan_id, revision, event_version, event_type, state, "
            "recorded_at, observed_map_revision, observed_policy_revision, "
            "removed_count, remaining_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ACCOUNT,
                event_plan.plan_id,
                surplus_event.revision,
                surplus_event.version,
                surplus_event.type.value,
                surplus_event.state.value,
                surplus_event.recorded_at.isoformat(),
                surplus_event.observed_map_revision,
                surplus_event.observed_policy_revision,
                surplus_event.removed_count,
                surplus_event.remaining_count,
            ),
        )
        persisted_event_count, persisted_max_revision = connection.execute(
            "SELECT COUNT(*), MAX(revision) FROM cleanup_plan_events "
            "WHERE account_key = ? AND plan_id = ?",
            (ACCOUNT, event_plan.plan_id),
        ).fetchone()
        header_plan_revision = int(
            connection.execute(
                "SELECT plan_revision FROM cleanup_plans "
                "WHERE account_key = ? AND plan_id = ?",
                (ACCOUNT, event_plan.plan_id),
            ).fetchone()[0]
        )
    assert int(persisted_event_count) == event_plan.plan_revision + 1
    assert int(persisted_max_revision) == event_plan.plan_revision + 1
    assert header_plan_revision == event_plan.plan_revision
    event_hydration_count = 0
    original_event_mapper = event_repository._cleanup_event_from_row

    def count_event_hydration(*args: object, **kwargs: object) -> object:
        nonlocal event_hydration_count
        event_hydration_count += 1
        return original_event_mapper(*args, **kwargs)

    monkeypatch.setattr(
        event_repository,
        "_cleanup_event_from_row",
        count_event_hydration,
    )
    with pytest.raises(CleanupPlanError) as surplus_events:
        event_repository.cleanup_plan_event_page(
            ACCOUNT,
            event_plan.plan_id,
            limit=1,
            offset=0,
            expected_plan_revision=event_plan.plan_revision,
        )
    assert surplus_events.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    assert event_hydration_count == 0


@pytest.mark.parametrize(
    "corruption",
    ("missing_plus_scope", "protection_changed_alone"),
)
def test_member_pages_reject_contextually_invalid_removal_reasons(
    tmp_path: Path,
    corruption: str,
) -> None:
    path = tmp_path / f"invalid-page-reasons-{corruption}.db"
    repository = _installed_repository(path)
    _command, _receipt, plan = _create_plan(repository, command_number=220)
    selected = next(
        member
        for member in plan.members
        if member.initial_state is CleanupMemberInitialState.SELECTED
    )
    repository.delete_indexed_messages(ACCOUNT, (selected.provider_message_id,))
    revalidate = _revalidation_command(repository, plan, command_number=221)
    repository.revalidate_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        revalidate,
        request_fingerprint=cleanup_command_fingerprint(
            revalidate,
            plan_id=plan.plan_id,
        ),
        clock=lambda: COMMAND_NOW + timedelta(minutes=1),
    )
    current = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert current is not None
    assert len(current.removals) == 1
    removal = current.removals[0]
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        deleted = connection.execute(
            "DELETE FROM cleanup_plan_member_reasons "
            "WHERE account_key = ? AND plan_id = ? "
            "AND provider_message_id = ? AND reason_context = 'removal'",
            (ACCOUNT, plan.plan_id, removal.provider_message_id),
        )
        assert deleted.rowcount >= 1
        if corruption == "missing_plus_scope":
            connection.executemany(
                "INSERT INTO cleanup_plan_member_reasons("
                "account_key, plan_id, provider_message_id, reason_context, "
                "removal_revision, reason_order, reason_code, reason_version) "
                "VALUES (?, ?, ?, 'removal', ?, ?, ?, 1)",
                (
                    (
                        ACCOUNT,
                        plan.plan_id,
                        removal.provider_message_id,
                        removal.revision,
                        18,
                        "missing_after_creation",
                    ),
                    (
                        ACCOUNT,
                        plan.plan_id,
                        removal.provider_message_id,
                        removal.revision,
                        19,
                        "scope_changed",
                    ),
                ),
            )
        else:
            connection.execute(
                "INSERT INTO cleanup_plan_member_reasons("
                "account_key, plan_id, provider_message_id, reason_context, "
                "removal_revision, reason_order, reason_code, reason_version) "
                "VALUES (?, ?, ?, 'removal', ?, 20, 'protection_changed', 1)",
                (
                    ACCOUNT,
                    plan.plan_id,
                    removal.provider_message_id,
                    removal.revision,
                ),
            )
    with pytest.raises(CleanupPlanError) as invalid_reasons:
        repository.cleanup_plan_member_page(
            ACCOUNT,
            plan.plan_id,
            state="removed",
            limit=500,
            offset=0,
            expected_plan_revision=current.plan_revision,
        )
    assert invalid_reasons.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE


def test_commands_enforce_replay_cas_inventory_and_terminal_account_delete(
    tmp_path: Path,
) -> None:
    path = tmp_path / "command-order.db"
    repository = _installed_repository(path)
    create, created_receipt, plan = _create_plan(repository, command_number=300)
    initial_counts = _cleanup_counts(path)

    cross_route = CancelCleanupPlanCommand(
        command_id=create.command_id,
        expected_plan_revision=plan.plan_revision,
    )
    with pytest.raises(CleanupPlanError) as conflict:
        repository.cancel_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            cross_route,
            request_fingerprint=cleanup_command_fingerprint(
                cross_route,
                plan_id=plan.plan_id,
            ),
            clock=_never_clock,
        )
    assert conflict.value.code is CleanupPlanErrorCode.COMMAND_ID_CONFLICT

    current = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert current is not None
    stale_revalidate = replace(
        _revalidation_command(repository, current, command_number=301),
        expected_plan_revision=current.plan_revision + 1,
    )
    with pytest.raises(CleanupPlanError) as stale_revalidation:
        repository.revalidate_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            stale_revalidate,
            request_fingerprint=cleanup_command_fingerprint(
                stale_revalidate,
                plan_id=plan.plan_id,
            ),
            clock=lambda: COMMAND_NOW + timedelta(minutes=1),
        )
    assert stale_revalidation.value.code is CleanupPlanErrorCode.PLAN_REVISION_CONFLICT
    stale_cancel = replace(
        _cancel_command(current, command_number=302),
        expected_plan_revision=current.plan_revision + 1,
    )
    with pytest.raises(CleanupPlanError) as stale_cancellation:
        repository.cancel_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            stale_cancel,
            request_fingerprint=cleanup_command_fingerprint(
                stale_cancel,
                plan_id=plan.plan_id,
            ),
            clock=lambda: COMMAND_NOW + timedelta(minutes=1),
        )
    assert stale_cancellation.value.code is CleanupPlanErrorCode.PLAN_REVISION_CONFLICT
    assert _cleanup_counts(path) == initial_counts

    fixture = canonical_synthetic_map_fixture()
    running = replace(
        fixture.checkpoint,
        scan_id="synthetic-map-running-v1",
        state=SyncState.RUNNING,
        processed_count=0,
        started_at=COMMAND_NOW,
        updated_at=COMMAND_NOW,
    )
    repository.start_full_index(ACCOUNT, running)
    replay = repository.create_cleanup_plan(
        ACCOUNT,
        create,
        request_fingerprint=cleanup_command_fingerprint(create),
        clock=_never_clock,
    )
    assert replay == replace(created_receipt, replayed=True)
    new_create = replace(create, command_id=_command_id(303))
    with pytest.raises(CleanupPlanError) as incomplete_create:
        repository.create_cleanup_plan(
            ACCOUNT,
            new_create,
            request_fingerprint=cleanup_command_fingerprint(new_create),
            clock=lambda: COMMAND_NOW + timedelta(minutes=2),
        )
    assert incomplete_create.value.code is CleanupPlanErrorCode.INVENTORY_INCOMPLETE
    current = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert current is not None
    incomplete_revalidate = RevalidateCleanupPlanCommand(
        command_id=_command_id(304),
        expected_plan_revision=current.plan_revision,
        expected_map_revision=create.expected_map_revision,
        expected_policy_revision=create.expected_policy_revision,
    )
    with pytest.raises(CleanupPlanError) as incomplete_revalidation:
        repository.revalidate_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            incomplete_revalidate,
            request_fingerprint=cleanup_command_fingerprint(
                incomplete_revalidate,
                plan_id=plan.plan_id,
            ),
            clock=lambda: COMMAND_NOW + timedelta(minutes=2),
        )
    assert incomplete_revalidation.value.code is CleanupPlanErrorCode.INVENTORY_INCOMPLETE

    cancel = _cancel_command(current, command_number=305)
    cancelled = repository.cancel_cleanup_plan(
        ACCOUNT,
        plan.plan_id,
        cancel,
        request_fingerprint=cleanup_command_fingerprint(cancel, plan_id=plan.plan_id),
        clock=lambda: COMMAND_NOW + timedelta(minutes=2),
    )
    assert cancelled.status is CleanupCommandStatus.CANCELLED
    repository.delete_account_index(ACCOUNT)
    assert repository.map_input_snapshot(ACCOUNT).account_exists is False
    assert _cleanup_counts(path) == {table: 0 for table in CLEANUP_TABLES}

    with pytest.raises(CleanupPlanError) as deleted_create:
        repository.create_cleanup_plan(
            ACCOUNT,
            create,
            request_fingerprint=cleanup_command_fingerprint(create),
            clock=lambda: COMMAND_NOW + timedelta(minutes=3),
        )
    assert deleted_create.value.code is CleanupPlanErrorCode.ACCOUNT_UNAVAILABLE
    with pytest.raises(CleanupPlanError) as deleted_cancel:
        repository.cancel_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            cancel,
            request_fingerprint=cleanup_command_fingerprint(
                cancel,
                plan_id=plan.plan_id,
            ),
            clock=lambda: COMMAND_NOW + timedelta(minutes=3),
        )
    assert deleted_cancel.value.code is CleanupPlanErrorCode.PLAN_NOT_FOUND
    assert repository.map_input_snapshot(ACCOUNT).account_exists is False


def test_concurrent_create_replays_once_and_revalidate_cancel_have_one_winner(
    tmp_path: Path,
) -> None:
    path = tmp_path / "concurrent.db"
    repository = _installed_repository(path)
    create = _create_command(repository, command_number=400)
    create_fingerprint = cleanup_command_fingerprint(create)
    create_barrier = Barrier(2)
    clock_lock = Lock()
    clock_reads = 0

    def counted_clock() -> datetime:
        nonlocal clock_reads
        with clock_lock:
            clock_reads += 1
        return COMMAND_NOW

    def concurrent_create() -> CleanupPlanReceipt:
        create_barrier.wait(timeout=5)
        return repository.create_cleanup_plan(
            ACCOUNT,
            create,
            request_fingerprint=create_fingerprint,
            clock=counted_clock,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        created = tuple(executor.map(lambda _value: concurrent_create(), range(2)))

    assert {receipt.replayed for receipt in created} == {False, True}
    assert len({receipt.plan_id for receipt in created}) == 1
    assert clock_reads == 1
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 1
    plan = repository.cleanup_plan(ACCOUNT, created[0].plan_id)
    assert plan is not None
    revalidate = _revalidation_command(repository, plan, command_number=401)
    cancel = _cancel_command(plan, command_number=402)
    transition_barrier = Barrier(2)

    def concurrent_revalidate() -> CleanupPlanReceipt | CleanupPlanErrorCode:
        transition_barrier.wait(timeout=5)
        try:
            return repository.revalidate_cleanup_plan(
                ACCOUNT,
                plan.plan_id,
                revalidate,
                request_fingerprint=cleanup_command_fingerprint(
                    revalidate,
                    plan_id=plan.plan_id,
                ),
                clock=lambda: COMMAND_NOW + timedelta(minutes=1),
            )
        except CleanupPlanError as error:
            return error.code

    def concurrent_cancel() -> CleanupPlanReceipt | CleanupPlanErrorCode:
        transition_barrier.wait(timeout=5)
        try:
            return repository.cancel_cleanup_plan(
                ACCOUNT,
                plan.plan_id,
                cancel,
                request_fingerprint=cleanup_command_fingerprint(
                    cancel,
                    plan_id=plan.plan_id,
                ),
                clock=lambda: COMMAND_NOW + timedelta(minutes=1),
            )
        except CleanupPlanError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(concurrent_revalidate),
            executor.submit(concurrent_cancel),
        )
        outcomes = tuple(future.result(timeout=10) for future in futures)

    receipts = tuple(item for item in outcomes if isinstance(item, CleanupPlanReceipt))
    errors = tuple(item for item in outcomes if isinstance(item, CleanupPlanErrorCode))
    assert len(receipts) == 1
    assert len(errors) == 1
    assert errors[0] in (
        CleanupPlanErrorCode.PLAN_REVISION_CONFLICT,
        CleanupPlanErrorCode.INVALID_TRANSITION,
    )
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 2
    final = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert final is not None
    assert final.plan_revision == 2
    assert len(final.events) == 2

    _create, _receipt, expiring_plan = _create_plan(repository, command_number=403)
    expiring_revalidate = _revalidation_command(
        repository,
        expiring_plan,
        command_number=404,
    )
    expiring_cancel = _cancel_command(expiring_plan, command_number=405)
    expiry_barrier = Barrier(2)

    def concurrent_expired_revalidate() -> CleanupPlanReceipt | CleanupPlanErrorCode:
        expiry_barrier.wait(timeout=5)
        try:
            return repository.revalidate_cleanup_plan(
                ACCOUNT,
                expiring_plan.plan_id,
                expiring_revalidate,
                request_fingerprint=cleanup_command_fingerprint(
                    expiring_revalidate,
                    plan_id=expiring_plan.plan_id,
                ),
                clock=lambda: expiring_plan.expires_at,
            )
        except CleanupPlanError as error:
            return error.code

    def concurrent_expired_cancel() -> CleanupPlanReceipt | CleanupPlanErrorCode:
        expiry_barrier.wait(timeout=5)
        try:
            return repository.cancel_cleanup_plan(
                ACCOUNT,
                expiring_plan.plan_id,
                expiring_cancel,
                request_fingerprint=cleanup_command_fingerprint(
                    expiring_cancel,
                    plan_id=expiring_plan.plan_id,
                ),
                clock=lambda: expiring_plan.expires_at,
            )
        except CleanupPlanError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        expiry_futures = (
            executor.submit(concurrent_expired_revalidate),
            executor.submit(concurrent_expired_cancel),
        )
        expiry_outcomes = tuple(future.result(timeout=10) for future in expiry_futures)

    assert expiry_outcomes == (
        CleanupPlanErrorCode.PLAN_EXPIRED,
        CleanupPlanErrorCode.PLAN_EXPIRED,
    )
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 3
    still_expired = repository.cleanup_plan(ACCOUNT, expiring_plan.plan_id)
    assert still_expired is not None
    assert still_expired.plan_revision == 1
    assert len(still_expired.events) == 1


def test_aggregate_overflow_rejects_the_command_without_any_repository_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "aggregate-overflow.db"
    repository = _installed_repository(path)
    command = _create_command(repository, command_number=490)
    before = _cleanup_counts(path)
    monkeypatch.setattr(cleanup_domain, "MAX_AGGREGATE_SIZE_ESTIMATE_BYTES", 1)

    with pytest.raises(CleanupPlanError) as overflow:
        repository.create_cleanup_plan(
            ACCOUNT,
            command,
            request_fingerprint=cleanup_command_fingerprint(command),
            clock=lambda: COMMAND_NOW,
        )

    assert overflow.value.code is CleanupPlanErrorCode.STUDY_UNAVAILABLE
    assert _cleanup_counts(path) == before
    assert repository.cleanup_plans(ACCOUNT) == ()
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 0


@pytest.mark.parametrize(
    "failure_method",
    (
        "_insert_cleanup_plan_row_conn",
        "_insert_cleanup_plan_targets_conn",
        "_insert_cleanup_plan_members_conn",
        "_insert_cleanup_plan_creation_reasons_conn",
        "_insert_cleanup_plan_samples_conn",
        "_insert_cleanup_plan_event_conn",
        "_insert_cleanup_plan_receipt_conn",
        "_advance_cleanup_plan_catalog_conn",
    ),
)
def test_creation_rolls_back_every_normalized_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_method: str,
) -> None:
    path = tmp_path / f"creation-rollback-{failure_method}.db"
    repository = _installed_repository(path)
    command = _create_command(repository, command_number=500)
    before = _cleanup_counts(path)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise _InjectedFailure(failure_method)

    monkeypatch.setattr(repository, failure_method, fail)
    with pytest.raises(_InjectedFailure):
        repository.create_cleanup_plan(
            ACCOUNT,
            command,
            request_fingerprint=cleanup_command_fingerprint(command),
            clock=lambda: COMMAND_NOW,
        )

    assert _cleanup_counts(path) == before
    assert repository.cleanup_plans(ACCOUNT) == ()
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 0


@pytest.mark.parametrize(
    "failure_method",
    (
        "_insert_cleanup_plan_removals_conn",
        "_insert_cleanup_plan_removal_reasons_conn",
        "_update_cleanup_plan_aggregate_conn",
        "_insert_cleanup_plan_receipt_conn",
        "_advance_cleanup_plan_catalog_conn",
    ),
)
def test_revalidation_rolls_back_removals_ledger_receipt_and_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_method: str,
) -> None:
    path = tmp_path / f"revalidation-rollback-{failure_method}.db"
    repository = _installed_repository(path)
    _create, _receipt, plan = _create_plan(repository, command_number=600)
    selected = next(
        member
        for member in plan.members
        if member.initial_state is CleanupMemberInitialState.SELECTED
    )
    repository.delete_indexed_messages(ACCOUNT, (selected.provider_message_id,))
    before_plan = repository.cleanup_plan(ACCOUNT, plan.plan_id)
    assert before_plan is not None
    command = _revalidation_command(repository, before_plan, command_number=601)
    before_counts = _cleanup_counts(path)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise _InjectedFailure(failure_method)

    monkeypatch.setattr(repository, failure_method, fail)
    with pytest.raises(_InjectedFailure):
        repository.revalidate_cleanup_plan(
            ACCOUNT,
            plan.plan_id,
            command,
            request_fingerprint=cleanup_command_fingerprint(
                command,
                plan_id=plan.plan_id,
            ),
            clock=lambda: COMMAND_NOW + timedelta(minutes=1),
        )

    assert _cleanup_counts(path) == before_counts
    assert repository.cleanup_plan(ACCOUNT, plan.plan_id) == before_plan
    assert repository.cleanup_plan_catalog_revision(ACCOUNT) == 1
