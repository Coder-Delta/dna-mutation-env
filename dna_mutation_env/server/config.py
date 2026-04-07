"""Runtime configuration for the genomic analysis environment service."""

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

    max_concurrent_envs: int
    host: str
    port: int
    workers: int
    default_task_id: str
    max_steps_per_episode: int
    log_level: str


def load_settings() -> RuntimeSettings:
    """Load validated runtime settings from environment variables."""
    return RuntimeSettings(
        max_concurrent_envs=_get_int("DNA_ENV_MAX_CONCURRENT_ENVS", default=8, minimum=1),
        host=os.getenv("DNA_ENV_HOST", "0.0.0.0"),
        port=_get_int("DNA_ENV_PORT", default=8000, minimum=1),
        workers=_get_int("DNA_ENV_WORKERS", default=1, minimum=1),
        default_task_id=os.getenv("DNA_ENV_DEFAULT_TASK", "easy_snv_short_read"),
        max_steps_per_episode=_get_int("DNA_ENV_MAX_STEPS", default=8, minimum=1),
        log_level=_get_log_level(),
    )


SETTINGS = load_settings()
