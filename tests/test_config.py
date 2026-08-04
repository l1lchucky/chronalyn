import json

import pytest

from chronalyn.config import load_config, write_default_config
from chronalyn.exceptions import ConfigurationError


def test_default_config_isolated(tmp_path):
    path = tmp_path / "config.json"
    write_default_config(path, namespace="acme", environment="production")
    config = load_config(path)
    assert config.hindsight.bank_id == "acme-production"
    assert config.mnemosyne.bank == "acme-production-checkpoints"
    assert config.hindsight.bank_id != config.mnemosyne.bank


def test_unknown_keys_are_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"namespace": "a", "environment": "b", "oops": True}))
    with pytest.raises(ConfigurationError, match="Unknown"):
        load_config(path)


def test_unsafe_bank_name_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "namespace": "a",
                "environment": "b",
                "hindsight": {"bank_id": "../escape"},
                "mnemosyne": {"bank": "safe-checkpoints"},
            }
        )
    )
    with pytest.raises(ConfigurationError):
        load_config(path)


def test_equal_bank_names_rejected(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "namespace": "a",
                "environment": "b",
                "hindsight": {"bank_id": "same"},
                "mnemosyne": {"bank": "same"},
            }
        )
    )
    with pytest.raises(ConfigurationError, match="different"):
        load_config(path)
