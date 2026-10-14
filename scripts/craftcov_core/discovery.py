"""Finding the files to scan, hashing them, and keeping paths relative to the scan root."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def discover_python_files(root: Path) -> list[str]:
    """Paths, relative to root, of every tracked .py file. Via git when
    possible (git already knows what to ignore — venvs, build artefacts —
    so this avoids reinventing that); falls back to a plain glob outside a
    git repo."""
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", "ls-files", "*.py"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return sorted(line for line in out.splitlines() if line)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*.py"))


def file_hash(root: Path, rel: str) -> str:
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()


def normalize_path(root: Path, raw: str) -> str | None:
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p).resolve()
    try:
        return str(p.relative_to(root))
    except ValueError:
        return None  # outside root somehow — caller skips rather than crashes
