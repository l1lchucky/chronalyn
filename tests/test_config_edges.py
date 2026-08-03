import json

import pytest

from hermes_memory_router.config import RouterConfig, load_config
from hermes_memory_router.exceptions import ConfigurationError


@pytest.mark.parametrize(
    "section,payload",
    [
        ("hindsight", {"recall_budget": "huge"}),
        ("hindsight", {"timeout_seconds": 0}),
        ("hindsight", {"recall_max_tokens": 0}),
        ("mnemosyne", {"top_k": 0}),
        ("redaction", {"mode": "maybe"}),
        ("redaction", {"max_record_chars": 1}),
        ("redaction", {"custom_patterns": ["("]}),
        ("routing", {"fallback_max_chars": 1}),
        ("routing", {"worker_poll_seconds": 0}),
        ("routing", {"worker_batch_size": 0}),
        ("routing", {"automatic_write_contexts": ["unknown"]}),
    ],
)
def test_invalid_nested_config_is_rejected(tmp_path, section, payload):
    data = {
        "namespace": "project",
        "environment": "staging",
        "hindsight": {"bank_id": "primary-bank"},
        "mnemosyne": {"bank": "checkpoint-bank"},
        section: payload,
    }
    # Preserve mandatory bank values when the parametrized section overwrites them.
    if section == "hindsight":
        data["hindsight"] = {"bank_id": "primary-bank", **payload}
    if section == "mnemosyne":
        data["mnemosyne"] = {"bank": "checkpoint-bank", **payload}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ConfigurationError):
        load_config(path)


def test_invalid_root_and_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ConfigurationError):
        load_config(missing)
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    with pytest.raises(ConfigurationError):
        load_config(bad)


def test_resolved_custom_state_db(tmp_path, monkeypatch):
    config = RouterConfig(namespace="project", environment="dev", state_db="$HMR_TEST_DB/router.db")
    config.hindsight.bank_id = "project-dev"
    config.mnemosyne.bank = "project-dev-checkpoints"
    monkeypatch.setenv("HMR_TEST_DB", str(tmp_path))
    assert config.resolved_state_db(tmp_path) == tmp_path / "router.db"
