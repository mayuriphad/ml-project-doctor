"""Training pipeline checks (category ``training``)."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project
from .base import check
from .patterns import (
    CHECKPOINT_RE,
    ENTRYPOINT_RE,
    FIT_RE,
    FIT_TRANSFORM_RE,
    SPLIT_RE,
    TRAIN_SPLIT_CALL_RE,
)

CONFIG_SUFFIXES = (".yaml", ".yml", ".toml", ".json", ".cfg", ".ini")
IGNORED_CONFIG_NAMES = frozenset(
    {
        "pyproject.toml",
        "setup.cfg",
        "package.json",
        "tsconfig.json",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".pre-commit-config.yaml",
        ".readthedocs.yaml",
        "mkdocs.yml",
        "codecov.yml",
        "pytest.ini",
        "tox.ini",
        "renovate.json",
        "cookiecutter.json",
    }
)


def _config_files(project: Project) -> list[str]:
    return project.select(
        lambda p: (
            p.lower().endswith(CONFIG_SUFFIXES)
            and not p.startswith(".github/")
            and PurePosixPath(p).name.lower() not in IGNORED_CONFIG_NAMES
        )
    )


@check("TRN001", "training", "Training entrypoint present")
def entrypoint(project: Project) -> list[Issue]:
    """Looks for an obvious training script, such as ``train.py``."""
    if not project.grep(FIT_RE):
        return []
    if project.select(lambda p: ENTRYPOINT_RE.match(PurePosixPath(p).name) is not None):
        return []
    return [
        Issue(
            Severity.INFO,
            "Training code found but no obvious entrypoint (e.g. train.py).",
            recommendation="Expose training as one documented command, e.g. "
            "`python -m yourpkg.train --config configs/base.yaml`.",
        )
    ]


@check("TRN002", "training", "Train/validation/test split")
def data_split(project: Project) -> list[Issue]:
    """Checks that training code uses a held-out split or cross-validation."""
    if not project.grep(FIT_RE) or project.grep(SPLIT_RE):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Model is trained but no train/validation/test split was detected.",
            recommendation="Hold out a test set, or use k-fold, group-aware or time-aware splits, "
            "and save the split indices.",
        )
    ]


@check("TRN003", "training", "Checkpointing or early stopping")
def checkpointing(project: Project) -> list[Issue]:
    """Checks that training saves checkpoints or stops early."""
    if not project.grep(FIT_RE) or project.grep(CHECKPOINT_RE):
        return []
    return [
        Issue(
            Severity.INFO,
            "No checkpointing or early stopping detected.",
            recommendation="Save checkpoints and use early stopping so long runs can resume "
            "and do not overfit.",
        )
    ]


@check("TRN004", "training", "Hyperparameters externalised to configuration")
def external_config(project: Project) -> list[Issue]:
    """Checks that hyperparameters live in configuration files rather than only in code."""
    if not project.grep(FIT_RE) or _config_files(project):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Training code found but no configuration files; hyperparameters are likely hardcoded.",
            recommendation="Move hyperparameters into YAML/TOML configs (or Hydra/params.yaml) "
            "and record the resolved config with each run.",
        )
    ]


@check("TRN005", "training", "Preprocessing fitted after the split")
def preprocessing_leakage(project: Project) -> list[Issue]:
    """Flags ``fit_transform`` calls that run before ``train_test_split`` in the same file."""
    issues = []
    for rel in project.python_files():
        lines = (project.read_text(rel) or "").splitlines()
        fits = [i for i, line in enumerate(lines, 1) if FIT_TRANSFORM_RE.search(line)]
        splits = [i for i, line in enumerate(lines, 1) if TRAIN_SPLIT_CALL_RE.search(line)]
        if fits and splits and fits[0] < splits[0]:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"fit_transform() on line {fits[0]} runs before train_test_split() on line "
                    f"{splits[0]}; statistics may leak from the test set.",
                    path=rel,
                    recommendation="Split first, then fit preprocessing on the training portion only, "
                    "or use a sklearn Pipeline.",
                )
            )
    return issues
