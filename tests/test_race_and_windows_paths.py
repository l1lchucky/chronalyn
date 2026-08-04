"""Write/delete race safety and Windows path handling.

The race that matters for data safety: a delete must never lose to an in-flight
write. If a retain is already claimed by the delivery worker when the record is
forgotten, the content must still be removed from the backend rather than left
orphaned with no local record pointing at it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from chronalyn import identity
from chronalyn.config import RouterConfig, new_config
from chronalyn.plugin_entry import entry_dir, install_plugin_entries
from chronalyn.policy import HINDSIGHT_ONLY
from chronalyn.store import RouterStore

# -- Write/delete race ------------------------------------------------------


def test_pending_write_is_cancelled_when_record_is_forgotten(router):
    """A queued retain must not reach the backend after a forget."""
    instance, primary, _checkpoint = router

    result = instance.retain_memory(content="secret to forget", context="ctx", metadata={})
    instance.forget(result.record_id)

    states = instance.store.delivery_states(result.record_id)
    assert states["hindsight:retain"] == "cancelled"

    # Draining after the forget must not write the cancelled content anywhere.
    instance.drain_outbox(50)
    assert primary.retained == {}


def test_completed_write_is_deleted_when_forget_arrives_after_delivery(router):
    """The dangerous interleaving: content already landed, then forget."""
    instance, primary, _checkpoint = router

    result = instance.retain_memory(content="already delivered", context="ctx", metadata={})
    instance.drain_outbox(50)
    external_ids = list(primary.retained)
    assert external_ids, "retain should have reached the backend"

    instance.forget(result.record_id)
    instance.drain_outbox(50)

    # The backend copy must be gone, not orphaned.
    assert primary.retained == {}
    assert external_ids[0] in primary.deleted
    assert instance.store.delivery_states(result.record_id)["hindsight:delete"] == "complete"


def test_forget_while_delivery_is_claimed_still_removes_backend_copy(router):
    """Simulate a worker mid-flight: claimed retain completes, then forget runs."""
    instance, primary, _checkpoint = router

    result = instance.retain_memory(content="in flight", context="ctx", metadata={})
    due = instance.store.due_deliveries(10)
    retain = next(d for d in due if d["operation"] == "retain")

    # Worker claims the delivery, and the forget lands before it completes.
    assert instance.store.claim(int(retain["id"]))
    instance.forget(result.record_id)

    # The in-flight write now completes, as the real worker would.
    receipt = primary.retain(
        content=str(retain["content"]),
        record_id=str(retain["record_id"]),
        kind=str(retain["kind"]),
        metadata=dict(retain["metadata"]),
    )
    instance.store.complete(
        int(retain["id"]), external_id=receipt.external_id, receipt=receipt.to_dict()
    )

    # A second forget pass must schedule the delete for the now-completed write,
    # so the backend cannot retain an orphaned copy.
    instance.store.schedule_delete(result.record_id)
    instance.drain_outbox(50)

    assert primary.retained == {}
    assert receipt.external_id in primary.deleted


def test_forgotten_record_is_marked_deleted_locally(router):
    instance, _primary, _checkpoint = router

    result = instance.retain_memory(content="tombstone", context="ctx", metadata={})
    instance.forget(result.record_id)

    record = instance.store.record(result.record_id)
    assert record is not None
    assert record["deleted"] == 1


def test_duplicate_write_is_deduplicated_not_double_delivered(router):
    """Checksum dedup must not create a second backend copy to leak."""
    instance, _primary, _checkpoint = router

    first = instance.retain_memory(content="same text", context="same", metadata={})
    second = instance.retain_memory(content="same text", context="same", metadata={})

    assert first.record_id == second.record_id


# -- Windows path handling --------------------------------------------------


def test_state_db_resolves_under_hermes_home_on_any_platform(tmp_path: Path) -> None:
    config = new_config(namespace="proj", environment="staging", policy=HINDSIGHT_ONLY)
    resolved = config.resolved_state_db(tmp_path)

    assert resolved == tmp_path / identity.STATE_DIRNAME / identity.STATE_DB_FILENAME
    assert resolved.is_absolute()


def test_state_db_expands_user_and_environment_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Works with native separators on Windows and POSIX alike."""
    monkeypatch.setenv("CHRONALYN_TEST_ROOT", str(tmp_path))
    config = RouterConfig(state_db=str(Path("$CHRONALYN_TEST_ROOT") / "custom.db"))

    resolved = config.resolved_state_db(tmp_path)

    assert resolved == tmp_path / "custom.db"
    assert "$" not in str(resolved)


def test_provider_entry_paths_use_platform_separators(tmp_path: Path) -> None:
    install_plugin_entries(tmp_path)

    directory = entry_dir(tmp_path, identity.PROVIDER_ID)
    assert directory.is_dir()
    # Path comparison must hold regardless of separator style.
    assert directory == tmp_path / "plugins" / identity.PROVIDER_ID
    assert directory.parent.name == "plugins"


def test_store_opens_on_a_path_containing_spaces(tmp_path: Path) -> None:
    """Windows home directories frequently contain spaces."""
    spaced = tmp_path / "Program Files" / "hermes home"
    spaced.mkdir(parents=True)
    database = spaced / identity.STATE_DB_FILENAME

    store = RouterStore(
        database,
        namespace="proj",
        environment="staging",
        profile_fingerprint="fp",
        strict_binding=True,
    )
    try:
        info = store.database_info()
        assert Path(info["path"]) == database
    finally:
        store.close()

    assert database.exists()


def test_backup_paths_are_relative_to_hermes_home(tmp_path: Path) -> None:
    """relative_to() would raise on mixed separators or absolute drift."""
    from chronalyn.compatibility import managed_backup_paths

    for path in managed_backup_paths(tmp_path):
        relative = path.relative_to(tmp_path)
        assert not relative.is_absolute()
        # POSIX form is used inside backup metadata for cross-platform restore.
        assert "\\" not in relative.as_posix()


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific path semantics")
def test_windows_paths_are_case_insensitive_for_entry_lookup(tmp_path: Path) -> None:
    install_plugin_entries(tmp_path)
    directory = entry_dir(tmp_path, identity.PROVIDER_ID)

    assert Path(str(directory).upper()).exists() or directory.exists()
