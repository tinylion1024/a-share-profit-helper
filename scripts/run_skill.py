#!/usr/bin/env python3
"""Compatibility wrapper for the installable CLI."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.main import main


if __name__ == "__main__":
    main()
