"""Dependency checks (category ``dependencies``)."""

from __future__ import annotations

import re
import sys
from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project, is_requirements_file, normalize_name
from .base import check

MAX_ISSUES = 20
STDLIB = frozenset(sys.stdlib_module_names)

MANIFEST_NAMES = frozenset({"setup.py", "setup.cfg", "environment.yml", "environment.yaml", "pipfile"})

# Import name -> distribution name, where they differ.
IMPORT_TO_DISTRIBUTION: dict[str, str] = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "skimage": "scikit-image",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
    "attr": "attrs",
    "Crypto": "pycryptodome",
    "OpenSSL": "pyopenssl",
    "serial": "pyserial",
}

# Tooling that is run from the command line rather than imported.
TOOLING = frozenset(
    {
        "pip",
        "setuptools",
        "wheel",
        "pytest",
        "pytest-cov",
        "coverage",
        "ruff",
        "black",
        "mypy",
        "pylint",
        "flake8",
        "isort",
        "pre-commit",
        "tox",
        "nox",
        "dvc",
        "jupyter",
        "notebook",
        "ipykernel",
        "gunicorn",
        "uvicorn",
        "twine",
        "build",
    }
)

RISKY_SPEC_RE = re.compile(r"git\+|file:|https?://|\.dev\d*|==\s*0\.0\.0")


def _manifests(project: Project) -> list[str]:
    found = [
        p for p in project.paths if is_requirements_file(p) or PurePosixPath(p).name.lower() in MANIFEST_NAMES
    ]
    pyproject = project.pyproject
    if "project" in pyproject or "poetry" in pyproject.get("tool", {}):
        found.append("pyproject.toml")
    return found


def _reverse_names() -> dict[str, str]:
    """Normalised distribution name -> import name."""
    return {normalize_name(dist): module for module, dist in IMPORT_TO_DISTRIBUTION.items()}


@check("DEP001", "dependencies", "Dependency manifest present")
def manifest_present(project: Project) -> list[Issue]:
    """Checks that dependencies are declared in a manifest so the environment can be rebuilt."""
    if _manifests(project):
        return []
    return [
        Issue(
            Severity.ERROR,
            "No dependency manifest found (requirements.txt, pyproject.toml, environment.yml or Pipfile).",
            recommendation="Declare dependencies explicitly so the environment can be rebuilt.",
        )
    ]


@check("DEP002", "dependencies", "Dependency specifiers are portable")
def risky_specifiers(project: Project) -> list[Issue]:
    """Flags Git URLs, local file paths, dev or pre-release builds, and 0.0.0 placeholder pins."""
    issues = []
    for req in project.requirements:
        if RISKY_SPEC_RE.search(req.spec):
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"'{req.name}' uses a non-portable specifier: {req.spec[:80]}",
                    path=req.source,
                    recommendation="Use a published release. Pin Git or local builds only in a "
                    "clearly marked, temporary override.",
                )
            )
    return issues[:MAX_ISSUES]


@check("DEP003", "dependencies", "Imports declared as dependencies")
def undeclared_imports(project: Project) -> list[Issue]:
    """Finds third-party modules imported by project code that no manifest declares."""
    if not _manifests(project):
        return []  # DEP001 already covers this case
    declared = {req.normalized for req in project.requirements}
    local = {normalize_name(name) for name in project.local_modules}
    missing: dict[str, str] = {}
    for module, files in project.imports.items():
        if module in STDLIB or module.startswith("_") or module in project.local_modules:
            continue
        if normalize_name(module) in local:
            continue
        if all(f.startswith(("tests/", "test/")) for f in files):
            continue
        dist = IMPORT_TO_DISTRIBUTION.get(module, module)
        if normalize_name(dist) in declared or normalize_name(module) in declared:
            continue
        missing[module] = dist
    if not missing:
        return []
    listing = ", ".join(
        module if module == dist else f"{module} (package {dist})" for module, dist in sorted(missing.items())
    )
    return [
        Issue(
            Severity.WARNING,
            f"Imported but not declared as dependencies: {listing}",
            recommendation="Add these packages to your manifest so installs are reproducible.",
        )
    ]


@check("DEP004", "dependencies", "Declared dependencies are used")
def unused_dependencies(project: Project) -> list[Issue]:
    """Lists declared dependencies that project code never imports (possible dead weight)."""
    if not project.python_files() or not project.requirements:
        return []
    reverse = _reverse_names()
    imported = {normalize_name(m) for m in project.imports}
    unused = sorted(
        {
            req.name
            for req in project.requirements
            if reverse.get(req.normalized, req.normalized) not in imported
            and req.normalized not in imported
            and req.normalized not in {normalize_name(t) for t in TOOLING}
        }
    )
    if not unused:
        return []
    return [
        Issue(
            Severity.INFO,
            "Declared but never imported by project code: " + ", ".join(unused[:15]),
            recommendation="Remove unused packages, or move tooling into a dev group. "
            "Ignore this if they are used only through the command line.",
        )
    ]
