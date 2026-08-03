import pytest

from hermes_memory_router.config import RedactionConfig
from hermes_memory_router.exceptions import SecretDetected
from hermes_memory_router.redaction import sanitize


@pytest.mark.parametrize("text,secret", [
    ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "abcdefghijklmnopqrstuvwxyz"),
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
    with pytest.raises(SecretDetected):
        sanitize("password=hunter2", config)


def test_content_is_bounded():
    config = RedactionConfig(max_record_chars=256)
    result = sanitize("x" * 1000, config)
    assert len(result.text) == 256
    assert result.truncated


def test_off_mode_preserves_text():
    result = sanitize("password=visible", RedactionConfig(mode="off"))
    assert result.text == "password=visible"
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
