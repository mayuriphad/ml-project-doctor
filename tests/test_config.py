from __future__ import annotations

import pytest

from ml_project_doctor.config import ConfigError, config_from_mapping, load_config
from ml_project_doctor.models import Severity


def test_missing_pyproject_yields_defaults(tmp_path) -> None:
    config = load_config(tmp_path)
    assert config.fail_on is Severity.ERROR
    assert config.ignore == frozenset()


def test_section_is_parsed(make_project) -> None:
    root = make_project(
        {
            "pyproject.toml": (
                "[tool.ml-project-doctor]\n"
                'fail_on = "warning"\n'
                'ignore = ["doc006", "dep004"]\n'
                "large_file_mb = 10\n"
            )
        }
    )
    config = load_config(root)
    assert config.fail_on is Severity.WARNING
    assert config.ignore == frozenset({"DOC006", "DEP004"})
    assert config.large_file_mb == 10.0


def test_unknown_option_is_rejected() -> None:
    with pytest.raises(ConfigError, match="unknown option"):
        config_from_mapping({"fial_on": "error"})


@pytest.mark.parametrize(
    ("section", "message"),
    [
        ({"fail_on": "catastrophic"}, "invalid severity"),
        ({"ignore": "DOC006"}, "'ignore' must be a list"),
        ({"large_file_mb": 0}, "'large_file_mb' must be a positive number"),
        ({"large_file_mb": True}, "'large_file_mb' must be a positive number"),
        ({"max_text_bytes": -1}, "'max_text_bytes' must be a positive integer"),
    ],
)
def test_invalid_values_are_rejected(section: dict, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        config_from_mapping(section)


def test_invalid_toml_raises(make_project) -> None:
    root = make_project({"pyproject.toml": "[tool.ml-project-doctor\n"})
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(root)
