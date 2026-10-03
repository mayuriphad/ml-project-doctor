"""Project scanning and the helpers every check uses to inspect a repository."""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Any

from .config import Config

SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".nox",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".ipynb_checkpoints",
        "node_modules",
        "site-packages",
        "build",
        "dist",
    }
)

_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")
_EXACT_VERSION_RE = re.compile(r"\d+(\.\d+)*")


def normalize_name(name: str) -> str:
    """PEP 503-style normalisation, with underscores so names compare with import names."""
    return re.sub(r"[-_.]+", "_", name).lower()


def is_pinned(spec: str) -> bool:
    """True for an exact version specifier such as ``==1.2.3`` (or a bare Poetry ``1.2.3``)."""
    text = spec.strip()
    if text.startswith(("==", "===")):
        return "*" not in text
    return _EXACT_VERSION_RE.fullmatch(text) is not None


def is_test_path(rel: str) -> bool:
    """True for test code, which is excluded from source-level checks."""
    path = PurePosixPath(rel)
    if any(part in ("tests", "test") for part in path.parts[:-1]):
        return True
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def is_requirements_file(rel: str) -> bool:
    path = PurePosixPath(rel)
    if path.suffix.lower() != ".txt":
        return False
    return path.name.lower().startswith("requirements") or (
        len(path.parts) > 1 and path.parts[0].lower() == "requirements"
    )


@dataclass(frozen=True)
class Requirement:
    """A declared dependency."""

    name: str
    spec: str
    source: str

    @property
    def normalized(self) -> str:
        return normalize_name(self.name)

    @property
    def pinned(self) -> bool:
        return is_pinned(self.spec)


def parse_requirement(line: str, source: str) -> Requirement | None:
    """Parse one PEP 508 requirement line. Returns None for comments and option lines."""
    text = re.split(r"\s+#", line, maxsplit=1)[0].strip()
    if not text or text.startswith(("#", "-")):
        return None
    text = text.split(";", 1)[0].strip()  # drop environment markers
    match = _REQUIREMENT_RE.match(text)
    if match is None:
        return None
    return Requirement(name=match.group(1), spec=match.group(3).strip(), source=source)


class Project:
    """A snapshot of a project directory, with lazily computed, cached views of its contents."""

    def __init__(self, root: str | Path, config: Config | None = None) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"not a directory: {root}")
        self.config = config or Config()
        self._sizes: dict[str, int] = {}
        self._text_cache: dict[str, str | None] = {}
        self._scan()

    def _scan(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info"))
            for name in filenames:
                full = Path(dirpath, name)
                try:
                    size = full.stat().st_size
                except OSError:
                    continue
                self._sizes[full.relative_to(self.root).as_posix()] = size
        self.paths: list[str] = sorted(self._sizes)

    # -- file queries -----------------------------------------------------------------

    def exists(self, rel: str) -> bool:
        return rel in self._sizes

    def size(self, rel: str) -> int:
        return self._sizes[rel]

    def has_dir(self, rel: str) -> bool:
        prefix = rel.rstrip("/") + "/"
        return any(path.startswith(prefix) for path in self.paths)

    def select(self, predicate: Callable[[str], bool]) -> list[str]:
        return [path for path in self.paths if predicate(path)]

    def with_suffix(self, *suffixes: str) -> list[str]:
        wanted = tuple(s.lower() for s in suffixes)
        return self.select(lambda p: PurePosixPath(p).suffix.lower() in wanted)

    def python_files(self) -> list[str]:
        """Project source files, excluding test code."""
        return [p for p in self.with_suffix(".py") if not is_test_path(p)]

    def read_text(self, rel: str) -> str | None:
        """Text of a file, or None if it is missing, unreadable or larger than the size limit."""
        if rel in self._text_cache:
            return self._text_cache[rel]
        text: str | None = None
        if rel in self._sizes and self._sizes[rel] <= self.config.max_text_bytes:
            try:
                # utf-8-sig tolerates a leading byte-order mark, which some Windows editors add.
                text = (self.root / rel).read_bytes().decode("utf-8-sig", errors="replace")
            except OSError:
                text = None
        self._text_cache[rel] = text
        return text

    def grep(self, pattern: re.Pattern[str], rels: Iterable[str] | None = None) -> list[tuple[str, int, str]]:
        """Return ``(path, line_number, stripped_line)`` for every matching line."""
        hits: list[tuple[str, int, str]] = []
        for rel in self.python_files() if rels is None else rels:
            text = self.read_text(rel)
            if text is None:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    hits.append((rel, lineno, line.strip()))
        return hits

    # -- parsed views -----------------------------------------------------------------

    @cached_property
    def pyproject(self) -> dict[str, Any]:
        text = self.read_text("pyproject.toml")
        if text is None:
            return {}
        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return {}

    @cached_property
    def requirements(self) -> list[Requirement]:
        """Every declared dependency: requirements files, pyproject and Poetry."""
        found: list[Requirement] = []
        for rel in self.select(is_requirements_file):
            for line in (self.read_text(rel) or "").splitlines():
                req = parse_requirement(line, rel)
                if req:
                    found.append(req)

        project_table = self.pyproject.get("project", {})
        if isinstance(project_table, dict):
            specs: list[object] = list(project_table.get("dependencies", []) or [])
            optional = project_table.get("optional-dependencies", {}) or {}
            if isinstance(optional, dict):
                for group in optional.values():
                    specs.extend(group or [])
            for spec in specs:
                if isinstance(spec, str):
                    req = parse_requirement(spec, "pyproject.toml")
                    if req:
                        found.append(req)

        tool = self.pyproject.get("tool", {})
        poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
        poetry_deps = poetry.get("dependencies", {}) if isinstance(poetry, dict) else {}
        for name, value in poetry_deps.items():
            if name.lower() == "python":
                continue
            if isinstance(value, str):
                spec = value
            elif isinstance(value, dict):
                spec = str(value.get("version", "*"))
            else:
                spec = "*"
            found.append(Requirement(name, spec, "pyproject.toml"))
        return found

    @cached_property
    def imports(self) -> dict[str, set[str]]:
        """Top-level modules imported by project code, mapped to the files importing them."""
        result: dict[str, set[str]] = {}
        for rel in self.python_files():
            text = self.read_text(rel)
            if text is None:
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    result.setdefault(module.split(".")[0], set()).add(rel)
        return result

    @cached_property
    def local_modules(self) -> set[str]:
        """Names of the project's own top-level packages and modules."""
        names: set[str] = set()
        for rel in self.python_files():
            parts = PurePosixPath(rel).parts
            if len(parts) == 1:
                names.add(PurePosixPath(rel).stem)
            elif parts[0] == "src" and len(parts) > 2:
                names.add(parts[1])
            else:
                names.add(parts[0])
        return names

    @cached_property
    def _known_names(self) -> set[str]:
        declared = {req.normalized for req in self.requirements}
        imported = {normalize_name(module) for module in self.imports}
        return declared | imported

    def uses(self, *modules: str) -> bool:
        """True if any of ``modules`` is declared as a dependency or imported by the code."""
        return any(normalize_name(module) in self._known_names for module in modules)

    # -- version control and artifact management -----------------------------------------

    @cached_property
    def lfs_patterns(self) -> list[str]:
        patterns: list[str] = []
        for line in (self.read_text(".gitattributes") or "").splitlines():
            parts = line.split()
            if len(parts) > 1 and "filter=lfs" in parts[1:]:
                patterns.append(parts[0])
        return patterns

    def is_lfs_tracked(self, rel: str) -> bool:
        name = PurePosixPath(rel).name
        for pattern in self.lfs_patterns:
            target = rel if "/" in pattern else name
            if fnmatch.fnmatch(target, pattern):
                return True
        return False

    def is_managed(self, rel: str) -> bool:
        """True if the file is stored outside plain Git, via Git LFS or DVC."""
        if self.is_lfs_tracked(rel) or self.exists(rel + ".dvc"):
            return True
        for path in self.paths:
            if path.endswith(".dvc") and rel.startswith(path[: -len(".dvc")] + "/"):
                return True
        dvc_text = (self.read_text("dvc.lock") or "") + (self.read_text("dvc.yaml") or "")
        return rel in dvc_text
