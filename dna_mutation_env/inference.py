"""Small smoke test for the DNA mutation environment.

Usage:
    python inference.py
    python inference.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
from typing import Optional

try:
    from dna_mutation_env import DnaMutationAction, DnaMutationEnv
    from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment
except ModuleNotFoundError:
    from client import DnaMutationEnv
    from models import DnaMutationAction
    from server.dna_mutation_env_environment import DnaMutationEnvironment


def run_local_demo(seed: int) -> None:
    """Run the environment directly in-process without a server."""
    env = DnaMutationEnvironment()
    observation = env.reset(seed=seed)

    print("--- Local DNA Mutation Task ---")
    print(f"Target:  {observation.target_sequence}")
    print(f"Current: {observation.current_sequence}")
    print(f"Initial Distance: {observation.distance}")
    print()

    for index in range(3):
        target_base = observation.target_sequence[index]
        observation = env.step(
            DnaMutationAction(
                position=index,
                new_base=target_base,
                reasoning=f"Match the target base at index {index}.",
            )
        )

        print(f"Step {index + 1}: mutated index {index} to {target_base}")
        print(f"Current: {observation.current_sequence}")
        print(f"Reward: {observation.reward:.2f} | Distance: {observation.distance}")
        print("-" * 30)

        if observation.done:
            break

    print("Finished local smoke test.")


def run_remote_demo(base_url: str, seed: int) -> None:
    """Run the smoke test against a live OpenEnv server."""
    client = DnaMutationEnv(base_url=base_url).sync()
    with client:
        result = client.reset(seed=seed)
        observation = result.observation

        print("--- Remote DNA Mutation Task ---")
        print(f"Target:  {observation.target_sequence}")
        print(f"Current: {observation.current_sequence}")
        print(f"Initial Distance: {observation.distance}")
        print()

        for index in range(3):
            target_base = observation.target_sequence[index]
            result = client.step(
                DnaMutationAction(
                    position=index,
                    new_base=target_base,
                    reasoning=f"Match the target base at index {index}.",
                )
            )
            observation = result.observation

            print(f"Step {index + 1}: mutated index {index} to {target_base}")
            print(f"Current: {observation.current_sequence}")
            print(f"Reward: {result.reward:.2f} | Distance: {observation.distance}")
            print("-" * 30)

            if result.done:
                break

    print("Finished remote smoke test.")


def main(base_url: Optional[str], seed: int) -> None:
    """Choose local or remote smoke test mode."""
    if base_url:
        run_remote_demo(base_url=base_url, seed=seed)
        return

    run_local_demo(seed=seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test the DNA mutation environment.")
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Optional OpenEnv server URL, for example http://localhost:8000",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Seed used for reproducible smoke tests.",
    )
    arguments = parser.parse_args()
    main(base_url=arguments.base_url, seed=arguments.seed)
