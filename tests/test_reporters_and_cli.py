from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from ml_project_doctor.cli import main
from ml_project_doctor.engine import audit
from ml_project_doctor.models import Finding, Report, Severity
from ml_project_doctor.reporters import to_html, to_json, to_text


def _report(findings: list[Finding] | None = None) -> Report:
    return Report(
        project_path="/tmp/p",
        tool_version="0.1.0",
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        findings=findings or [],
        checks=[],
        score=90,
        category_scores={"data": 90},
    )


def test_json_round_trips(make_project) -> None:
    report = audit(make_project({}))
    data = json.loads(to_json(report))
    assert data["schema_version"] == "1.0"
    assert data["score"] == report.score
    assert data["summary"]["total"] == len(report.findings)
    assert all({"check_id", "severity", "message"} <= set(f) for f in data["findings"])


def test_text_report_lists_findings(make_project) -> None:
    text = to_text(audit(make_project({})))
    assert "Score:" in text
    assert "DOC001" in text
    assert "-> " in text  # recommendations are shown


def test_html_escapes_user_content() -> None:
    finding = Finding("X1", "data", "t", Severity.WARNING, "<script>alert(1)</script>", path="a&b.csv")
    page = to_html(_report([finding]))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "a&amp;b.csv" in page
    assert page.startswith("<!doctype html>")


def test_cli_list_checks(capsys) -> None:
    assert main(["--list-checks"]) == 0
    assert "DQ001" in capsys.readouterr().out


def test_cli_writes_json_and_exits_1_on_errors(make_project, tmp_path) -> None:
    project = make_project({})
    out = tmp_path / "reports" / "audit.json"
    code = main([str(project), "--format", "json", "-o", str(out)])
    assert code == 1
    assert json.loads(out.read_text(encoding="utf-8"))["findings"]


def test_cli_exit_zero_for_healthy_project(make_project, healthy_files, capsys) -> None:
    project = make_project(healthy_files)
    assert main([str(project), "--fail-on", "error"]) == 0
    assert "Score:" in capsys.readouterr().out


def test_cli_fail_on_warning_is_stricter(make_project, healthy_files) -> None:
    healthy_files["README.md"] = "# Short\n"  # triggers DOC002 (warning)
    project = make_project(healthy_files)
    assert main([str(project), "--fail-on", "error"]) == 0
    assert main([str(project), "--fail-on", "warning"]) == 1


def test_cli_unknown_ignore_id_exits_2(make_project, capsys) -> None:
    assert main([str(make_project({})), "--ignore", "NOPE"]) == 2
    assert "unknown check id" in capsys.readouterr().err


def test_cli_missing_directory_exits_2(tmp_path) -> None:
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "nope")])
    assert exc.value.code == 2


def test_cli_invalid_fail_on_is_rejected_by_argparse() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--fail-on", "catastrophic"])
    assert exc.value.code == 2
