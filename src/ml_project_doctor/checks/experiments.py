"""Experiment tracking checks (category ``experiments``)."""

from __future__ import annotations

import json

from ..models import Issue, Severity
from ..project import Project
from .base import check
from .patterns import FIT_RE, TRACKING_CODE_RE

TRACKING_MODULES = (
    "mlflow",
    "wandb",
    "neptune",
    "comet_ml",
    "clearml",
    "tensorboard",
    "tensorboardX",
    "aim",
    "sacred",
    "guild",
)
TRACKING_OUTPUT_DIRS = (
    "mlruns",
    "wandb",
    "lightning_logs",
    "tb_logs",
    "runs",
    ".neptune",
    ".clearml",
    "aim",
)


@check("EXP001", "experiments", "Experiment tracking in use")
def tracking_library(project: Project) -> list[Issue]:
    """Checks that training runs are tracked with a tool such as MLflow or Weights & Biases."""
    if not project.grep(FIT_RE):
        return []
    if project.uses(*TRACKING_MODULES) or project.grep(TRACKING_CODE_RE):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Training code found but no experiment tracking was detected.",
            recommendation="Log parameters, metrics and artifacts with MLflow, Weights & Biases, "
            "Neptune, ClearML or TensorBoard.",
        )
    ]


@check("EXP002", "experiments", "Tracking output kept out of Git")
def tracking_outputs(project: Project) -> list[Issue]:
    """Flags experiment tracking output directories that are not listed in .gitignore."""
    gitignore = project.read_text(".gitignore") or ""
    issues = []
    for directory in TRACKING_OUTPUT_DIRS:
        if not project.has_dir(directory) or directory in gitignore:
            continue
        count = sum(1 for p in project.paths if p.startswith(directory + "/"))
        issues.append(
            Issue(
                Severity.WARNING,
                f"Experiment output '{directory}/' ({count} files) is present and not in .gitignore.",
                path=directory,
                recommendation="Add it to .gitignore and keep runs in a tracking server or artifact store.",
            )
        )
    return issues


@check("EXP003", "experiments", "Notebooks free of saved outputs")
def notebook_outputs(project: Project) -> list[Issue]:
    """Reports notebooks that commit cell outputs, which bloat diffs and hide stale results."""
    issues = []
    for rel in project.with_suffix(".ipynb"):
        try:
            notebook = json.loads(project.read_text(rel) or "{}")
        except json.JSONDecodeError:
            continue
        cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
        has_outputs = any(
            isinstance(cell, dict) and cell.get("cell_type") == "code" and cell.get("outputs")
            for cell in cells
        )
        if has_outputs:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Notebook has saved cell outputs.",
                    path=rel,
                    recommendation="Clear outputs before committing (e.g. nbstripout) and move "
                    "reusable logic into importable modules.",
                )
            )
    return issues
