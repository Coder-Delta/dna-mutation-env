"""Runtime configuration for the DNA mutation environment service."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int, minimum: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    parsed = int(value)
    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {parsed}")
    return parsed


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_log_level(default: str = "INFO") -> str:
    value = os.getenv("DNA_ENV_LOG_LEVEL", default).strip().upper()
    allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    if value not in allowed:
        raise ValueError(
            f"DNA_ENV_LOG_LEVEL must be one of {sorted(allowed)}, got {value}"
        )
    return value


@dataclass(frozen=True)
class RuntimeSettings:
    """Environment-driven runtime settings."""

    sequence_length: int
    max_concurrent_envs: int
    host: str
    port: int
    workers: int
    reveal_target_sequence: bool
    max_steps_per_episode: int
    log_level: str


def load_settings() -> RuntimeSettings:
    """Load validated runtime settings from environment variables."""
    sequence_length = _get_int("DNA_ENV_SEQUENCE_LENGTH", default=10, minimum=2)
    max_steps_default = sequence_length * 2

    return RuntimeSettings(
        sequence_length=sequence_length,
        max_concurrent_envs=_get_int("DNA_ENV_MAX_CONCURRENT_ENVS", default=8, minimum=1),
        host=os.getenv("DNA_ENV_HOST", "0.0.0.0"),
        port=_get_int("DNA_ENV_PORT", default=8000, minimum=1),
        workers=_get_int("DNA_ENV_WORKERS", default=1, minimum=1),
        reveal_target_sequence=_get_bool("DNA_ENV_REVEAL_TARGET", default=True),
        max_steps_per_episode=_get_int(
            "DNA_ENV_MAX_STEPS",
            default=max_steps_default,
            minimum=1,
        ),
        log_level=_get_log_level(),
    )


SETTINGS = load_settings()
