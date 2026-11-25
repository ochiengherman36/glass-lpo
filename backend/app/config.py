from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "high"
DEFAULT_MAX_TOKENS = 16000
DEFAULT_MAX_UPLOAD_MB = 15

load_dotenv(BACKEND_DIR / ".env")


def env_str(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ExtractionSettings:
    model: str = DEFAULT_MODEL
    effort: str = DEFAULT_EFFORT
    max_tokens: int = DEFAULT_MAX_TOKENS
    use_fallbacks: bool = True

    @classmethod
    def from_env(cls) -> ExtractionSettings:
        return cls(
            model=env_str("ANTHROPIC_MODEL", DEFAULT_MODEL),
            effort=env_str("ANTHROPIC_EFFORT", DEFAULT_EFFORT),
            max_tokens=int(env_str("ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            use_fallbacks=env_bool("ANTHROPIC_USE_FALLBACKS", True),
        )


@dataclass(frozen=True)
class AppSettings:
    output_dir: Path = BACKEND_DIR / "outputs"
    static_dir: Path = BACKEND_DIR / "static"
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_MB * 1024 * 1024

    @classmethod
    def from_env(cls) -> AppSettings:
        return cls(
            output_dir=Path(env_str("OUTPUT_DIR", str(BACKEND_DIR / "outputs"))),
            static_dir=Path(env_str("STATIC_DIR", str(BACKEND_DIR / "static"))),
            max_upload_bytes=int(env_str("MAX_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB))) * 1024 * 1024,
        )
