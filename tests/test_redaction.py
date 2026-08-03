import pytest

from hermes_memory_router.config import RedactionConfig
from hermes_memory_router.exceptions import SecretDetected
from hermes_memory_router.redaction import sanitize


FAKE_BEARER = "-".join(("demo", "token", "not", "secret")) * 2


@pytest.mark.parametrize("text,secret", [
    ("Authorization: Bearer " + FAKE_BEARER, FAKE_BEARER),
    ("API_KEY=super-secret-value", "super-secret-value"),
    ("postgresql://user:pass@localhost/db", "user:pass@"),
    ("eyJabcdefghij.abcdefghij.abcdefghij", "eyJabcdefghij"),
    ("https://example.test/x?token=hello&safe=yes", "token=hello"),
])
def test_redacts_common_secrets(text, secret):
    result = sanitize(text, RedactionConfig())
    assert secret not in result.text
    assert result.findings


def test_reject_mode_fails_closed():
    config = RedactionConfig(mode="reject")
    fake_secret = "hunter" + "2"
    with pytest.raises(SecretDetected):
        sanitize("password=" + fake_secret, config)


def test_content_is_bounded():
    config = RedactionConfig(max_record_chars=256)
    result = sanitize("x" * 1000, config)
    assert len(result.text) == 256
    assert result.truncated


def test_off_mode_preserves_text():
    visible = "vis" + "ible"
    result = sanitize("password=" + visible, RedactionConfig(mode="off"))
    assert result.text == "password=" + visible
    assert result.findings == ()


def test_custom_pattern_and_high_entropy():
    custom = RedactionConfig(custom_patterns=[r"PROJECT-[0-9]+"])
    result = sanitize(
        "PROJECT-123 ABCdef1234567890_+/=ABCdef1234567890_+/=",
        custom,
    )
    assert "PROJECT-123" not in result.text
    assert "custom_0" in result.findings


def test_unsigned_url_is_preserved():
    url = "https://example.test/path?safe=yes"
    assert sanitize(url, RedactionConfig()).text == url


def test_redacts_openai_style_key_without_literal_secret_fixture():
    candidate = "sk-" + "proj-" + "abcdefghijklmnopqrstuvwxyz"
    result = sanitize(candidate, RedactionConfig())
    assert candidate not in result.text
    assert "openai_key" in result.findings


def test_metadata_sensitive_key_is_redacted():
    from hermes_memory_router.redaction import sanitize_metadata

    result = sanitize_metadata(
        {"nested": {"api_key": "plain-value", "safe": "ok"}},
        RedactionConfig(),
    )
    assert result.value["nested"]["api_key"] == "[REDACTED]"
    assert result.value["nested"]["safe"] == "ok"
    assert "metadata_key:api_key" in result.findings


def test_metadata_sensitive_key_rejects_in_strict_mode():
    from hermes_memory_router.redaction import sanitize_metadata

    with pytest.raises(SecretDetected):
        sanitize_metadata({"refresh_token": "plain-value"}, RedactionConfig(mode="reject"))


def test_metadata_containers_are_bounded():
    from hermes_memory_router.redaction import sanitize_metadata

    result = sanitize_metadata(list(range(20)), RedactionConfig(), max_items=5)
    assert result.value == [0, 1, 2, 3, 4]
    assert result.truncated
