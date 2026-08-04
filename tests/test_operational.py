from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from hermes_memory_router.config import new_config
from hermes_memory_router.exceptions import ConfigurationError
from hermes_memory_router.health import collect_health
from hermes_memory_router.policy import HINDSIGHT_MNEMOSYNE
from hermes_memory_router.store import RouterStore


def make_store(tmp_path: Path) -> RouterStore:
    return RouterStore(
        tmp_path / "router.db",
        namespace="project",
        environment="staging",
        profile_fingerprint="profile-a",
        strict_binding=True,
    )


def test_database_info_reports_identity_sizes_and_oldest_incomplete_delivery(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    record_id, _ = store.create_record(
        namespace="project",
        environment="staging",
        kind="checkpoint",
        content="safe test data",
        metadata={},
        backends=["hindsight"],
    )
    delivery = store.due_deliveries(1)[0]
    store.fail(int(delivery["id"]), error="controlled", next_attempt_at=0)

    info = store.database_info()

    assert info["schema_version"] == 2
    assert info["binding"] == {
        "namespace": "project",
        "environment": "staging",
        "profile": "profile-a",
    }
    assert info["deliveries"]["failed"] == 1
    assert info["deliveries"]["pending"] == 0
    assert info["oldest_incomplete_delivery"] is not None
    assert info["size_bytes"] > 0
    assert "safe test data" not in json.dumps(info)
    assert store.delivery_states(record_id)["hindsight:retain"] == "failed"
    store.close()


def test_database_integrity_check_reports_corruption(tmp_path: Path) -> None:
    path = tmp_path / "router.db"
    store = make_store(tmp_path)
    store.close()
    path.write_bytes(b"not a sqlite database")

    result = RouterStore.check_database(path)

    assert result["ok"] is False
    assert result["integrity"] != "ok"


def test_online_backup_writes_manifest_and_sha256(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    output = tmp_path / "backup.sqlite"

    manifest = store.backup_database(output)

    assert output.exists()
    assert sqlite3.connect(output).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    assert manifest["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert manifest["binding"]["namespace"] == "project"
    assert RouterStore.verify_backup_manifest(output)["ok"] is True
    store.close()


def test_vacuum_requires_explicit_confirmation(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    with pytest.raises(ConfigurationError, match="--yes"):
        store.vacuum_database(confirm=False)

    result = store.vacuum_database(confirm=True)
    assert result["vacuumed"] is True
    store.close()


def test_health_states_distinguish_warning_degraded_and_unsafe(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    config = new_config(namespace="project", environment="staging", policy="hindsight-only")
    config.routing.start_worker = False
    healthy = collect_health(
        config=config,
        store=store,
        expected_profile="profile-a",
        backends={"hindsight": {"ok": True, "version": "1.2.3"}},
        worker_alive=True,
    )
    assert healthy["state"] == "healthy"

    record_id, _ = store.create_record(
        namespace="project",
        environment="staging",
        kind="turn",
        content="queued",
        metadata={},
        backends=["hindsight"],
    )
    warning = collect_health(
        config=config,
        store=store,
        expected_profile="profile-a",
        backends={"hindsight": {"ok": True}},
        worker_alive=True,
    )
    assert warning["state"] == "warning"

    delivery = store.due_deliveries(1)[0]
    store.fail(int(delivery["id"]), error="controlled", next_attempt_at=0, dead=True)
    degraded = collect_health(
        config=config,
        store=store,
        expected_profile="profile-a",
        backends={"hindsight": {"ok": False, "error": "down"}},
        worker_alive=True,
    )
    assert degraded["state"] == "degraded"

    unsafe = collect_health(
        config=config,
        store=store,
        expected_profile="wrong-profile",
        backends={"hindsight": {"ok": True}},
        worker_alive=True,
    )
    assert unsafe["state"] == "unsafe"
    assert unsafe["exit_code"] == 3
    assert store.delivery_states(record_id)["hindsight:retain"] == "dead"
    store.close()


def test_health_reports_missing_optional_mnemosyne_as_warning(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    config = new_config(namespace="project", environment="staging", policy="hindsight-only")
    config.routing.start_worker = False

    payload = collect_health(
        config=config,
        store=store,
        expected_profile="profile-a",
        backends={"hindsight": {"ok": True}},
        worker_alive=True,
        optional_mnemosyne={"enabled": False, "installed": False, "version": None},
    )

    assert payload["state"] == "warning"
    assert any("mnemosyne is not installed" in warning for warning in payload["warnings"])
    store.close()


def test_health_marks_configured_unhealthy_mnemosyne_degraded(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    config = new_config(namespace="project", environment="staging", policy=HINDSIGHT_MNEMOSYNE)
    config.routing.start_worker = False

    payload = collect_health(
        config=config,
        store=store,
        expected_profile="profile-a",
        backends={
            "hindsight": {"ok": True},
            "mnemosyne": {"ok": False, "error": "down"},
        },
        worker_alive=True,
        optional_mnemosyne={"enabled": True, "installed": True, "version": "3.15.0"},
    )

    assert payload["state"] == "degraded"
    assert any("mnemosyne" in reason for reason in payload["degraded"])
    store.close()


def test_database_info_detects_namespace_environment_and_profile_mismatches(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    config = new_config(namespace="other", environment="production", policy="hindsight-only")
    config.routing.start_worker = False

    payload = collect_health(
        config=config,
        store=store,
        expected_profile="profile-b",
        backends={"hindsight": {"ok": True}},
        worker_alive=True,
    )

    assert payload["state"] == "unsafe"
    assert {"namespace", "environment", "profile"} <= set(payload["binding"]["mismatches"])
    store.close()


def test_backup_manifest_verification_rejects_tampering(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    output = tmp_path / "backup.sqlite"
    store.backup_database(output)
    output.write_bytes(output.read_bytes() + b"tampered")

    verification = RouterStore.verify_backup_manifest(output)

    assert verification["ok"] is False
    assert verification["sha256_matches"] is False
    store.close()


def test_database_check_does_not_expose_record_content(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.create_record(
        namespace="project",
        environment="staging",
        kind="turn",
        content="private memory content",
        metadata={},
        backends=[],
    )
    store.close()

    result = RouterStore.check_database(tmp_path / "router.db")

    assert result["ok"] is True
    assert "private memory content" not in json.dumps(result)
