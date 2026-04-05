from dna_mutation_env.models import DnaMutationAction
from dna_mutation_env.server.config import SETTINGS
from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment


def test_reset_is_seeded_and_reproducible() -> None:
    env_a = DnaMutationEnvironment()
    env_b = DnaMutationEnvironment()

    obs_a = env_a.reset(seed=123)
    obs_b = env_b.reset(seed=123)

    assert obs_a.current_sequence == obs_b.current_sequence
    assert obs_a.target_sequence == obs_b.target_sequence
    assert obs_a.distance == obs_b.distance


def test_step_updates_sequence_and_metadata() -> None:
    env = DnaMutationEnvironment()
    obs = env.reset(seed=11)

    next_obs = env.step(
        DnaMutationAction(
            position=0,
            new_base=obs.target_sequence[0] if obs.target_sequence else "A",
            reasoning="Align first base.",
        )
    )

    assert len(next_obs.current_sequence) == SETTINGS.sequence_length
    assert next_obs.metadata["step_count"] == 1
    assert "mutation" in next_obs.metadata


def test_step_rejects_invalid_position() -> None:
    env = DnaMutationEnvironment()
    env.reset(seed=7)

    try:
        env.step(
            DnaMutationAction(
                position=SETTINGS.sequence_length + 1,
                new_base="A",
                reasoning="Should fail",
            )
        )
    except ValueError as exc:
        assert "out of range" in str(exc)
        return

    raise AssertionError("Expected ValueError for invalid mutation position")

