# Configuration

ml-project-doctor reads its settings from `[tool.ml-project-doctor]` in the audited project's
`pyproject.toml`. If the file or the section is missing, defaults apply.

```toml
[tool.ml-project-doctor]
fail_on = "error"
ignore = ["DOC006"]
large_file_mb = 50
max_text_bytes = 2000000
```

## Options

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `fail_on` | string | `"error"` | Lowest severity that makes the exit code 1: `"info"`, `"warning"` or `"error"`. |
| `ignore` | list of strings | `[]` | Check IDs to skip, for example `["DOC006", "DEP004"]`. Case-insensitive. Unknown IDs are an error. |
| `large_file_mb` | number > 0 | `50` | Size in MB above which a data or model file must be managed by Git LFS or DVC. |
| `max_text_bytes` | integer > 0 | `2000000` | Files larger than this are skipped by text-based checks. This keeps large data files from slowing the audit. |

Unknown keys are rejected, so a typo such as `fial_on` fails with a clear error and exit code 2.

## Precedence

1. Command-line flags (`--fail-on`, `--ignore`, `--category`) override the config file.
2. `--ignore` values are combined with `ignore` from the config, not substituted.
3. The config file is read from the directory being audited, not from the current directory.

## Examples

**Fail the build on warnings, but accept known gaps:**

```toml
[tool.ml-project-doctor]
fail_on = "warning"
ignore = ["DOC006", "EXP003"]
```

**Allow larger files in Git (for example, a small team that accepts the cost):**

```toml
[tool.ml-project-doctor]
large_file_mb = 200
```

**Audit only the data and reproducibility categories from the command line:**

```console
ml-project-doctor --category data --category reproducibility
```
