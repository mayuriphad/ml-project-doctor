"""Configuration, read from ``[tool.ml-project-doctor]`` in ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Severity

_KNOWN_KEYS = frozenset({"fail_on", "ignore", "large_file_mb", "max_text_bytes"})


class ConfigError(ValueError):
    """Raised when the configuration is invalid."""


@dataclass(frozen=True)
class Config:
    fail_on: Severity = Severity.ERROR
    ignore: frozenset[str] = frozenset()
    large_file_mb: float = 50.0
    max_text_bytes: int = 2_000_000


def load_config(root: Path) -> Config:
    """Load configuration from ``root/pyproject.toml``. Missing config yields defaults."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    section = data.get("tool", {}).get("ml-project-doctor")
    if section is None:
        return Config()
    return config_from_mapping(section)


def config_from_mapping(section: Mapping[str, Any]) -> Config:
    """Validate a raw ``[tool.ml-project-doctor]`` table and build a :class:`Config`."""
    unknown = set(section) - _KNOWN_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"unknown option(s) in [tool.ml-project-doctor]: {names}")

    try:
        fail_on = Severity.parse(str(section.get("fail_on", "error")))
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    ignore = section.get("ignore", [])
    if not isinstance(ignore, list) or not all(isinstance(item, str) for item in ignore):
        raise ConfigError("'ignore' must be a list of check IDs, e.g. [\"DOC006\"]")

    large = section.get("large_file_mb", 50.0)
    if not _is_number(large) or large <= 0:
        raise ConfigError("'large_file_mb' must be a positive number")

    max_bytes = section.get("max_text_bytes", 2_000_000)
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise ConfigError("'max_text_bytes' must be a positive integer")

    return Config(
        fail_on=fail_on,
        ignore=frozenset(item.strip().upper() for item in ignore),
        large_file_mb=float(large),
        max_text_bytes=max_bytes,
    )


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
