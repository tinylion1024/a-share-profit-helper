"""Reusable local cache helpers for provider-side persistence."""

from __future__ import annotations

import tempfile
from csv import DictReader, DictWriter
from pathlib import Path


class ProviderCacheStore:
    """Simple file-backed cache store for provider runtime artifacts."""

    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, filename: str) -> Path:
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def load_csv_rows(self, filename: str) -> list[dict[str, str]]:
        path = self.path(filename)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(DictReader(handle))

    def save_csv_rows(self, filename: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path = self.path(filename)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                writer = DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
                temp_path = Path(handle.name)
            temp_path.replace(path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
