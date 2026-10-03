"""Check registry. Importing this package registers every built-in check."""

from __future__ import annotations

from . import (  # noqa: F401  (imported for their registration side effects)
    data,
    dependencies,
    documentation,
    experiments,
    model_artifacts,
    reproducibility,
    training,
)
from .base import REGISTRY, CheckSpec


def all_checks() -> dict[str, CheckSpec]:
    """All registered checks, keyed and sorted by check ID."""
    return dict(sorted(REGISTRY.items()))


__all__ = ["CheckSpec", "all_checks"]
