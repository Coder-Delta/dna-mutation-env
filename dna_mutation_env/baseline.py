"""Baseline evaluator that uses an OpenAI-compatible client from env config."""

from __future__ import annotations

import argparse
import json
import os

from openai import OpenAI

try:
    from dna_mutation_env.models import DnaMutationAction, DnaMutationObservation
    from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment
except ModuleNotFoundError:
    from models import DnaMutationAction, DnaMutationObservation
    from server.dna_mutation_env_environment import DnaMutationEnvironment


SYSTEM_PROMPT = """
You are a genomic analysis agent operating a DNA mutation detection environment.
Return exactly one JSON object with keys:
action_type, locus, end, variant_type, ref_allele, alt_allele, confidence, reasoning.
Prefer inspect_region before a final answer when evidence is ambiguous.
""".strip()

HF_DEFAULT_BASE_URL = "https://router.huggingface.co/v1"


def _extract_json(content: str) -> str:
    """Strip simple Markdown fences from model output."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    return cleaned


def build_client() -> OpenAI:
    """Create an OpenAI-compatible client from hackathon or Hugging Face env vars."""
    try:
        api_key = os.environ["API_KEY"]
    except KeyError:
        api_key = os.getenv("HF_TOKEN")

    if not api_key:
        raise RuntimeError(
            "API_KEY must be set before running baseline.py "
            "(or HF_TOKEN for the Hugging Face fallback)."
        )

    try:
        base_url = os.environ["API_BASE_URL"]
    except KeyError:
        base_url = os.getenv("OPENAI_BASE_URL") or HF_DEFAULT_BASE_URL

    try:
        return OpenAI(api_key=api_key, base_url=base_url)
    except Exception as exc:
        raise RuntimeError("Failed to initialize the OpenAI client from environment variables.") from exc


def choose_action(
    client: OpenAI, model: str, observation: DnaMutationObservation
) -> DnaMutationAction:
    """Ask the model for the next environment action."""
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_id": observation.task_id,
                        "difficulty": observation.difficulty,
                        "task_description": observation.task_description,
                        "reference_sequence": observation.reference_sequence,
                        "observed_sequence": observation.observed_sequence,
                        "coverage": observation.coverage,
                        "quality_scores": observation.quality_scores,
                        "candidate_regions": [
                            region.model_dump() for region in observation.candidate_regions
                        ],
                        "prior_findings": [
                            finding.model_dump() for finding in observation.prior_findings
                        ],
                        "action_budget_remaining": observation.action_budget_remaining,
                    }
                ),
            },
        ],
    )
    content = _extract_json(response.choices[0].message.content or "{}")
    return DnaMutationAction.model_validate_json(content)


def run_episode(model: str, task_id: str, seed: int) -> float:
    """Evaluate one model on one task and return the final score."""
    client = build_client()
    env = DnaMutationEnvironment()
    observation = env.reset(seed=seed, task_id=task_id)

    while not observation.done:
        action = choose_action(client, model=model, observation=observation)
        observation = env.step(action)

    print(
        json.dumps(
            {
                "task_id": observation.task_id,
                "difficulty": observation.difficulty,
                "reward": observation.reward,
                "reward_details": observation.reward_details.model_dump(),
                "findings": [finding.model_dump() for finding in observation.prior_findings],
            },
            indent=2,
        )
    )
    return observation.reward


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DNA mutation baseline evaluator.")
    parser.add_argument("--model", required=True, help="OpenAI-compatible model id.")
    parser.add_argument(
        "--task-id",
        default="easy_snv_short_read",
        help="Task to evaluate: easy_snv_short_read, medium_indel_low_coverage, or hard_repeat_structural_variant.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Seed for reproducible resets.")
    args = parser.parse_args()

    score = run_episode(model=args.model, task_id=args.task_id, seed=args.seed)
    print(f"Final score: {score:.4f}")


if __name__ == "__main__":
    main()
