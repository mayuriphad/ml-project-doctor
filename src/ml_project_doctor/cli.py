"""Command-line interface: ``ml-project-doctor [PATH] [options]``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .checks import all_checks
from .config import ConfigError, load_config
from .engine import audit
from .models import CATEGORIES, Severity
from .reporters import to_html, to_json, to_text

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

_RENDERERS = {"text": to_text, "json": to_json, "html": to_html}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ml-project-doctor",
        description="Audit an ML/MLOps project for data quality, reproducibility, training, "
        "experiments, models, dependencies and documentation.",
        epilog="Exit codes: 0 = no findings at or above --fail-on, 1 = such findings exist, "
        "2 = usage or configuration error.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory to audit (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=sorted(_RENDERERS),
        default="text",
        help="report format (default: text)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="FILE",
        help="write the report to FILE instead of stdout",
    )
    parser.add_argument(
        "--fail-on",
        choices=[s.value for s in Severity],
        help="exit with 1 when a finding has at least this severity (default: config, else error)",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="ID",
        help="skip a check by ID (repeatable)",
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=CATEGORIES,
        metavar="NAME",
        help=f"run only checks in this category (repeatable): {', '.join(CATEGORIES)}",
    )
    parser.add_argument("--list-checks", action="store_true", help="list available checks and exit")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        for spec in all_checks().values():
            print(f"{spec.id:<8} {spec.category:<16} {spec.title}")
        return EXIT_OK

    root = Path(args.path)
    if not root.is_dir():
        parser.error(f"not a directory: {args.path}")

    try:
        config = load_config(root.resolve())
        fail_on = Severity.parse(args.fail_on) if args.fail_on else config.fail_on
        report = audit(root, config=config, categories=args.category, ignore=args.ignore)
    except (ConfigError, ValueError) as exc:
        print(f"ml-project-doctor: error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    rendered = _RENDERERS[args.format](report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        _write_stdout(rendered)

    return EXIT_FINDINGS if report.fails(fail_on) else EXIT_OK


def _write_stdout(text: str) -> None:
    stream = sys.stdout
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.buffer.write(text.encode("utf-8", errors="replace"))
        stream.flush()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
