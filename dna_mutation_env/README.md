# DNA Mutation Environment

A production-oriented reinforcement learning environment built with `openenv-core` for sequence optimization tasks. The agent starts with a random DNA sequence and mutates it toward a target sequence, one position at a time.

This project is designed for hackathon demos, RL experimentation, and lightweight bioinformatics workflows where discrete sequence editing is a natural action space.

## Overview

At every episode reset, the environment generates:

- a random `N`-base `target_sequence` (`N` is configurable)
- a random `N`-base `current_sequence`

On each step, the agent submits:

- `position`: zero-based index to mutate
- `new_base`: one of `A`, `T`, `C`, `G`
- `reasoning`: free-text explanation for traceability

The environment then:

- updates the selected base in `current_sequence`
- computes the Hamming distance to the target
- returns a normalized reward based on sequence similarity
- marks the episode complete when the sequences match exactly

## Reward Function

The reward is:

```text
reward = 1.0 - (distance / length)
```

For a sequence length of `10`:

- distance `10` -> reward `0.0`
- distance `5` -> reward `0.5`
- distance `0` -> reward `1.0`

## Environment Contract

### Action

`DnaMutationAction`

- `position: int`
- `new_base: Literal["A", "T", "C", "G"]`
- `reasoning: str`

### Observation

`DnaMutationObservation`

- `current_sequence: str`
- `target_sequence: str`
- `distance: int`
- `reward: float`
- `done: bool`
- `metadata: dict`

## Project Structure

```text
dna_mutation_env/
|-- __init__.py
|-- client.py
|-- models.py
|-- openenv.yaml
|-- pyproject.toml
|-- README.md
|-- tests/
|-- server/
|   |-- __init__.py
|   |-- app.py
|   |-- config.py
|   |-- dna_mutation_env_environment.py
|   `-- Dockerfile
`-- uv.lock
```

## Installation

From the repository root:

```bash
cd dna_mutation_env
uv sync
```

If you are using the workspace virtual environment directly:

```bash
python -m pip install -e .
```

## Run Locally

Start the FastAPI/OpenEnv server:

```bash
cd dna_mutation_env
uv run server
```

Or run Uvicorn directly:

```bash
cd dna_mutation_env
uv run uvicorn dna_mutation_env.server.app:app --host 0.0.0.0 --port 8000 --reload
```

Available endpoints typically include:

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /schema`
- `GET /health`
- `GET /ready`
- `WS /ws`

## Quick Start

### 1. Run the Environment In-Process

This is the fastest way to validate the environment logic during development.

```python
from dna_mutation_env.models import DnaMutationAction
from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment

env = DnaMutationEnvironment()
observation = env.reset(seed=7)

print("Target:", observation.target_sequence)
print("Current:", observation.current_sequence)
print("Distance:", observation.distance)

action = DnaMutationAction(
    position=0,
    new_base=observation.target_sequence[0],
    reasoning="Match the first base to reduce the distance.",
)

observation = env.step(action)
print("Updated:", observation.current_sequence)
print("Reward:", observation.reward)
print("Done:", observation.done)
```

### 2. Connect to a Running Server

```python
from dna_mutation_env import DnaMutationAction, DnaMutationEnv

client = DnaMutationEnv(base_url="http://localhost:8000").sync()

with client:
    result = client.reset(seed=7)
    observation = result.observation

    action = DnaMutationAction(
        position=0,
        new_base=observation.target_sequence[0],
        reasoning="Align the first position with the target.",
    )

    result = client.step(action)
    print(result.observation.current_sequence)
    print(result.reward)
    print(result.done)
```

## Smoke Test

A simple smoke-test script is available at the repository root:

```bash
python inference.py
```

To test against a running server:

```bash
python inference.py --base-url http://localhost:8000
```

## Runtime Configuration

Server behavior is configurable through environment variables:

- `DNA_ENV_SEQUENCE_LENGTH` (default: `10`)
- `DNA_ENV_MAX_STEPS` (default: `2 * sequence_length`)
- `DNA_ENV_MAX_CONCURRENT_ENVS` (default: `8`)
- `DNA_ENV_REVEAL_TARGET` (default: `true`)
- `DNA_ENV_LOG_LEVEL` (default: `INFO`)
- `DNA_ENV_HOST` (default: `0.0.0.0`)
- `DNA_ENV_PORT` (default: `8000`)
- `DNA_ENV_WORKERS` (default: `1`)

Example:

```bash
DNA_ENV_SEQUENCE_LENGTH=20 DNA_ENV_REVEAL_TARGET=false uv run server
```

## Docker Build

Build the environment image from the `dna_mutation_env` directory:

```bash
docker build -t dna-mutation-env:latest -f server/Dockerfile .
```

Run the container:

```bash
docker run --rm -p 8000:8000 dna-mutation-env:latest
```

## Deploy with OpenEnv

The environment includes an `openenv.yaml` manifest and is structured for deployment as an OpenEnv-compatible FastAPI service.

From the `dna_mutation_env` directory:

```bash
openenv push
```

Common options:

```bash
openenv push --private
openenv push --repo-id <namespace>/<repo-name>
```

## Deployment Notes

- Runtime: FastAPI
- App entrypoint: `server.app:app`
- Default port: `8000`
- Manifest: `openenv.yaml`

This makes the project suitable for:

- Hugging Face Spaces
- container-based demos
- internal RL evaluation services
- lightweight remote training environments

## Development Notes

The environment implementation lives in:

- `models.py`
- `server/dna_mutation_env_environment.py`
- `server/app.py`

The packaged client lives in:

- `client.py`

## Quality Gates

Run checks locally:

```bash
cd dna_mutation_env
pip install -e ".[dev]"
ruff check .
pytest
```

GitHub Actions CI runs lint and tests on Python 3.10-3.12 for every push/PR to `main`.

## Security Notes

- Keep secrets in local `.env` only; never commit `.env`.
- Rotate any credential that was accidentally committed in the past.
- For shared/public training settings, consider running with `DNA_ENV_REVEAL_TARGET=false`.

## License

This project inherits the repository licensing and upstream OpenEnv framework licensing where applicable.
