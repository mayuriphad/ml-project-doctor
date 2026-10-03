# Usage

## Command line

```console
ml-project-doctor [PATH] [-f text|json|html] [-o FILE] [--fail-on SEVERITY]
                  [--ignore ID ...] [--category NAME ...] [--list-checks]
```

Typical workflows:

```console
# Terminal summary
ml-project-doctor .

# Shareable HTML page
ml-project-doctor . -f html -o reports/doctor.html

# Machine-readable output for dashboards
ml-project-doctor . -f json -o reports/doctor.json

# Strict mode in CI: fail on warnings
ml-project-doctor . --fail-on warning

# Focus on one area
ml-project-doctor . --category models --category dependencies
```

Writing to a file creates missing parent directories. The confirmation message goes to stderr, so
stdout stays clean for piping.

## Python API

```python
from ml_project_doctor import Severity, audit

report = audit("path/to/project")

print(f"score={report.score}")
for name, score in report.category_scores.items():
    print(f"  {name}: {score}")

for finding in report.findings:
    if finding.severity is Severity.ERROR:
        print(finding.check_id, finding.path, finding.message)

if report.fails(Severity.WARNING):
    raise SystemExit(1)
```

`audit()` accepts these keyword arguments:

| Argument | Description |
| --- | --- |
| `config` | A `Config` object. When omitted, the project's `pyproject.toml` is read. |
| `categories` | Iterable of category names. When omitted, all categories run. |
| `ignore` | Iterable of check IDs, combined with the configured ignore list. |

It raises `ValueError` for unknown IDs or categories, and `ConfigError` (a `ValueError`) for invalid configuration.

To render a report in another format:

```python
from ml_project_doctor.reporters import to_html, to_json, to_text

open("report.html", "w", encoding="utf-8").write(to_html(report))
```

## JSON report schema

The JSON report has `schema_version: "1.0"`. Breaking changes will increment the major version.

```json
{
  "schema_version": "1.0",
  "tool": {"name": "ml-project-doctor", "version": "0.1.0"},
  "project_path": "/abs/path/to/project",
  "generated_at": "2026-10-03T12:00:00+00:00",
  "score": 78,
  "category_scores": {"data": 90, "reproducibility": 62, "...": 0},
  "summary": {"total": 5, "info": 3, "warning": 1, "error": 1},
  "checks": [
    {"check_id": "DQ001", "category": "data", "title": "Dataset files present",
     "status": "passed", "finding_count": 0}
  ],
  "findings": [
    {"check_id": "REP002", "category": "reproducibility", "title": "Requirements pinned",
     "severity": "warning", "message": "2 requirement(s) not pinned with '==': numpy, pandas",
     "path": "requirements.txt", "recommendation": "Pin exact versions (name==x.y.z) or use a lock file."}
  ]
}
```

`checks[].status` is one of `passed`, `failed` (findings were produced) or `error` (the check crashed).
`path` is relative to the project root, with forward slashes, and may be `null`.
