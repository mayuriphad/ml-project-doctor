"""Core data models shared by checks, the engine and reporters."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

TOOL_NAME = "ml-project-doctor"
SCHEMA_VERSION = "1.0"

CATEGORIES: tuple[str, ...] = (
    "data",
    "reproducibility",
    "training",
    "experiments",
    "models",
    "dependencies",
    "documentation",
)


class Severity(StrEnum):
    """How serious a finding is. Ordered: INFO < WARNING < ERROR."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return _RANKS[self]

    @property
    def penalty(self) -> int:
        """Points deducted from a category score for one finding of this severity."""
        return _PENALTIES[self]

    @classmethod
    def parse(cls, value: str | Severity) -> Severity:
        if isinstance(value, cls):
            return value
        try:
            return cls(value.strip().lower())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(f"invalid severity {value!r}; expected one of: {valid}") from None


_RANKS: dict[Severity, int] = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
_PENALTIES: dict[Severity, int] = {Severity.INFO: 1, Severity.WARNING: 4, Severity.ERROR: 10}


@dataclass(frozen=True)
class Issue:
    """Returned by a check for each problem it detects."""

    severity: Severity
    message: str
    path: str | None = None
    recommendation: str = ""


@dataclass(frozen=True)
class Finding:
    """An issue attributed to the check that produced it."""

    check_id: str
    category: str
    title: str
    severity: Severity
    message: str
    path: str | None = None
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "title": self.title,
            "severity": self.severity.value,
            "message": self.message,
            "path": self.path,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class CheckResult:
    """Outcome of running one check."""

    check_id: str
    category: str
    title: str
    status: str  # "passed", "failed" or "error" (the check itself crashed)
    finding_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "title": self.title,
            "status": self.status,
            "finding_count": self.finding_count,
        }


def compute_scores(
    findings: Iterable[Finding], categories: Iterable[str] = CATEGORIES
) -> tuple[int, dict[str, int]]:
    """Return ``(overall, per_category)`` scores from 0 to 100.

    Each category starts at 100 and loses points per finding. The overall score
    is the unweighted mean of the category scores.
    """
    penalties = dict.fromkeys(categories, 0)
    for finding in findings:
        if finding.category in penalties:
            penalties[finding.category] += finding.severity.penalty
    scores = {name: max(0, 100 - points) for name, points in penalties.items()}
    overall = round(sum(scores.values()) / len(scores)) if scores else 100
    return overall, scores


@dataclass
class Report:
    """The complete result of an audit."""

    project_path: str
    tool_version: str
    generated_at: datetime
    findings: list[Finding]
    checks: list[CheckResult]
    score: int
    category_scores: dict[str, int]

    def severity_counts(self) -> dict[str, int]:
        return {s.value: sum(1 for f in self.findings if f.severity is s) for s in Severity}

    def max_severity(self) -> Severity | None:
        return max((f.severity for f in self.findings), key=lambda s: s.rank, default=None)

    def fails(self, fail_on: Severity) -> bool:
        """True when any finding is at or above ``fail_on``."""
        return any(f.severity.rank >= fail_on.rank for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": TOOL_NAME, "version": self.tool_version},
            "project_path": self.project_path,
            "generated_at": self.generated_at.isoformat(),
            "score": self.score,
            "category_scores": dict(self.category_scores),
            "summary": {"total": len(self.findings), **self.severity_counts()},
            "checks": [c.to_dict() for c in self.checks],
            "findings": [f.to_dict() for f in self.findings],
        }
