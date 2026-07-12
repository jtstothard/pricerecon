"""Canonical deterministic quality gate for PriceRecon."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tomllib import loads as toml_loads

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
PYTHON_ROOTS = (REPO_ROOT / "src" / "pricerecon", REPO_ROOT / "tests")
FRONTEND_PATHS = (FRONTEND_ROOT / "src",)
IGNORED_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".coverage"}


@dataclass(frozen=True, slots=True)
class QualityCheck:
    name: str
    command: list[str]
    cwd: Path = REPO_ROOT


def _run(command: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    completed = _run(["git", *args], cwd=cwd)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _print_header(text: str) -> None:
    print(f"\n==> {text}", flush=True)


def _run_command(check: QualityCheck) -> None:
    _print_header(check.name)
    print(f"$ {' '.join(check.command)}", flush=True)
    completed = subprocess.run(check.command, cwd=check.cwd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _load_yaml(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        yaml.safe_load(handle)


def validate_repository_configuration(repo_root: Path = REPO_ROOT) -> None:
    """Fail fast on malformed repo configuration files and templates."""

    yaml_files = [
        repo_root / "config.yml",
        repo_root / "docker-compose.yml",
        repo_root / ".github" / "workflows" / "ci.yml",
    ]
    template_dir = repo_root / "src" / "pricerecon" / "connectors" / "templates"
    yaml_files.extend(sorted(template_dir.glob("*.yml")))

    for path in yaml_files:
        if path.exists():
            _load_yaml(path)

    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        toml_loads(pyproject.read_text(encoding="utf-8"))

    package_json = repo_root / "frontend" / "package.json"
    if package_json.exists():
        json.loads(package_json.read_text(encoding="utf-8"))


def _candidate_base_refs() -> list[str]:
    base_refs: list[str] = []
    github_base_ref = os.environ.get("GITHUB_BASE_REF")
    if github_base_ref:
        base_refs.append(f"origin/{github_base_ref}")
    base_refs.extend(["origin/main", "main", "origin/master", "master"])
    seen: set[str] = set()
    ordered: list[str] = []
    for ref in base_refs:
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    return ordered


def _changed_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    status = _git("status", "--porcelain", cwd=repo_root)
    if status:
        diff = _git("diff", "--name-only", "HEAD", cwd=repo_root)
        staged = _git("diff", "--name-only", "--cached", cwd=repo_root)
        untracked = _git("ls-files", "--others", "--exclude-standard", cwd=repo_root)
        names = [
            name for name in (diff + "\n" + staged + "\n" + untracked).splitlines() if name.strip()
        ]
        return [repo_root / name for name in dict.fromkeys(names)]

    for ref in _candidate_base_refs():
        if not _git("rev-parse", "--verify", ref, cwd=repo_root):
            continue
        merge_base = _git("merge-base", "HEAD", ref, cwd=repo_root)
        if not merge_base:
            continue
        diff = _git(
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            f"{merge_base}...HEAD",
            cwd=repo_root,
        )
        names = [name for name in diff.splitlines() if name.strip()]
        if names:
            return [repo_root / name for name in dict.fromkeys(names)]

    return []


def _is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_PATH_PARTS for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def _python_paths_for_tools(paths: list[Path]) -> list[Path]:
    return [
        path
        for path in paths
        if not _is_ignored_path(path)
        and path.suffix == ".py"
        and any(root in path.parents or path == root for root in PYTHON_ROOTS)
    ]


def _frontend_paths_for_tools(paths: list[Path]) -> list[Path]:
    return [
        path
        for path in paths
        if not _is_ignored_path(path)
        and path.suffix in {".ts", ".tsx", ".js", ".jsx", ".json"}
        and any(root in path.parents or path == root for root in FRONTEND_PATHS)
    ]


def _format_paths(paths: list[Path], *, cwd: Path = REPO_ROOT) -> list[str]:
    return [str(path.relative_to(cwd)) for path in paths]


def build_quality_checks(repo_root: Path = REPO_ROOT) -> list[QualityCheck]:
    changed_files = _changed_files(repo_root)
    changed_python = _python_paths_for_tools(changed_files)
    changed_frontend = _frontend_paths_for_tools(changed_files)

    python_targets = (
        _format_paths(changed_python, cwd=repo_root)
        if changed_python
        else ["src/pricerecon", "tests"]
    )
    frontend_build_needed = bool(changed_frontend) or not changed_files

    checks = [
        QualityCheck(
            "Validate configuration and templates",
            [
                sys.executable,
                "-c",
                "from pricerecon.quality_gate import validate_repository_configuration; validate_repository_configuration()",
            ],
            cwd=repo_root,
        ),
        QualityCheck(
            "Black check",
            [sys.executable, "-m", "black", "--check", *python_targets],
            cwd=repo_root,
        ),
        QualityCheck(
            "Ruff check", [sys.executable, "-m", "ruff", "check", *python_targets], cwd=repo_root
        ),
        QualityCheck("Mypy check", [sys.executable, "-m", "mypy", *python_targets], cwd=repo_root),
        QualityCheck("Pytest", [sys.executable, "-m", "pytest"], cwd=repo_root),
    ]

    if frontend_build_needed:
        checks.append(QualityCheck("Frontend build", ["npm", "run", "build"], cwd=FRONTEND_ROOT))
    return checks


def main(argv: list[str] | None = None) -> None:
    """Run the canonical deterministic PriceRecon quality gate."""

    _ = argv  # Reserved for future subcommands; keeps the entry point stable.
    validate_repository_configuration()
    for check in build_quality_checks():
        _run_command(check)
    print("\nQuality gate passed.", flush=True)


if __name__ == "__main__":
    main()
