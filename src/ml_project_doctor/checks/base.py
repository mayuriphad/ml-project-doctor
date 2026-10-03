"""Check registration. Each check is a function ``(Project) -> list[Issue]``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models import CATEGORIES

if TYPE_CHECKING:
    from ..project import Project

CheckFunc = Callable[["Project"], Any]


@dataclass(frozen=True)
class CheckSpec:
    id: str
    category: str
    title: str
    func: CheckFunc
    description: str = ""


REGISTRY: dict[str, CheckSpec] = {}


def check(check_id: str, category: str, title: str) -> Callable[[CheckFunc], CheckFunc]:
    """Register a check. The function's docstring becomes its description in ``docs``."""
    if category not in CATEGORIES:
        raise ValueError(f"unknown category for {check_id}: {category!r}")

    def decorator(func: CheckFunc) -> CheckFunc:
        if check_id in REGISTRY:
            raise ValueError(f"duplicate check id: {check_id}")
        REGISTRY[check_id] = CheckSpec(
            id=check_id,
            category=category,
            title=title,
            func=func,
            description=(func.__doc__ or "").strip(),
        )
        return func

    return decorator
