"""Data quality checks (category ``data``)."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..models import Issue, Severity
from ..project import Project, is_test_path
from .base import check
from .patterns import DOC_NAME_RE, LOADER_RE, VALIDATION_CODE_RE

MB = 1024 * 1024
MAX_ISSUES = 20

DATA_SUFFIXES = (
    ".csv",
    ".tsv",
    ".parquet",
    ".feather",
    ".jsonl",
    ".xlsx",
    ".xls",
    ".h5",
    ".hdf5",
    ".npy",
    ".npz",
    ".arrow",
    ".avro",
    ".orc",
    ".sqlite",
    ".db",
)

VALIDATION_MODULES = (
    "great_expectations",
    "pandera",
    "pydantic",
    "cerberus",
    "voluptuous",
    "pydeequ",
    "evidently",
    "whylogs",
    "pointblank",
    "tensorflow_data_validation",
)


def _data_files(project: Project) -> list[str]:
    """Dataset files outside test fixtures."""
    return [p for p in project.with_suffix(*DATA_SUFFIXES) if not is_test_path(p)]


@check("DQ001", "data", "Dataset files present")
def dataset_presence(project: Project) -> list[Issue]:
    """Looks for dataset files committed to the repository."""
    if _data_files(project):
        return []
    return [
        Issue(
            Severity.INFO,
            "No dataset files found in the repository.",
            recommendation="If data is downloaded at runtime, document its source, version and checksum.",
        )
    ]


@check("DQ002", "data", "Large data files managed by Git LFS or DVC")
def large_data_unmanaged(project: Project) -> list[Issue]:
    """Flags large data files committed directly to Git instead of Git LFS or DVC."""
    limit = project.config.large_file_mb * MB
    issues = []
    for rel in _data_files(project):
        size = project.size(rel)
        if size > limit and not project.is_managed(rel):
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"{size / MB:.1f} MB data file committed directly to Git.",
                    path=rel,
                    recommendation="Track it with Git LFS (`git lfs track`) or DVC (`dvc add`).",
                )
            )
    return issues[:MAX_ISSUES]


@check("DQ003", "data", "Data validation present")
def data_validation(project: Project) -> list[Issue]:
    """Checks that code loading data is guarded by schema or quality validation."""
    loads = project.grep(LOADER_RE)
    if not loads and not _data_files(project):
        return []
    if project.uses(*VALIDATION_MODULES) or project.grep(VALIDATION_CODE_RE):
        return []
    return [
        Issue(
            Severity.WARNING,
            "Data is loaded but no schema or quality validation was detected.",
            path=loads[0][0] if loads else None,
            recommendation="Validate at load time with Great Expectations, Pandera or pydantic, "
            "or with explicit schema and null-count assertions.",
        )
    ]


@check("DQ004", "data", "Datasets documented")
def data_documentation(project: Project) -> list[Issue]:
    """Checks that each directory holding data has a README, data card or datasheet."""
    data_dirs = {PurePosixPath(p).parent.as_posix() for p in _data_files(project)}
    if not data_dirs:
        return []
    doc_dirs = {
        PurePosixPath(p).parent.as_posix()
        for p in project.select(lambda p: DOC_NAME_RE.match(PurePosixPath(p).name) is not None)
    }

    def documented(directory: str) -> bool:
        candidates = [PurePosixPath(directory), *PurePosixPath(directory).parents]
        return any(c.as_posix() in doc_dirs for c in candidates)

    undocumented = sorted(d for d in data_dirs if not documented(d))
    if not undocumented:
        return []
    return [
        Issue(
            Severity.INFO,
            "Data directories without a README, data card or datasheet: " + ", ".join(undocumented[:10]),
            recommendation="Describe the source, license, schema, collection process and known biases.",
        )
    ]
