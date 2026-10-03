from __future__ import annotations

import pytest

from ml_project_doctor.checks import all_checks
from ml_project_doctor.engine import audit
from ml_project_doctor.models import CATEGORIES, Severity


def _ids(report) -> set[str]:
    return {f.check_id for f in report.findings}


def _findings(report, check_id: str):
    return [f for f in report.findings if f.check_id == check_id]


# -- whole-project behaviour ----------------------------------------------------------


def test_registry_has_all_categories() -> None:
    specs = all_checks()
    assert len(specs) >= 30
    assert {spec.category for spec in specs.values()} == set(CATEGORIES)
    assert all(spec.description for spec in specs.values()), "every check needs a docstring"


def test_empty_project_reports_core_errors(make_project) -> None:
    report = audit(make_project({}))
    assert {"DEP001", "DOC001"} <= _ids(report)
    assert report.fails(Severity.ERROR)
    assert report.score < 100


def test_healthy_project_has_no_errors(make_project, healthy_files) -> None:
    report = audit(make_project(healthy_files))
    assert report.max_severity() is not Severity.ERROR, report.findings
    assert report.score >= 90


def test_category_filter(make_project) -> None:
    report = audit(make_project({}), categories=["data"])
    assert report.findings
    assert {f.category for f in report.findings} == {"data"}
    assert set(report.category_scores) == {"data"}


def test_ignore_suppresses_check(make_project) -> None:
    report = audit(make_project({}), ignore=["DOC001"])
    assert "DOC001" not in _ids(report)


def test_unknown_ignore_id_is_an_error(make_project) -> None:
    with pytest.raises(ValueError, match="unknown check id"):
        audit(make_project({}), ignore=["NOPE999"])


def test_unknown_category_is_an_error(make_project) -> None:
    with pytest.raises(ValueError, match="unknown categor"):
        audit(make_project({}), categories=["vibes"])


# -- individual checks -----------------------------------------------------------------


def test_unpinned_requirements_flagged(make_project) -> None:
    root = make_project({"requirements.txt": "numpy\npandas==2.1.0\n"})
    hits = _findings(audit(root), "REP002")
    assert len(hits) == 1
    assert hits[0].path == "requirements.txt"
    assert "numpy" in hits[0].message


def test_missing_seed_flagged_and_cleared_by_seed(make_project) -> None:
    code = "def run(model, X, y):\n    model.fit(X, y)\n"
    assert "REP003" in _ids(audit(make_project({"train.py": code})))

    seeded = "import numpy as np\nnp.random.seed(0)\n" + code
    assert "REP003" not in _ids(audit(make_project({"train.py": seeded})))


def test_fit_transform_before_split_is_leakage(make_project) -> None:
    leaky = """\
        from sklearn.model_selection import train_test_split
        X_scaled = scaler.fit_transform(X)
        X_train, X_test = train_test_split(X_scaled)
    """
    clean = """\
        from sklearn.model_selection import train_test_split
        X_train, X_test = train_test_split(X)
        X_train = scaler.fit_transform(X_train)
    """
    assert "TRN005" in _ids(audit(make_project({"prep.py": leaky})))
    assert "TRN005" not in _ids(audit(make_project({"prep.py": clean})))


def test_undeclared_import_flagged_with_distribution_mapping(make_project) -> None:
    root = make_project(
        {
            "pyproject.toml": '[project]\nname="x"\ndependencies=["numpy==1.0"]\n',
            "app.py": "import sklearn\nimport numpy\n",
        }
    )
    hits = _findings(audit(root), "DEP003")
    assert len(hits) == 1
    assert "sklearn (package scikit-learn)" in hits[0].message
    assert "numpy" not in hits[0].message


def test_declared_import_is_not_flagged(make_project) -> None:
    root = make_project(
        {
            "pyproject.toml": '[project]\nname="x"\ndependencies=["scikit-learn==1.4.2"]\n',
            "app.py": "import sklearn\n",
        }
    )
    assert "DEP003" not in _ids(audit(root))


def test_test_only_imports_are_not_flagged(make_project) -> None:
    root = make_project(
        {
            "pyproject.toml": '[project]\nname="x"\ndependencies=["numpy==1.0"]\n',
            "tests/test_x.py": "import hypothesis\n",
        }
    )
    assert "DEP003" not in _ids(audit(root))


def test_risky_specifier_flagged(make_project) -> None:
    root = make_project({"requirements.txt": "mylib @ git+https://github.com/x/mylib.git\nnumpy==1.26.0\n"})
    hits = _findings(audit(root), "DEP002")
    assert [h.path for h in hits] == ["requirements.txt"]


def test_absolute_path_flagged(make_project) -> None:
    config = 'data_dir: "C:\\\\Users\\\\bob\\\\datasets"\n'
    hits = _findings(audit(make_project({"configs/base.yaml": config})), "REP005")
    assert len(hits) == 1
    assert hits[0].path == "configs/base.yaml"


def test_large_data_needs_lfs(make_project) -> None:
    files = {
        "pyproject.toml": "[tool.ml-project-doctor]\nlarge_file_mb = 0.001\n",
        "data/train.csv": b"a" * 2000,
    }
    assert "DQ002" in _ids(audit(make_project(files)))

    files[".gitattributes"] = "data/*.csv filter=lfs diff=lfs merge=lfs -text\n"
    assert "DQ002" not in _ids(audit(make_project(files)))


def test_large_model_binary_is_error(make_project) -> None:
    files = {
        "pyproject.toml": "[tool.ml-project-doctor]\nlarge_file_mb = 0.001\n",
        "models/best.pt": b"w" * 2000,
    }
    hits = _findings(audit(make_project(files)), "MDL001")
    assert hits and hits[0].severity is Severity.ERROR


def test_unsafe_deserialisation_flagged(make_project) -> None:
    code = (
        "import joblib, torch\n"
        "m = joblib.load('m.joblib')\n"
        "w = torch.load('w.pt')\n"
        "safe = torch.load('w.pt', weights_only=True)\n"
    )
    hits = _findings(audit(make_project({"serve.py": code})), "MDL003")
    assert len(hits) == 2
    assert {h.message.split(":")[0] for h in hits} == {"line 2", "line 3"}


def test_notebook_outputs_flagged(make_project) -> None:
    notebook = (
        '{"cells": [{"cell_type": "code", "execution_count": 1, '
        '"outputs": [{"output_type": "stream"}], "source": []}], "nbformat": 4}'
    )
    assert "EXP003" in _ids(audit(make_project({"analysis.ipynb": notebook})))


# -- resilience -----------------------------------------------------------------------


def test_crashing_check_is_isolated(make_project, monkeypatch) -> None:
    from ml_project_doctor.checks.base import REGISTRY, CheckSpec

    def boom(project):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(REGISTRY, "ZZ999", CheckSpec("ZZ999", "data", "boom", boom, ""))
    report = audit(make_project({"README.md": "x"}))

    crash = _findings(report, "ZZ999")
    assert crash and crash[0].severity is Severity.ERROR
    assert "kaboom" in crash[0].message
    assert any(c.check_id == "ZZ999" and c.status == "error" for c in report.checks)
    # Other checks still ran.
    assert any(c.check_id == "DOC001" for c in report.checks)
