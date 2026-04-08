from dna_mutation_env.graders import grade_easy_task, grade_hard_task, grade_medium_task
from dna_mutation_env.models import DnaMutationAction, VariantCall
from dna_mutation_env.server.dna_mutation_env_environment import DnaMutationEnvironment
from dna_mutation_env.tasks import get_task


def test_reset_supports_task_selection() -> None:
    env = DnaMutationEnvironment()
    obs = env.reset(seed=123, task_id="easy_snv_short_read")

    assert obs.task_id == "easy_snv_short_read"
    assert obs.difficulty == "easy"
    assert len(obs.quality_scores) == len(obs.observed_sequence)
    assert "truth_variant_type" not in obs.metadata
    assert not hasattr(env.state, "truth")


def test_incremental_reward_for_correct_inspection_and_submission() -> None:
    env = DnaMutationEnvironment()
    env.reset(seed=7, task_id="easy_snv_short_read")

    inspect_obs = env.step(
        DnaMutationAction(
            action_type="inspect_region",
            locus=5,
            end=5,
            reasoning="Inspect the mismatch hotspot.",
        )
    )
    assert inspect_obs.reward > 0.0

    final_obs = env.step(
        DnaMutationAction(
            action_type="submit_answer",
            locus=5,
            end=5,
            variant_type="snv",
            ref_allele="A",
            alt_allele="G",
            confidence=0.99,
            reasoning="Submit the exact SNV call.",
        )
    )

    assert final_obs.done is True
    assert final_obs.reward >= 0.9
    assert final_obs.reward_details.classification_accuracy == 1.0


def test_false_positive_and_loop_penalties_apply() -> None:
    env = DnaMutationEnvironment()
    env.reset(seed=9, task_id="medium_indel_low_coverage")

    obs = None
    for _ in range(3):
        obs = env.step(
            DnaMutationAction(
                action_type="flag_snv",
                locus=0,
                variant_type="snv",
                ref_allele="T",
                alt_allele="C",
                confidence=0.2,
                reasoning="This is intentionally incorrect.",
            )
        )

    assert obs is not None
    assert 0.0 <= obs.reward <= 1.0
    assert obs.reward == 0.0
    assert obs.reward_details.false_positive_penalty > 0.0
    assert obs.reward_details.loop_penalty > 0.0


def test_task_graders_return_full_credit_for_truth() -> None:
    easy = get_task("easy_snv_short_read")
    medium = get_task("medium_indel_low_coverage")
    hard = get_task("hard_repeat_structural_variant")

    assert grade_easy_task(easy, easy.truth) == 1.0
    assert grade_medium_task(medium, medium.truth) == 1.0
    assert grade_hard_task(hard, hard.truth) == 1.0


def test_hard_grader_is_overlap_aware() -> None:
    hard = get_task("hard_repeat_structural_variant")
    partial_prediction = VariantCall(
        locus=7,
        end=17,
        variant_type="repeat_expansion",
        ref_allele=hard.truth.ref_allele,
        alt_allele="",
        confidence=0.6,
    )

    score = grade_hard_task(hard, partial_prediction)
    assert 0.4 < score < 1.0


def test_reward_outputs_stay_bounded() -> None:
    env = DnaMutationEnvironment()
    env.reset(seed=7, task_id="easy_snv_short_read")

    obs = env.step(
        DnaMutationAction(
            action_type="flag_snv",
            locus=0,
            variant_type="snv",
            ref_allele="A",
            alt_allele="T",
            confidence=0.1,
            reasoning="Incorrect call to test lower bound.",
        )
    )

    assert 0.0 <= obs.reward <= 1.0
    assert 0.0 <= obs.reward_details.value <= 1.0
