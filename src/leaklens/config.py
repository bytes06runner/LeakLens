"""Load YAML configs shipped with the package (configs/ in the source tree, leaklens/_configs/ in a wheel)."""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

_SOURCE_DIR = Path(__file__).resolve().parents[2] / "configs"
_WHEEL_DIR = Path(__file__).resolve().parent / "_configs"


@cache
def load_config(name: str) -> dict[str, Any]:
    for base in (_WHEEL_DIR, _SOURCE_DIR):
        path = base / f"{name}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text())
    raise FileNotFoundError(f"config {name!r} not found in {_WHEEL_DIR} or {_SOURCE_DIR}")
