# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Dna Mutation Env Environment.

This module creates an HTTP server that exposes the DnaMutationEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from .config import SETTINGS
    from ..models import DnaMutationAction, DnaMutationObservation
    from .dna_mutation_env_environment import DnaMutationEnvironment
except (ModuleNotFoundError, ImportError):
    from server.config import SETTINGS
    from models import DnaMutationAction, DnaMutationObservation
    from server.dna_mutation_env_environment import DnaMutationEnvironment

logging.basicConfig(
    level=getattr(logging, SETTINGS.log_level),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)

# Create the app with web interface and README integration
app = create_app(
    DnaMutationEnvironment,
    DnaMutationAction,
    DnaMutationObservation,
    env_name="dna_mutation_env",
    max_concurrent_envs=SETTINGS.max_concurrent_envs,
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Convert environment input errors into clear client-facing responses."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/ready")
async def readiness() -> dict[str, str]:
    """Readiness probe endpoint for orchestrators like Kubernetes."""
    return {"status": "ready"}


def main(host: str = SETTINGS.host, port: int = SETTINGS.port):
    """
    Entry point for direct execution via uv run or python -m.

    This function enables running the server without Docker:
        uv run --project . server
        uv run --project . server --port 8001
        python -m dna_mutation_env.server.app

    Args:
        host: Host address to bind to (default: "0.0.0.0")
        port: Port number to listen on (default: 8000)

    For production deployments, consider using uvicorn directly with
    multiple workers:
        uvicorn dna_mutation_env.server.app:app --workers 4
    """
    import uvicorn

    LOGGER.info(
        "Starting dna_mutation_env host=%s port=%s workers=%s default_task=%s concurrent_envs=%s",
        SETTINGS.host,
        port,
        SETTINGS.workers,
        SETTINGS.default_task_id,
        SETTINGS.max_concurrent_envs,
    )
    uvicorn.run(app, host=host, port=port, workers=SETTINGS.workers)


if __name__ == "__main__":
    main()
