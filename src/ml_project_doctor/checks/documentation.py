"""Documentation checks (category ``documentation``)."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project
from .base import check

MIN_README_CHARS = 300


def _root_file(project: Project, prefix: str) -> str | None:
    names = project.select(lambda p: "/" not in p and PurePosixPath(p).name.lower().startswith(prefix))
    return sorted(names)[0] if names else None


@check("DOC001", "documentation", "README present")
def readme_present(project: Project) -> list[Issue]:
    """Checks that the repository has a README at the root."""
    if _root_file(project, "readme"):
        return []
    return [
        Issue(
            Severity.ERROR,
            "No README found at the repository root.",
            recommendation="Describe what the project does, how to install it, "
            "and how to train and evaluate.",
        )
    ]


@check("DOC002", "documentation", "README has substance")
def readme_length(project: Project) -> list[Issue]:
    """Flags READMEs too short to explain a project."""
    name = _root_file(project, "readme")
    if name is None:
        return []
    text = project.read_text(name) or ""
    if len(text.strip()) >= MIN_README_CHARS:
        return []
    return [
        Issue(
            Severity.WARNING,
            f"README is only {len(text.strip())} characters long.",
            path=name,
            recommendation="Add the project purpose, setup steps, usage example and results summary.",
        )
    ]


@check("DOC003", "documentation", "README covers installation and usage")
def readme_sections(project: Project) -> list[Issue]:
    """Checks that the README explains how to install and use the project."""
    name = _root_file(project, "readme")
    if name is None:
        return []
    text = (project.read_text(name) or "").lower()
    missing = []
    if not re.search(r"install|setup|getting started|quick ?start", text):
        missing.append("installation")
    if not re.search(r"usage|quick ?start|how to|example|run ", text):
        missing.append("usage")
    if not missing:
        return []
    return [
        Issue(
            Severity.WARNING,
            "README does not describe: " + ", ".join(missing) + ".",
            path=name,
            recommendation="Include copy-paste install and usage commands.",
        )
    ]


@check("DOC004", "documentation", "Reproduction instructions")
def reproduction_steps(project: Project) -> list[Issue]:
    """Checks that the README explains how to reproduce training or results."""
    name = _root_file(project, "readme")
    if name is None:
        return []
    text = (project.read_text(name) or "").lower()
    if re.search(r"reproduc|retrain|train|experiment", text):
        return []
    return [
        Issue(
            Severity.INFO,
            "README has no reproduction or training instructions.",
            path=name,
            recommendation="Document the exact commands, seeds, data version and hardware "
            "needed to reproduce results.",
        )
    ]


@check("DOC005", "documentation", "License file present")
def license_file(project: Project) -> list[Issue]:
    """Checks for a LICENSE file so users know how the code may be used."""
    if _root_file(project, "licen") or _root_file(project, "copying"):
        return []
    return [
        Issue(
            Severity.WARNING,
            "No LICENSE file found.",
            recommendation="Add a LICENSE file. Without one, the code is not open for reuse by default.",
        )
    ]


@check("DOC006", "documentation", "Changelog present")
def changelog(project: Project) -> list[Issue]:
    """Checks for a changelog that records changes between releases."""
    if _root_file(project, "changelog") or _root_file(project, "history"):
        return []
    return [
        Issue(
            Severity.INFO,
            "No CHANGELOG found.",
            recommendation="Keep a CHANGELOG.md so model and code changes are traceable.",
        )
    ]
