"""Regular expressions shared by several checks. Matched line by line."""

from __future__ import annotations

import re

# Training
FIT_RE = re.compile(r"\.fit\(|Trainer\(|fit_generator\(|optimizer\.step\(")
SEED_RE = re.compile(
    r"random\.seed\(|np\.random\.seed\(|numpy\.random\.seed\(|torch\.manual_seed\("
    r"|tf\.random\.set_seed\(|set_seed\(|seed_everything\(|random_state\s*=|PYTHONHASHSEED"
)
SPLIT_RE = re.compile(
    r"train_test_split|KFold|GroupKFold|TimeSeriesSplit|validation_split|val_size"
    r"|valid_size|test_size|random_split|split_dataset|train_val_split"
)
CHECKPOINT_RE = re.compile(
    r"ModelCheckpoint|EarlyStopping|early_stopping|save_checkpoint|torch\.save\("
    r"|save_pretrained\(|save_model\(|\.log_model\(|checkpoint",
    re.IGNORECASE,
)
ENTRYPOINT_RE = re.compile(r"^(train|training|fit|run_training|main|__main__)[\w-]*\.py$", re.IGNORECASE)
FIT_TRANSFORM_RE = re.compile(r"\.fit_transform\(")
TRAIN_SPLIT_CALL_RE = re.compile(r"train_test_split\(")

# Data
LOADER_RE = re.compile(
    r"read_csv|read_parquet|read_json|read_excel|read_sql|read_feather|load_dataset"
    r"|np\.load\(|tf\.data\.|torchvision\.datasets"
)
VALIDATION_CODE_RE = re.compile(
    r"validate_schema|check_schema|expect_column|\.validate\(|assert\s+.*\.shape\b"
    r"|assert\s+.*\.isna\(\)"
)

# Experiments
TRACKING_CODE_RE = re.compile(r"log_metrics?\(|log_params?\(|add_scalars?\(|wandb\.log\(|mlflow\.")

# Models
REGISTRY_RE = re.compile(r"register_model|model_registry|model_version|sha256|hashlib\.|dvc", re.IGNORECASE)
HEALTH_RE = re.compile(r"""["']/?(health|healthz|readyz?)["']""")
UNSAFE_LOAD_RE = re.compile(r"pickle\.loads?\(|joblib\.load\(|torch\.load\((?![^)]*weights_only\s*=\s*True)")

# Reproducibility
ABS_PATH_RE = re.compile(r"""["'](?:/home/|/Users/|[A-Za-z]:[\\/]+Users[\\/])[^"']*["']""")
FROM_RE = re.compile(r"^\s*FROM\s+(\S+)", re.IGNORECASE)

# Documentation
DOC_NAME_RE = re.compile(r"^(readme|datacard|data_card|data-card|datasheet)", re.IGNORECASE)
