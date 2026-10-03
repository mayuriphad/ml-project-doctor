# Check catalogue

Each check has an ID, a category and a default severity. Severities are `info`, `warning` and `error`.
Use `ml-project-doctor --list-checks` to see the checks installed in your version.

Detection is static. Checks read files and parse Python with `ast` or regular expressions. None of them execute your code.

## Data (`data`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| DQ001 | Dataset files present | info | No CSV, Parquet, HDF5, Arrow or similar files in the repo. Fine if data is fetched at runtime; document where it comes from. |
| DQ002 | Large data files managed by Git LFS or DVC | error | A data file above `large_file_mb` is committed directly to Git. Track it with `git lfs track` or `dvc add`. |
| DQ003 | Data validation present | warning | Code loads data but no schema or quality validation was found. Add Great Expectations, Pandera, pydantic, or explicit assertions. |
| DQ004 | Datasets documented | info | A data directory has no README, data card or datasheet in it or in an ancestor directory. |

## Reproducibility (`reproducibility`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| REP001 | Dependency lock file present | warning | No `uv.lock`, `poetry.lock`, `pdm.lock`, `conda-lock.yml` or similar, and requirements files are not fully pinned. |
| REP002 | Requirements pinned | warning | A requirements file lists packages without `==`. Pin exact versions. |
| REP003 | Random seeds set | warning | Training code (`.fit(`, `Trainer(`) exists but no seeding call (`set_seed`, `random_state=`, `torch.manual_seed`, ...) was found. |
| REP004 | Python version pinned | info | No `requires-python`, `.python-version`, `runtime.txt`, or pinned Dockerfile `FROM python:X`. |
| REP005 | No hardcoded absolute paths | warning | Code or config contains `/home/...`, `/Users/...` or `C:\Users\...`. Use relative paths or configuration. |
| REP006 | Container definition present | info | No Dockerfile. Containers pin the OS, system libraries and Python. |
| REP007 | Container base image pinned | warning | A Dockerfile `FROM` has no tag or uses `:latest`. Pin a version or digest. |

## Training (`training`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| TRN001 | Training entrypoint present | info | Training code exists but no file is named like `train.py`. Expose one documented command. |
| TRN002 | Train/validation/test split | warning | Training runs but no split (`train_test_split`, k-fold, `validation_split`, ...) was found. |
| TRN003 | Checkpointing or early stopping | info | No checkpoint saving or early stopping found. Long runs cannot resume and may overfit. |
| TRN004 | Hyperparameters externalised | warning | Training code exists but the repo has no YAML/TOML/JSON configuration files. |
| TRN005 | Preprocessing fitted after the split | warning | `fit_transform` appears before `train_test_split` in the same file. Possible target leakage. Split first, or use a Pipeline. |

## Experiments (`experiments`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| EXP001 | Experiment tracking in use | warning | Training code exists but no tracker (MLflow, W&B, Neptune, ClearML, TensorBoard, ...) was detected. |
| EXP002 | Tracking output kept out of Git | warning | `mlruns/`, `wandb/`, `lightning_logs/` and similar directories are present and not mentioned in `.gitignore`. |
| EXP003 | Notebooks free of saved outputs | info | A `.ipynb` file has saved cell outputs. Clear them with `nbstripout` before committing. |

## Models (`models`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| MDL001 | Model binaries managed | error / warning | A model file is above `large_file_mb` (error) or above 5 MB (warning) and is committed directly to Git. Use LFS, DVC or a registry. |
| MDL002 | Model card present | warning | Model artifacts are present but no `MODEL_CARD.md` (or `model_card.md`) exists. |
| MDL003 | No unsafe deserialisation | warning | Code calls `pickle.load`, `joblib.load`, or `torch.load` without `weights_only=True`. Loading untrusted pickles can run arbitrary code. |
| MDL004 | Serving health endpoint | info | A serving framework (FastAPI, Flask, BentoML, ...) is used but no `/health` or `/ready` route was found. |
| MDL005 | Model versioning or registry | info | Model artifacts exist but no registry, checksum or DVC record was detected. |

## Dependencies (`dependencies`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| DEP001 | Dependency manifest present | error | No `requirements*.txt`, `pyproject.toml` with dependencies, `setup.py`, `setup.cfg`, `environment.yml` or `Pipfile`. |
| DEP002 | Dependency specifiers are portable | warning | A requirement uses a Git URL, a local `file:` path, a dev build, or `==0.0.0`. |
| DEP003 | Imports declared as dependencies | warning | Project code imports a third-party package that no manifest declares. Import names are mapped to package names (for example `sklearn` to `scikit-learn`). Test-only imports are ignored. |
| DEP004 | Declared dependencies are used | info | A declared package is never imported. Tooling such as pytest and ruff is excluded. |

## Documentation (`documentation`)

| ID | Check | Severity | What it looks for and how to fix it |
| --- | --- | --- | --- |
| DOC001 | README present | error | No README at the repository root. |
| DOC002 | README has substance | warning | README is under 300 characters. |
| DOC003 | README covers installation and usage | warning | README has no installation or usage section. |
| DOC004 | Reproduction instructions | info | README does not mention training, reproduction or experiments. |
| DOC005 | License file present | warning | No `LICENSE` file at the root. |
| DOC006 | Changelog present | info | No `CHANGELOG` or `HISTORY` file at the root. |

## Engine behaviour

- If a check raises an exception, the engine records an `error` finding with the exception text (check ID
  `<id>`, message `check raised ...`) and continues with the other checks. Its `status` is `error` in the report.
- Files over `max_text_bytes` are not read by text-based checks.
- The following directories are never scanned: `.git`, `.venv`, `venv`, `env`, `.tox`, `__pycache__`,
  `node_modules`, `site-packages`, `build`, `dist`, `*.egg-info`.
