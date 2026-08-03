from hermes_memory_router.factory import _read_profile_env_value


def test_profile_env_value_is_exact_and_non_shell(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# comment\n"
        "OTHER=value\n"
        "HINDSIGHT_API_KEY=secret-value\n"
        "HINDSIGHT_API_KEY_SUFFIX=wrong\n"
    )
    assert _read_profile_env_value(path, "HINDSIGHT_API_KEY") == "secret-value"
    assert _read_profile_env_value(path, "MISSING") == ""


def test_profile_env_missing_is_empty(tmp_path):
    assert _read_profile_env_value(tmp_path / "missing", "KEY") == ""
