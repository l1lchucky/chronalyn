from __future__ import annotations

from dataclasses import dataclass

HINDSIGHT_ONLY = "hindsight-only"
HINDSIGHT_MNEMOSYNE = "hindsight-primary-mnemosyne-checkpoints"


@dataclass(frozen=True)
class PolicyDefinition:
    name: str
    automatic_backends: tuple[str, ...]
    checkpoint_backends: tuple[str, ...]
    recall_primary: str
    fallback_backend: str | None
    reflect_backend: str
    description: str


POLICIES = {
    HINDSIGHT_ONLY: PolicyDefinition(
        name=HINDSIGHT_ONLY,
        automatic_backends=("hindsight",),
        checkpoint_backends=("hindsight",),
        recall_primary="hindsight",
        fallback_backend=None,
        reflect_backend="hindsight",
        description="Hindsight handles every memory operation in this mode.",
    ),
    HINDSIGHT_MNEMOSYNE: PolicyDefinition(
        name=HINDSIGHT_MNEMOSYNE,
        automatic_backends=("hindsight",),
        checkpoint_backends=("hindsight", "mnemosyne"),
        recall_primary="hindsight",
        fallback_backend="mnemosyne",
        reflect_backend="hindsight",
        description=(
            "Hindsight handles normal memory and reflection. Mnemosyne stores "
            "verified checkpoints and is used only as a small fallback."
        ),
    ),
}


def get_policy(name: str) -> PolicyDefinition:
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported routing policy: {name}") from exc
