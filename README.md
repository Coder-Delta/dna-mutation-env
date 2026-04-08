---
title: DNA Mutation OpenEnv
emoji: "🧬"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
  - genomics
  - bioinformatics
---

# DNA Mutation OpenEnv

This project is now structured as a Meta OpenEnv-compatible genomic analysis environment. Instead of mutating a string toward a hidden target, the agent acts like a variant analyst: it inspects evidence, flags candidate mutations, categorizes them, and submits a final call.

The layout has been cleaned up to remove duplicate deployment files. The project now uses:

- one Docker build path: `Dockerfile`
- one dependency source: `pyproject.toml`
- one OpenEnv manifest: `openenv.yaml`

## Tasks

- `easy_snv_short_read`: single SNV in a short high-quality sequence
- `medium_indel_low_coverage`: deletion detection with reduced local coverage
- `hard_repeat_structural_variant`: structural/repetitive-region event with ambiguous evidence

Each task is backed by a programmatic grader that returns a score in `[0.0, 1.0]`.

## Core Architecture

- `models.py`: strict Pydantic models for `DnaMutationAction`, `DnaMutationObservation`, `DnaMutationReward`, and `VariantCall`
- `tasks.py`: canonical easy/medium/hard task definitions
- `graders.py`: task-specific scorers for SNVs, indels, and structural variants
- `server/dna_mutation_env_environment.py`: OpenEnv environment with `reset(...)`, `step(action)`, and exported state
- `server/app.py`: FastAPI/OpenEnv server wrapper
- `baseline.py`: baseline evaluator using the OpenAI Python client with `HF_TOKEN`

## Updated File Structure

```text
dna_mutation_env/
|-- __init__.py
|-- baseline.py
|-- client.py
|-- Dockerfile
|-- graders.py
|-- inference.py
|-- models.py
|-- openenv.yaml
|-- pyproject.toml
|-- README.md
|-- tasks.py
|-- tests/
|   |-- test_api.py
|   `-- test_environment.py
`-- server/
    |-- __init__.py
    |-- app.py
    |-- config.py
    `-- dna_mutation_env_environment.py
```

## Observation, Action, Reward

Observation includes:

- `reference_sequence`
- `observed_sequence`
- `coverage`
- `quality_scores`
- `candidate_regions`
- `prior_findings`
- `reward_details`

Actions include:

- `inspect_region`
- `flag_snv`
- `flag_indel`
- `flag_structural_variant`
- `categorize_variant`
- `submit_answer`

Reward logic provides partial credit for useful locus discovery and correct variant typing, and applies penalties for false positives and repeated looping actions.

The public reward contract is bounded to `0.0` through `1.0`. Penalties reduce credit toward zero rather than producing negative scores, which keeps the environment validator- and leaderboard-friendly.

## Run Locally

Install:

```bash
cd dna_mutation_env
pip install -e .
```

Start the environment server:

```bash
python -m server.app
```

Run the local heuristic smoke test:

```bash
python inference.py --task-id easy_snv_short_read
```

Run the OpenAI-compatible baseline:

```bash
set HF_TOKEN=your_token
python baseline.py --model your-model-id --task-id medium_indel_low_coverage
```

If you need a custom OpenAI-compatible endpoint, set `OPENAI_BASE_URL`. By default the baseline uses `https://router.huggingface.co/v1`.

## Baseline Scores

Reference heuristic / expected baseline targets for the included synthetic tasks:

- `easy_snv_short_read`: `1.00` with the exact locus and allele call
- `medium_indel_low_coverage`: `1.00` with the exact deletion call
- `hard_repeat_structural_variant`: `1.00` with the exact structural-variant span and allele call
- `hard_repeat_structural_variant`: approximately `0.63` for a partial overlap / repeat-expansion style call, matching the current grader test fixture

When you run `baseline.py`, record the exact model and date used for your hackathon submission since LLM-based baseline scores can vary by backend model.

## Docker

Build:

```bash
cd dna_mutation_env
docker build -t dna-mutation-openenv .
```

Run:

```bash
docker run --rm -p 8000:8000 dna-mutation-openenv
```

## OpenEnv Metadata

The environment manifest is stored in `openenv.yaml`:

```yaml
spec_version: 1
name: dna_mutation_env
type: space
runtime: fastapi
app: server.app:app
port: 8000
```

## Hugging Face Spaces

This repo is ready for a Docker-based Space.

Deploy directly with OpenEnv:

```bash
cd dna_mutation_env
openenv validate
openenv push . --repo-id username/space-name
```

Notes:

- create the Hugging Face Space with SDK set to `Docker`
- keep the README front matter, `openenv.yaml`, and root `Dockerfile` in the pushed directory
- add `HF_TOKEN` as a Space secret only if you want to run `baseline.py` inside the Space itself

## Test In Hugging Face Space

After deployment, test the live Space through its API endpoints.

Open:

- Space page: `https://huggingface.co/spaces/username/space-name`
- Docs UI: `https://your-space-subdomain.hf.space/docs`
- Health: `https://your-space-subdomain.hf.space/health`
- Ready: `https://your-space-subdomain.hf.space/ready`
- Schema: `https://your-space-subdomain.hf.space/schema`

Recommended test flow:

1. Open `/docs`
2. Call `POST /reset`
3. Call `POST /step` with an inspection action
4. Call `POST /step` again with `submit_answer`
5. Confirm the final response has `done: true`

Example `POST /reset` body:

```json
{
  "seed": 7,
  "task_id": "easy_snv_short_read"
}
```

Example inspection step:

```json
{
  "action_type": "inspect_region",
  "locus": 5,
  "end": 5,
  "reasoning": "Inspect the mismatch hotspot."
}
```

Example final answer:

```json
{
  "action_type": "submit_answer",
  "locus": 5,
  "end": 5,
  "variant_type": "snv",
  "ref_allele": "A",
  "alt_allele": "G",
  "confidence": 0.99,
  "reasoning": "Submit the exact SNV call."
}
```

Expected checks:

- `/health` returns status `200`
- `/ready` returns `{"status":"ready"}`
- `/schema` returns the action and observation schema
- `/reset` returns a task observation
- `submit_answer` ends the episode with `done: true`

## Testing

```bash
cd dna_mutation_env
pytest
```
