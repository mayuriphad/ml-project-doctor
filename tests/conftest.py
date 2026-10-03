from __future__ import annotations

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

HEALTHY_README = textwrap.dedent(
    """\
    # Churn Predictor

    A small gradient-boosted model that predicts customer churn from usage logs.

    ## Installation

    ```bash
    uv sync
    ```

    ## Usage

    Train the model with a single command:

    ```bash
    python -m demo.train --config configs/base.yaml
    ```

    ## Reproducing results

    Seeds are fixed in `set_seed()`. Run the command above on the pinned
    environment in `uv.lock` to reproduce the metrics reported in our runs.
    """
)

HEALTHY_TRAIN = """\
import mlflow
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


def set_seed(seed: int) -> None:
    np.random.seed(seed)


def main() -> None:
    set_seed(42)
    X, y = np.zeros((10, 2)), np.zeros(10)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    with mlflow.start_run():
        model = LogisticRegression().fit(X_train, y_train)
        mlflow.log_metric("train_rows", len(X_train))
        mlflow.sklearn.log_model(model, "model")


if __name__ == "__main__":
    main()
"""

HEALTHY_PYPROJECT = """\
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy==1.26.4", "scikit-learn==1.4.2", "mlflow==2.13.0"]
"""


@pytest.fixture
def make_project(tmp_path: Path) -> Callable[[dict[str, str | bytes]], Path]:
    """Write a dict of ``relative_path -> content`` into a fresh project directory."""

    def _make(files: dict[str, str | bytes]) -> Path:
        for rel, content in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(textwrap.dedent(content), encoding="utf-8")
        return tmp_path

    return _make


@pytest.fixture
def healthy_files() -> dict[str, str]:
    return {
        "pyproject.toml": HEALTHY_PYPROJECT,
        "README.md": HEALTHY_README,
        "LICENSE": "MIT License\n\nCopyright (c) 2026\n",
        "uv.lock": "version = 1\n",
        ".python-version": "3.11\n",
        ".gitignore": "mlruns/\n__pycache__/\n",
        "Dockerfile": "FROM python:3.11-slim\n",
        "CHANGELOG.md": "# Changelog\n",
        "configs/base.yaml": "lr: 0.01\nepochs: 5\n",
        "src/demo/__init__.py": "",
        "src/demo/train.py": HEALTHY_TRAIN,
        "tests/test_train.py": "import pytest\n\n\ndef test_placeholder():\n    assert True\n",
    }
