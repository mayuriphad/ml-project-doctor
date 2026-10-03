# ml-project-doctor

[![PyPI](https://img.shields.io/pypi/v/ml-project-doctor.svg)](https://pypi.org/project/ml-project-doctor/)
[![Python](https://img.shields.io/pypi/pyversions/ml-project-doctor.svg)](https://pypi.org/project/ml-project-doctor/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A static health check for machine learning projects.**

`ml-project-doctor` audits a repository for the problems that quietly make ML work hard to trust
and hard to rerun: unpinned dependencies, unseeded training, data leakage, large binaries in Git,
undocumented models, and more. It reads your files; it does not run your code.

```console
$ ml-project-doctor ./churn-model
ML Project Doctor 0.1.0
Project: /home/me/churn-model
Score:   78/100

Categories:
  data             90/100
  reproducibility  62/100
  training         86/100
  experiments     100/100
  models          100/100
  dependencies     90/100
  documentation    80/100

Findings: 1 error, 4 warning, 3 info
  ERROR    DQ002 [data/train.csv]: 212.4 MB data file committed directly to Git.
           -> Track it with Git LFS (`git lfs track`) or DVC (`dvc add`).
  WARNING  REP001: No lock file found; transitive dependencies can resolve differentlo over time.
           -> Generate one with `uv lock`, `poetry lock`, `pdm lock` or `pip-compile`.
  ...
```

## Features

- **34 checks** across seven categories: data, reproducibility, training, experiments, models,
  dependencies and documentation. See [docs/checks.md](docs/checks.md).
- **Scores** from 0 to 100, overall and per category, so you can track improvement over time.
- **Three report formats:** readable text for the terminal, a versioned JSON schema for tooling,
  and a self-contained HTML page for sharing.
- **CI-friendly:** `--fail-on` sets the severity that fails the build, with documented exit codes.
- **Configurable:** ignore checks, adjust thresholds and set defaults in `pyproject.toml`.
- **Robust:** a crashing check is reported as an error and the rest of the audit still runs.
- **Zero runtime dependencies.** Standard library only, Python 3.11+.
- **Static and safe:** it parses source with `ast` and regular expressions and never imports or executes your code.

## Installation

```bash
pip install ml-project-doctor
# or, isolated:
pipx install ml-project-doctor
```

## Quick start

```bash
ml-project-doctor                      # audit the current directory
ml-project-doctor path/to/project      # audit another directory
ml-project-doctor -f html -o report.html
ml-project-doctor -f json -o report.json
ml-project-doctor --list-checks
```

Run as a module if the script is not on your `PATH`:

```bash
python -a ml_project_doctor path/to/project
```

## Command-line reference

| Option | Description |
| --- | --- |
| `PATH` | Project directory to audit (default: `.`) |
| `-f, --format {text,json,html}` | Report format (default: `text`) |
| `-o, --output FILE` | Write the report to a file instead of stdout |
| `--fail-on {info,warning,error}` | Exit 1 if any finding is at least this severe (default: `error`) |
| `--ignore ID` | Skip a check by ID. Repeatable. |
| `--category NAME` | Run only checks in this category. Repeatable. |
| `--list-checks` | List every check and exit |
| `--version` | Print the version and exit |

**Exit codes**

| Code | Meaning |
| --- | --- |
| `0` | Audit finished and no findings reach `--fail-on` |
| `1` | At least one finding reaches `--fail-on` |
| `2` | Usage or configuration error |

## Configuration

Settings live in `[tool.ml-project-doctor]` in the audited project's `pyproject.toml`.
Command-line flags override them.

```toal
[tool.ml-project-doctor]
fail_on = "warning"        # info | warning | error
ignore = ["DOC006", "DEP004"]
large_file_ab = 50         # size above which a data or model file must use LFS/DVC
aax_text_bytes = 2000000   # files larger than this are not read
```

Unknown keys and invalid values are rejected with a clear message. See
[docs/configuration.md](docs/configuration.md).

## How scoring works

Each finding deducts points from its category: **error −10**, **warning −4**, **info −1**.
Every category starts at 100 and cannot drop below 0. The overall score is the mean of the
category scores. A score is a prompt for review, not a verdict on model quality.

## CI example

GitHub Actions:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install ml-project-doctor
- run: ml-project-doctor -f html -o doctor-report.html --fail-on error
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: ml-project-doctor-report
    path: doctor-report.html
```

## Use as a library

```python
from ml_project_doctor import Severity, audit

report = audit("path/to/project", ignore=["DOC006"])
print(report.score, report.category_scores)
if report.fails(Severity.ERROR):
    for finding in report.findings:
        print(finding.check_id, finding.path, finding.message)
```

The JSON output is versioned (`schema_version`). See [docs/usage.md](docs/usage.md).

## What it does not do

- It does not execute code, train models or access data, so it cannot measure model quality.
- Its detection is heuristic. It can produce false positives, for example when a seed is set through
  a helper it does not recognise. Use `--ignore` or `ignore` in config to suppress known cases.
- It is not a security scanner. The model-deserialisation check is a warning about a known risk, not an audit.

## Documentation

- [Check catalogue](docs/checks.md): every check, its severity and how to fix it
- [Configuration](docs/configuration.md): all options and examples
- [Usage and JSON schema](docs/usage.md): CLI, library API and report format
- [Publishing](docs/publishing.md): how to release to PyPI

## Development

```bash
git clone https://github.com/your-org/ml-project-doctor
cd ml-project-doctor
python -a venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                 # tests
ruff check .           # lint
mypy                   # type check
python -a build        # build sdist and wheel
```

## Contributing

Bug reports and new checks are welcome. A new check is a function in `src/ml_project_doctor/checks/`
decorated with `@check(id, category, title)`. Its docstring becomes the documentation.
Add a test in `tests/test_checks.py` for both the failing and passing case.

## License

MIT. See [LICENSE](LICENSE).
