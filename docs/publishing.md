# Publishing to PyPI

The release workflow uses PyPI **trusted publishing** (OIDC), so no API token is stored in GitHub.

## One-time setup

1. **Replace placeholders.** Set the real repository URLs in `pyproject.toml` under `[project.urls]`,
   and the author name and email you want shown on PyPI.
2. **Create the project on PyPI** by adding a trusted publisher at
   <https://pypi.org/manage/account/publishing/>:
   - PyPI project name: `ml-project-doctor`
   - Owner and repository: your GitHub org and repo
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. **Create a GitHub environment** named `pypi` (Settings, then Environments). Add required reviewers if you want a manual gate.
4. Optional: dry-run on TestPyPI by copying the workflow and pointing it at `https://test.pypi.org/legacy/`.

## Release checklist

```bash
# 1. Tests, lint and types pass on all supported Pythons
pytest
ruff check .
mypy

# 2. Bump the version in src/ml_project_doctor/__init__.py and CHANGELOG.md

# 3. Build and validate the artifacts locally
rm -rf dist
python -m build
twine check --strict dist/*

# 4. Smoke-test the wheel in a clean environment
python -m venv /tmp/smoke && /tmp/smoke/bin/pip install dist/*.whl
/tmp/smoke/bin/ml-project-doctor --version

# 5. Tag and publish a GitHub release
git tag v0.1.0 && git push origin v0.1.0
```

Creating a GitHub release for the tag triggers `.github/workflows/publish.yml`, which builds the
sdist and wheel and uploads them to PyPI.

## Versioning

The version is defined once, in `src/ml_project_doctor/__init__.py` (`__version__`), and read by Hatchling.
Follow Semantic Versioning:

- **PATCH:** fixes to existing checks, no change in findings beyond the bug
- **MINOR:** new checks, new report fields, new options
- **MAJOR:** removed checks or options, changed JSON schema, changed exit-code meaning

Adding a check can change scores for existing users, so call it out in the changelog.
