from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import RedactionConfig
from .exceptions import SecretDetected

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("authorization_bearer", re.compile(
        r"(?i)(authorization\s*:\s*bearer\s+)([A-Za-z0-9._~+/=-]{10,})"
    )),
    ("assignment_secret", re.compile(
        r"(?i)\b((?:api[_-]?key|secret|token|password|passwd|pwd|"
        r"client[_-]?secret|private[_-]?key|access[_-]?key)"
        r"\s*[:=]\s*[\"']?)([^\s,\"';]+)"
    )),
    ("openai_key", re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_-]{12,})\b")),
    ("github_token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,})\b")),
    ("jwt", re.compile(
        r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"
    )),
    ("private_key", re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    )),
    ("dsn_password", re.compile(
        r"(?i)\b(postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?)://"
        r"([^@\s:/]+):([^@\s]+)@"
    )),
]

_SENSITIVE_QUERY_KEYS = {
    "token", "access_token", "auth", "authorization", "signature", "sig",
    "key", "api_key", "apikey", "password", "secret", "x-amz-signature",
    "x-goog-signature",
}


@dataclass(frozen=True)
class RedactionResult:
    text: str
    findings: tuple[str, ...]
    truncated: bool


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {ch: value.count(ch) for ch in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def _redact_signed_urls(text: str, replacement: str) -> tuple[str, bool]:
    changed = False
    url_re = re.compile(r"https?://[^\s<>'\"]+")
    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        raw = match.group(0)
        try:
            split = urlsplit(raw)
            pairs = parse_qsl(split.query, keep_blank_values=True)
            if not any(key.lower() in _SENSITIVE_QUERY_KEYS for key, _ in pairs):
                return raw
            safe = [
                (key, replacement if key.lower() in _SENSITIVE_QUERY_KEYS else value)
                for key, value in pairs
            ]
            changed = True
            return urlunsplit((split.scheme, split.netloc, split.path, urlencode(safe), split.fragment))
        except Exception:
            return raw
    return url_re.sub(repl, text), changed


def sanitize(text: str, config: RedactionConfig) -> RedactionResult:
    value = text or ""
    truncated = len(value) > config.max_record_chars
    if truncated:
        value = value[:config.max_record_chars]

    if config.mode == "off":
        return RedactionResult(value, (), truncated)

    findings: list[str] = []
    output = value

    for name, pattern in _PATTERNS:
        if pattern.search(output):
            findings.append(name)
            if name == "authorization_bearer":
                output = pattern.sub(rf"\1{config.replacement}", output)
            elif name == "assignment_secret":
                output = pattern.sub(rf"\1{config.replacement}", output)
            elif name == "dsn_password":
                output = pattern.sub(
                    rf"\1://{config.replacement}:{config.replacement}@",
                    output,
                )
            else:
                output = pattern.sub(config.replacement, output)

    output, changed = _redact_signed_urls(output, config.replacement)
    if changed:
        findings.append("signed_url")

    for index, raw_pattern in enumerate(config.custom_patterns):
        pattern = re.compile(raw_pattern)
        if pattern.search(output):
            findings.append(f"custom_{index}")
            output = pattern.sub(config.replacement, output)

    # Catch token-like high-entropy strings conservatively. Avoid ordinary hashes
    # by requiring mixed character classes and a prefix-like separator nearby.
    entropy_re = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9_+/=-]{40,})(?![A-Za-z0-9])")
    def entropy_repl(match: re.Match[str]) -> str:
        candidate = match.group(1)
        classes = sum(bool(re.search(p, candidate)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[_+/=-]"))
        if classes >= 3 and _entropy(candidate) >= 4.2:
            findings.append("high_entropy_token")
            return config.replacement
        return candidate
    output = entropy_re.sub(entropy_repl, output)

    if findings and config.mode == "reject":
        raise SecretDetected(
            "Content rejected because likely secrets were detected: "
            + ", ".join(sorted(set(findings)))
        )

    return RedactionResult(output, tuple(sorted(set(findings))), truncated)
