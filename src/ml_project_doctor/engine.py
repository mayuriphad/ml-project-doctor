"""Runs the registered checks against a project and assembles a :class:`Report`."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .checks import all_checks
from .checks.base import CheckSpec
from .config import Config, load_config
from .models import CATEGORIES, CheckResult, Finding, Issue, Report, Severity, compute_scores
from .project import Project


def audit(
    root: str | Path,
    *,
    config: Config | None = None,
    categories: Iterable[str] | None = None,
    ignore: Iterable[str] = (),
) -> Report:
    """Audit the project at ``root``.

    Args:
        root: Project directory.
        config: Settings to use. Defaults to ``[tool.ml-project-doctor]`` in the project.
        categories: Only run checks in these categories. Defaults to all.
        ignore: Check IDs to skip, in addition to ``config.ignore``.

    Raises:
        ValueError: If an unknown check ID or category is requested.
        ConfigError: If the project's configuration is invalid.
    """
    root_path = Path(root).resolve()
    if config is None:
        config = load_config(root_path)

    registry = all_checks()
    ignored = {item.strip().upper() for item in (*config.ignore, *ignore)}
    unknown_ids = ignored - set(registry)
    if unknown_ids:
        raise ValueError(f"unknown check id(s): {', '.join(sorted(unknown_ids))}")

    wanted = set(categories) if categories is not None else set(CATEGORIES)
    unknown_categories = wanted - set(CATEGORIES)
    if unknown_categories:
        raise ValueError(f"unknown categor(y/ies): {', '.join(sorted(unknown_categories))}")

    specs = [s for s in registry.values() if s.category in wanted and s.id not in ignored]
    project = Project(root_path, config)

    findings: list[Finding] = []
    results: list[CheckResult] = []
    for spec in specs:
        status, issues = _run(spec, project)
        findings.extend(
            Finding(
                check_id=spec.id,
                category=spec.category,
                title=spec.title,
                severity=issue.severity,
                message=issue.message,
                path=issue.path,
                recommendation=issue.recommendation,
            )
            for issue in issues
        )
        results.append(
            CheckResult(
                check_id=spec.id,
                category=spec.category,
                title=spec.title,
                status=status,
                finding_count=len(issues),
            )
        )

    score, category_scores = compute_scores(findings, [c for c in CATEGORIES if c in wanted])
    return Report(
        project_path=str(project.root),
        tool_version=__version__,
        generated_at=datetime.now(UTC),
        findings=findings,
        checks=results,
        score=score,
        category_scores=category_scores,
    )


def _run(spec: CheckSpec, project: Project) -> tuple[str, list[Issue]]:
    """Run one check. A crashing check is reported as an error rather than aborting the audit."""
    try:
        issues = list(spec.func(project))
    except Exception as exc:
        crash = Issue(
            Severity.ERROR,
            f"check raised {type(exc).__name__}: {exc}",
            recommendation="This is a bug in ml-project-doctor. Please report it with the project layout.",
        )
        return "error", [crash]
    return ("failed" if issues else "passed"), issues
