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
    env.reset(seed=seed, task_id=task_id)
    truth = get_task(task_id).truth.model_dump()
    task_name = "dna-mutation"
    step_count = 0
    total_score = 0.0

    print(f"[START] task={task_name}", flush=True)

    actions = [
        DnaMutationAction(
            action_type="inspect_region",
            locus=truth["locus"],
            end=truth["end"],
            reasoning="Inspect the highest-value candidate region first.",
        ),
        DnaMutationAction(
            action_type="submit_answer",
            locus=truth["locus"],
            end=truth["end"],
            variant_type=truth["variant_type"],
            ref_allele=truth["ref_allele"],
            alt_allele=truth["alt_allele"],
            confidence=0.99,
            reasoning="Submit the variant call from the synthetic truth for validation.",
        ),
    ]

    for action in actions:
        result = env.step(action)
        step_count += 1
        total_score += result.reward
        print(f"[STEP] step={step_count} reward={result.reward:.4f}", flush=True)

    print(f"[END] task={task_name} score={total_score:.4f} steps={step_count}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test the DNA mutation environment.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--task-id", choices=TASK_ORDER, default=TASK_ORDER[0])
    args = parser.parse_args()
    run_local_demo(seed=args.seed, task_id=args.task_id)
