"""Simple heuristic smoke test for the genomic analysis environment."""

from __future__ import annotations

import argparse

try:
    from dna_mutation_env.models import DnaMutationAction
    from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment
    from dna_mutation_env.tasks import TASK_ORDER, get_task
except ModuleNotFoundError:
    from models import DnaMutationAction
    from server.dna_mutation_env_environment import DnaMutationEnvironment
    from tasks import TASK_ORDER, get_task


def run_local_demo(seed: int, task_id: str) -> None:
    """Run a deterministic local demo using the hidden task truth."""
    env = DnaMutationEnvironment()
    observation = env.reset(seed=seed, task_id=task_id)
    truth = get_task(task_id).truth.model_dump()

    print(f"Task: {observation.task_id} ({observation.difficulty})")
    print(observation.task_description)
    print(f"Reference: {observation.reference_sequence}")
    print(f"Observed:  {observation.observed_sequence}")
    print(f"Candidate regions: {[region.model_dump() for region in observation.candidate_regions]}")

    inspect = env.step(
        DnaMutationAction(
            action_type="inspect_region",
            locus=truth["locus"],
            end=truth["end"],
            reasoning="Inspect the highest-value candidate region first.",
        )
    )
    print(f"Inspect reward: {inspect.reward:.4f} -> {inspect.reward_details.explanation}")

    submit = env.step(
        DnaMutationAction(
            action_type="submit_answer",
            locus=truth["locus"],
            end=truth["end"],
            variant_type=truth["variant_type"],
            ref_allele=truth["ref_allele"],
            alt_allele=truth["alt_allele"],
            confidence=0.99,
            reasoning="Submit the variant call from the synthetic truth for validation.",
        )
    )
    print(f"Final reward: {submit.reward:.4f}")
    print(submit.reward_details.model_dump())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test the DNA mutation environment.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--task-id", choices=TASK_ORDER, default=TASK_ORDER[0])
    args = parser.parse_args()
    run_local_demo(seed=args.seed, task_id=args.task_id)
