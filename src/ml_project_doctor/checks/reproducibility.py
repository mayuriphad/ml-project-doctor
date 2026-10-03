"""Reproducibility checks (category ``reproducibility``)."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project, is_requirements_file, is_test_path
from .base import check
from .patterns import ABS_PATH_RE, FIT_RE, FROM_RE, SEED_RE

MAX_ISSUES = 20

LOCKFILES = frozenset(
    {
        "poetry.lock",
        "uv.lock",
        "pdm.lock",
        "pipfile.lock",
        "conda-lock.yml",
        "requirements.lock",
        "requirements-lock.txt",
    }
)
CODE_SUFFIXES = (".py", ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini")


def _dockerfiles(project: Project) -> list[str]:
    return project.select(lambda p: PurePosixPath(p).name.lower().startswith("dockerfile"))


@check("REP001", "reproducibility", "Dependency lock file present")
def lock_file(project: Project) -> list[Issue]:
    """Checks for a lock file, or fully pinned requirements files, so dependency resolution is stable."""
    if any(PurePosixPath(p).name.lower() in LOCKFILES for p in project.paths):
        return []
    req_files = [r for r in project.requirements if is_requirements_file(r.source)]
    if req_files and all(r.pinned for r in req_files):
        return []
    return [
        Issue(
            Severity.WARNING,
            "No lock file found; transitive dependencies can resolve differently over time.",
            recommendation="Generate one with `uv lock`, `poetry lock`, `pdm lock` or `pip-compile`.",
        )
    ]


@check("REP002", "reproducibility", "Requirements pinned")
def unpinned_requirements(project: Project) -> list[Issue]:
    """Flags requirements files that declare packages without an exact version."""
    issues = []
    sources = sorted({r.source for r in project.requirements if is_requirements_file(r.source)})
    for source in sources:
        loose = [r.name for r in project.requirements if r.source == source and not r.pinned]
        if not loose:
            continue
        shown = ", ".join(loose[:8]) + (" ..." if len(loose) > 8 else "")
        issues.append(
            Issue(
                Severity.WARNING,
                f"{len(loose)} requirement(s) not pinned with '==': {shown}",
                path=source,
                recommendation="Pin exact versions (name==x.y.z) or use a lock file.",
            )
        )
    return issues


@check("REP003", "reproducibility", "Random seeds set")
def random_seeds(project: Project) -> list[Issue]:
    """Checks that training code sets random seeds for reproducible results."""
    fit_hits = project.grep(FIT_RE)
    if not fit_hits or project.grep(SEED_RE):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Training code found but no random seed is set.",
            path=fit_hits[0][0],
            recommendation="Seed Python, NumPy and your framework in one set_seed() helper, "
            "and pass random_state to splitters.",
        )
    ]


@check("REP004", "reproducibility", "Python version pinned")
def python_version(project: Project) -> list[Issue]:
    """Checks that the Python version is declared in one of the usual places."""
    if (
        project.pyproject.get("project", {}).get("requires-python")
        or project.exists(".python-version")
        or project.exists("runtime.txt")
        or project.grep(FROM_RE, _dockerfiles(project))
    ):
        return []
    return [
        Issue(
            Severity.INFO,
            "No Python version is pinned.",
            recommendation="Set requires-python in pyproject.toml and add a .python-version file.",
        )
    ]


@check("REP005", "reproducibility", "No hardcoded absolute paths")
def absolute_paths(project: Project) -> list[Issue]:
    """Finds absolute, machine-specific paths in code and configuration."""
    rels = project.select(lambda p: p.lower().endswith(CODE_SUFFIXES) and not is_test_path(p))
    hits = project.grep(ABS_PATH_RE, rels)
    return [
        Issue(
            Severity.WARNING,
            f"line {lineno}: {line[:120]}",
            path=rel,
            recommendation="Use paths relative to the project root or read them from configuration.",
        )
        for rel, lineno, line in hits[:MAX_ISSUES]
    ]


@check("REP006", "reproducibility", "Container definition present")
def container(project: Project) -> list[Issue]:
    """Looks for a Dockerfile that pins the OS, system libraries and Python."""
    if _dockerfiles(project):
        return []
    return [
        Issue(
            Severity.INFO,
            "No Dockerfile found.",
            recommendation="A container pins the OS, system libraries and Python for training and serving.",
        )
    ]


@check("REP007", "reproducibility", "Container base image pinned")
def base_image(project: Project) -> list[Issue]:
    """Flags Dockerfile base images that have no tag or use ``latest``."""
    issues = []
    for rel in _dockerfiles(project):
        for line in (project.read_text(rel) or "").splitlines():
            match = FROM_RE.match(line)
            if not match:
                continue
            image = match.group(1)
            if "@sha256:" in image:
                continue
            name = image.rsplit("/", 1)[-1]
            if ":" not in name or name.endswith(":latest"):
                issues.append(
                    Issue(
                        Severity.WARNING,
                        f"Base image '{image}' is not pinned to a version.",
                        path=rel,
                        recommendation="Pin a specific tag (e.g. python:3.11-slim) or a digest.",
                    )
                )
    return issues
