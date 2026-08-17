"""Single source of truth for Chronalyn identity and compatibility aliases.

Chronalyn is long-term memory orchestration for Hermes Agent: Hindsight
provides deeper history and semantic recall, Mnemosyne keeps verified
checkpoints with bounded fallback. Console, change-intelligence, bug-discovery
and deployment-analysis modules are roadmap items and are not implemented here.

Durable identities are deliberately separated from brand identities:

* ``PROVIDER_ID`` / ``DISTRIBUTION`` / ``CLI_COMMAND`` are the new public
  identity and may change with a major release.
* ``LEGACY_*`` values are recognised for backward compatibility with existing
  Hermes Memory Router installations. They are never written as the preferred
  value, but they are accepted, detected, backed up, and reported.
* ``STATE_DIRNAME`` is a *durable* on-disk identity. It is intentionally NOT
  rebranded: renaming it would strand existing configuration, databases and
  backups.
"""

from __future__ import annotations

# -- Brand ------------------------------------------------------------------
BRAND = "Chronalyn"
TAGLINE = "Give Hermes a past it can actually use."
HERMES_COMPONENT = "Chronalyn"

# -- Versions ---------------------------------------------------------------
# Python/PEP 440 version and the human release name must stay in lockstep.
VERSION = "1.0.0"
RELEASE_NAME = "v1.0.0"
RELEASE_TAG = RELEASE_NAME
IS_RELEASE_CANDIDATE = False

# -- Distribution and CLI ---------------------------------------------------
DISTRIBUTION = "chronalyn"
PACKAGE = "chronalyn"
CLI_COMMAND = "chronalyn"
LEGACY_DISTRIBUTION = "hermes-memory-router"
LEGACY_PACKAGE = "hermes_memory_router"
LEGACY_CLI_COMMAND = "hermes-memory-router"

# -- Hermes provider identity ----------------------------------------------
# The preferred provider id, plus the legacy id kept loadable so an existing
# ``memory.provider: hermes_memory_router`` configuration keeps working until
# the user explicitly migrates.
PROVIDER_ID = "chronalyn"
LEGACY_PROVIDER_ID = "hermes_memory_router"
PROVIDER_IDS = (PROVIDER_ID, LEGACY_PROVIDER_ID)

# Backends the router owns internally. If one of these is *also* configured as a
# separate Hermes provider, that is a conflict rather than a Chronalyn alias.
CHILD_PROVIDERS = frozenset({"hindsight", "mnemosyne"})

# -- Durable on-disk identity (intentionally not rebranded) ------------------
STATE_DIRNAME = "memory-router"
STATE_DB_FILENAME = "router.db"
CONFIG_FILENAME = "config.json"

# -- Release artifacts ------------------------------------------------------
REPOSITORY = "l1lchucky/chronalyn"
WHEEL = f"{PACKAGE}-{VERSION}-py3-none-any.whl"
SDIST = f"{PACKAGE}-{VERSION}.tar.gz"
SBOM = f"{DISTRIBUTION}-{RELEASE_NAME}.spdx.json"
CHECKSUMS = f"SHA256SUMS-{DISTRIBUTION}-{RELEASE_NAME}.txt"
RELEASE_BASE = f"https://github.com/{REPOSITORY}/releases/download/{RELEASE_TAG}"
USER_AGENT = f"{DISTRIBUTION}/{RELEASE_NAME.lstrip('v')}"

# -- Upstream ---------------------------------------------------------------
OFFICIAL_HERMES_INSTALLER = "https://hermes-agent.nousresearch.com/install.sh"
MNEMOSYNE_SPEC = "mnemosyne-memory>=3.15,<4"

DEPRECATION_NOTICE = (
    f"{LEGACY_CLI_COMMAND} is deprecated and will be removed in a future "
    f"release; use `{CLI_COMMAND}` instead."
)


def is_provider_id(value: str) -> bool:
    """Return True when *value* identifies Chronalyn, including the legacy id."""
    return value.strip() in PROVIDER_IDS


__all__ = [
    "BRAND",
    "CHECKSUMS",
    "CHILD_PROVIDERS",
    "CLI_COMMAND",
    "CONFIG_FILENAME",
    "DEPRECATION_NOTICE",
    "DISTRIBUTION",
    "HERMES_COMPONENT",
    "IS_RELEASE_CANDIDATE",
    "LEGACY_CLI_COMMAND",
    "LEGACY_DISTRIBUTION",
    "LEGACY_PACKAGE",
    "LEGACY_PROVIDER_ID",
    "MNEMOSYNE_SPEC",
    "OFFICIAL_HERMES_INSTALLER",
    "PACKAGE",
    "PROVIDER_ID",
    "PROVIDER_IDS",
    "RELEASE_BASE",
    "RELEASE_NAME",
    "RELEASE_TAG",
    "REPOSITORY",
    "SBOM",
    "SDIST",
    "STATE_DB_FILENAME",
    "STATE_DIRNAME",
    "TAGLINE",
    "USER_AGENT",
    "VERSION",
    "WHEEL",
    "is_provider_id",
]
