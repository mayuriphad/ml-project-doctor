# Changelog

All notable changes are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-03

### Added

- Audit engine that runs 34 checks across seven categories: data, reproducibility,
  training, experiments, models, dependencies and documentation.
- Scoring: per-category and overall scores from 0 to 100.
- Reports in text, JSON (versioned schema) and self-contained HTML.
- CLI `ml-project-doctor` with `--format`, `--output`, `--fail-on`, `--ignore`,
  `--category` and `--list-checks`. Exit codes: 0 pass, 1 findings, 2 usage error.
- Configuration via `[tool.ml-project-doctor]` in `pyproject.toml`.
- Crash isolation: a failing check is reported as an error and the audit continues.
- Zero runtime dependencies; Python 3.11+.
