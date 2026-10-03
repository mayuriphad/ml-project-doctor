"""Model artifact checks (category ``models``)."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project, is_test_path
from .base import check
from .patterns import HEALTH_RE, REGISTRY_RE, UNSAFE_LOAD_RE

MB = 1024 * 1024
MAX_ISSUES = 20
WARN_SIZE_MB = 5.0

MODEL_SUFFIXES = (
    ".pkl",
    ".pickle",
    ".joblib",
    ".h5",
    ".keras",
    ".pt",
    ".pth",
    ".onnx",
    ".safetensors",
    ".ckpt",
    ".pb",
    ".tflite",
    ".gguf",
    ".bin",
    ".mlmodel",
)
MODEL_CARD_NAMES = frozenset({"model_card.md", "modelcard.md", "model-card.md"})
SERVING_MODULES = ("fastapi", "flask", "starlette", "bentoml", "litserve", "sanic", "tornado")
REGISTRY_MODULES = ("mlflow", "wandb", "neptune", "clearml", "bentoml")


def _artifacts(project: Project) -> list[str]:
    return [p for p in project.with_suffix(*MODEL_SUFFIXES) if not is_test_path(p)]


@check("MDL001", "models", "Model binaries managed outside plain Git")
def model_binaries(project: Project) -> list[Issue]:
    """Flags large model files committed directly to Git, and mid-size ones without LFS or DVC."""
    limit = project.config.large_file_mb * MB
    issues = []
    for rel in _artifacts(project):
        if project.is_managed(rel):
            continue
        size = project.size(rel)
        if size > limit:
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"{size / MB:.1f} MB model file committed directly to Git.",
                    path=rel,
                    recommendation="Use Git LFS, DVC or a model registry (MLflow, W&B) instead.",
                )
            )
        elif size > WARN_SIZE_MB * MB:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"{size / MB:.1f} MB model file committed directly to Git.",
                    path=rel,
                    recommendation="Track model files with Git LFS or DVC to keep clones small.",
                )
            )
    return issues[:MAX_ISSUES]


@check("MDL002", "models", "Model card present")
def model_card(project: Project) -> list[Issue]:
    """Checks that projects shipping model artifacts document them in a model card."""
    if not _artifacts(project):
        return []
    if any(PurePosixPath(p).name.lower() in MODEL_CARD_NAMES for p in project.paths):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Model artifacts present but no model card found.",
            recommendation="Add MODEL_CARD.md covering intended use, training data, metrics, "
            "limitations and license.",
        )
    ]


@check("MDL003", "models", "No unsafe deserialisation")
def unsafe_deserialisation(project: Project) -> list[Issue]:
    """Flags pickle-based loading, which can execute arbitrary code from an untrusted file."""
    hits = project.grep(UNSAFE_LOAD_RE)
    return [
        Issue(
            Severity.WARNING,
            f"line {lineno}: {line[:120]}",
            path=rel,
            recommendation="Load only trusted files, verify checksums first, or prefer safetensors "
            "and torch.load(..., weights_only=True).",
        )
        for rel, lineno, line in hits[:MAX_ISSUES]
    ]


@check("MDL004", "models", "Serving health endpoint")
def health_endpoint(project: Project) -> list[Issue]:
    """Checks that a model serving app exposes a health or readiness route."""
    if not project.uses(*SERVING_MODULES) or project.grep(HEALTH_RE):
        return []
    return [
        Issue(
            Severity.INFO,
            "Serving framework detected but no health endpoint found.",
            recommendation="Expose /health (liveness) and /ready (readiness) for orchestrators.",
        )
    ]


@check("MDL005", "models", "Model versioning or registry")
def model_registry(project: Project) -> list[Issue]:
    """Checks that model artifacts are versioned with a checksum, registry or DVC record."""
    if not _artifacts(project):
        return []
    if project.uses(*REGISTRY_MODULES) or project.grep(REGISTRY_RE):
        return []
    return [
        Issue(
            Severity.INFO,
            "Model artifacts are present without a registry, checksum or version record.",
            recommendation="Register models in MLflow or W&B, or record SHA-256 checksums with each release.",
        )
    ]
