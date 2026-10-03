from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ml_project_doctor.config import Config
from ml_project_doctor.models import (
    CATEGORIES,
    Finding,
    Report,
    Severity,
    compute_scores,
)
from ml_project_doctor.project import Project, is_test_path, normalize_name, parse_requirement


def _finding(severity: Severity, category: str = "data") -> Finding:
    return Finding("X1", category, "t", severity, "m")


# -- models -------------------------------------------------------------------------


def test_severity_parse_and_rank() -> None:
    assert Severity.parse(" WARNING ") is Severity.WARNING
    assert Severity.INFO.rank < Severity.WARNING.rank < Severity.ERROR.rank


def test_severity_parse_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="invalid severity"):
        Severity.parse("critical")


def test_compute_scores_penalises_only_the_affected_category() -> None:
    overall, cats = compute_scores([_finding(Severity.ERROR)], CATEGORIES)
    assert cats["data"] == 90
    assert all(score == 100 for name, score in cats.items() if name != "data")
    assert overall == round((90 + 100 * 6) / 7)


def test_compute_scores_floor_is_zero() -> None:
    findings = [_finding(Severity.ERROR)] * 20
    _, cats = compute_scores(findings, ["data"])
    assert cats["data"] == 0


def test_report_fails_respects_threshold() -> None:
    report = Report(
        project_path="x",
        tool_version="0",
        generated_at=datetime.now(UTC),
        findings=[_finding(Severity.WARNING)],
        checks=[],
        score=96,
        category_scores={"data": 96},
    )
    assert report.fails(Severity.WARNING)
    assert not report.fails(Severity.ERROR)
    assert report.max_severity() is Severity.WARNING


# -- project scanning -------------------------------------------------------------------


def test_scan_skips_virtualenvs_and_caches(make_project) -> None:
    root = make_project(
        {
            "src/a.py": "x = 1\n",
            ".venv/lib/b.py": "y = 2\n",
            "__pycache__/c.pyc": b"\x00",
            "pkg.egg-info/d.txt": "",
        }
    )
    assert Project(root).paths == ["src/a.py"]


def test_read_text_respects_size_limit(make_project) -> None:
    root = make_project({"big.txt": "x" * 100, "small.txt": "ok"})
    project = Project(root, Config(max_text_bytes=10))
    assert project.read_text("big.txt") is None
    assert project.read_text("small.txt") == "ok"


def test_project_rejects_non_directory(tmp_path) -> None:
    with pytest.raises(NotADirectoryError):
        Project(tmp_path / "missing")


@pytest.mark.parametrize(
    ("line", "name", "spec", "pinned"),
    [
        ("numpy==1.26.0  # comment", "numpy", "==1.26.0", True),
        ("requests>=2 ; python_version>'3'", "requests", ">=2", False),
        (
            "torch @ https://example.com/torch.whl",
            "torch",
            "@ https://example.com/torch.whl",
            False,
        ),
        ("scikit-learn[extra]==1.4.2", "scikit-learn", "==1.4.2", True),
        ("pandas", "pandas", "", False),
    ],
)
def test_parse_requirement_line(line: str, name: str, spec: str, pinned: bool) -> None:
    req = parse_requirement(line, "requirements.txt")
    assert req is not None
    assert (req.name, req.spec, req.pinned) == (name, spec, pinned)


@pytest.mark.parametrize("line", ["", "# just a comment", "-r base.txt", "-e ."])
def test_parse_requirement_ignores_non_requirements(line: str) -> None:
    assert parse_requirement(line, "requirements.txt") is None


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("tests/test_x.py", True),
        ("src/pkg/tests/helpers.py", True),
        ("test_model.py", True),
        ("pkg/model_test.py", True),
        ("conftest.py", True),
        ("src/pkg/model.py", False),
        ("src/pkg/testing_utils.py", False),
    ],
)
def test_is_test_path(rel: str, expected: bool) -> None:
    assert is_test_path(rel) is expected


def test_normalize_name_matches_import_style() -> None:
    assert normalize_name("Scikit-Learn") == normalize_name("scikit_learn") == "scikit_learn"


def test_imports_and_declared_requirements(make_project) -> None:
    root = make_project(
        {
            "pyproject.toml": '[project]\nname="x"\ndependencies=["numpy==1.0"]\n',
            "requirements-dev.txt": "pytest>=8\n",
            "app/main.py": "import os\nimport numpy.linalg\nfrom sklearn.cluster import KMeans\n",
        }
    )
    project = Project(root)
    assert {"os", "numpy", "sklearn"} <= set(project.imports)
    declared = {r.name for r in project.requirements}
    assert declared == {"numpy", "pytest"}
    assert project.local_modules == {"app"}


def test_lfs_and_dvc_management(make_project) -> None:
    root = make_project(
        {
            ".gitattributes": "data/*.parquet filter=lfs diff=lfs merge=lfs -text\n",
            "data/a.parquet": b"x",
            "models/m.pkl": b"x",
            "models/m.pkl.dvc": "outs: []\n",
            "raw/r.csv": b"x",
        }
    )
    project = Project(root)
    assert project.is_managed("data/a.parquet")
    assert project.is_managed("models/m.pkl")
    assert not project.is_managed("raw/r.csv")
