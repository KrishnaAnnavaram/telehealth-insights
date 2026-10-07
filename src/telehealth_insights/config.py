"""Settings from environment variables (and an optional local .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PREFIX = "TELEHEALTH_"


def load_env_file(path: str | os.PathLike = ".env") -> int:
    """Read KEY=VALUE lines into os.environ. Existing variables win. Returns the count of new keys."""
    p = Path(path)
    if not p.is_file():
        return 0
    added = 0
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        value = value.strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            added += 1
    return added


def _get(name: str, default: str = "") -> str:
    value = os.environ.get(PREFIX + name, "")
    return value.strip() if value.strip() else default


@dataclass(frozen=True)
class Settings:
    data_path: str | None
    codebook_path: str | None
    output_dir: str
    seed: int
    alpha: float

    @classmethod
    def from_env(cls) -> "Settings":
        s = cls(
            data_path=_get("DATA") or None,
            codebook_path=_get("CODEBOOK") or None,
            output_dir=_get("OUTPUT", "reports/latest"),
            seed=int(_get("SEED", "42")),
            alpha=float(_get("ALPHA", "0.05")),
        )
        if not 0 < s.alpha < 0.5:
            raise ValueError("TELEHEALTH_ALPHA must be in (0, 0.5)")
        return s
