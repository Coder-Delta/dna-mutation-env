"""Genomic analysis OpenEnv implementation."""

from __future__ import annotations

import logging
import random
from collections import Counter
from typing import Any, Optional
from uuid import uuid4

from fastmcp import FastMCP
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..graders import grade_prediction
    from ..models import (
        DnaMutationAction,
        DnaMutationObservation,
        DnaMutationReward,
        TaskSpec,
        VariantCall,
    )
    from ..tasks import TASK_ORDER, get_task
    from .config import SETTINGS
except ImportError:
    from graders import grade_prediction
    from models import (
        DnaMutationAction,
        DnaMutationObservation,
        DnaMutationReward,
        TaskSpec,
        VariantCall,
    )
    from tasks import TASK_ORDER, get_task
    from server.config import SETTINGS

LOGGER = logging.getLogger(__name__)


class DnaMutationEnvironment(Environment):
    """Environment that simulates agent-driven genomic mutation detection."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = SETTINGS.max_concurrent_envs > 1

    def __init__(self):
        super().__init__()
        self._rng = random.Random()
        self._task: TaskSpec = get_task(SETTINGS.default_task_id)
        self._max_steps = self._task.max_steps
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._findings: list[VariantCall] = []
        self._action_counter: Counter[str] = Counter()
        self._completed = False
        self._last_reward = self._empty_reward("Environment initialized.")
        self.mcp_server = self._build_mcp_server()
        self._sync_state_fields()

    def _empty_reward(self, explanation: str) -> DnaMutationReward:
        return DnaMutationReward(
            value=0.0,
            locus_accuracy=0.0,
            classification_accuracy=0.0,
            allele_accuracy=0.0,
            false_positive_penalty=0.0,
            loop_penalty=0.0,
            explanation=explanation,
        )

    def _bounded_reward(self, value: float) -> float:
        """Clamp environment rewards into the public 0.0 to 1.0 contract."""
        return max(0.0, min(1.0, round(value, 4)))

    def _select_task(
        self,
        *,
        task_id: str | None = None,
        difficulty: str | None = None,
    ) -> TaskSpec:
        if task_id:
            return get_task(task_id)

        if difficulty:
            for candidate_id in TASK_ORDER:
                candidate = get_task(candidate_id)
                if candidate.difficulty == difficulty:
                    return candidate
            raise ValueError(f"No task found for difficulty={difficulty}")

        return get_task(self._rng.choice(TASK_ORDER))

    def _normalize_action(self, action: DnaMutationAction) -> str:
        return "|".join(
            [
                action.action_type,
                str(action.locus),
                str(action.end),
                str(action.variant_type),
                str(action.ref_allele),
                str(action.alt_allele),
            ]
        )

    def _prediction_from_action(self, action: DnaMutationAction) -> VariantCall:
        action_variant_type = action.variant_type
        if action.action_type == "flag_snv":
            action_variant_type = "snv"
        elif action.action_type == "flag_indel" and action_variant_type not in {"insertion", "deletion"}:
            action_variant_type = "deletion"
        elif action.action_type == "flag_structural_variant":
            action_variant_type = "structural_variant"

        return VariantCall(
            locus=action.locus or 0,
            end=action.end if action.end is not None else action.locus,
            variant_type=action_variant_type or "unknown",
            ref_allele=action.ref_allele or "",
            alt_allele=action.alt_allele or "",
            confidence=action.confidence,
        )

    def _partial_signal(self, prediction: VariantCall) -> tuple[float, float, float]:
        truth = self._task.truth

        if self._task.difficulty == "hard":
            truth_end = truth.end if truth.end is not None else truth.locus
            pred_end = prediction.end if prediction.end is not None else prediction.locus
            overlap = max(0, min(truth_end, pred_end) - max(truth.locus, prediction.locus) + 1)
            truth_len = truth_end - truth.locus + 1
            locus_accuracy = min(1.0, overlap / truth_len) if truth_len else 0.0
        else:
            tolerance = 0 if self._task.difficulty == "easy" else 1
            distance = abs(prediction.locus - truth.locus)
            if distance <= tolerance:
                locus_accuracy = 1.0 if distance == 0 else 0.7
            else:
                locus_accuracy = 0.0

        if prediction.variant_type == truth.variant_type:
            classification_accuracy = 1.0
        elif self._task.difficulty == "hard" and prediction.variant_type == "repeat_expansion":
            classification_accuracy = 0.8
        else:
            classification_accuracy = 0.0

        allele_accuracy = 0.0
        if prediction.ref_allele == truth.ref_allele:
            allele_accuracy += 0.5
        if prediction.alt_allele == truth.alt_allele:
            allele_accuracy += 0.5
        return locus_accuracy, classification_accuracy, allele_accuracy

    def _sync_state_fields(self) -> None:
        self._state.task_id = self._task.task_id
        self._state.difficulty = self._task.difficulty
        self._state.max_steps = self._max_steps
        self._state.reference_length = len(self._task.reference_sequence)
        self._state.observed_length = len(self._task.observed_sequence)
        self._state.findings = [finding.model_dump() for finding in self._findings]
        self._state.completed = self._completed

    def _build_observation(self) -> DnaMutationObservation:
        self._sync_state_fields()
        return DnaMutationObservation(
            task_id=self._task.task_id,
            difficulty=self._task.difficulty,
            task_description=self._task.description,
            reference_sequence=self._task.reference_sequence,
            observed_sequence=self._task.observed_sequence,
            coverage=self._task.coverage,
            quality_scores=self._task.quality_scores,
            candidate_regions=self._task.candidate_regions,
            prior_findings=self._findings,
            action_budget_remaining=max(0, self._max_steps - self._state.step_count),
            reward=self._last_reward.value,
            reward_details=self._last_reward,
            done=self._completed,
            metadata={
                "step_count": self._state.step_count,
                "max_steps": self._max_steps,
                "difficulty": self._task.difficulty,
            },
        )

    def _serialize_observation(self, observation: DnaMutationObservation) -> dict[str, Any]:
        """Return a JSON-serializable observation payload for MCP tools."""
        return observation.model_dump(mode="json")

    def _serialize_step_result(self, observation: DnaMutationObservation) -> dict[str, Any]:
        """Mirror the REST step envelope for MCP tool callers."""
        return {
            "observation": self._serialize_observation(observation),
            "reward": observation.reward,
            "done": observation.done,
        }

    def _build_mcp_server(self) -> FastMCP:
        """Expose a minimal MCP tool surface so LLM clients can discover and call the env."""
        mcp = FastMCP("dna_mutation_env")

        @mcp.tool()
        def reset_episode(
            task_id: str | None = None,
            difficulty: str | None = None,
            seed: int | None = None,
        ) -> dict[str, Any]:
            """Reset the environment and return the first observation."""
            kwargs: dict[str, Any] = {}
            if task_id is not None:
                kwargs["task_id"] = task_id
            if difficulty is not None:
                kwargs["difficulty"] = difficulty
            observation = self.reset(seed=seed, **kwargs)
            return {"observation": self._serialize_observation(observation)}

        @mcp.tool()
        def get_observation() -> dict[str, Any]:
            """Return the latest observation without taking a new action."""
            return {"observation": self._serialize_observation(self._build_observation())}

        @mcp.tool()
        def get_state() -> dict[str, Any]:
            """Return the current internal environment state."""
            return self.state.model_dump(mode="json")

        @mcp.tool()
        def take_action(
            action_type: str,
            locus: int | None = None,
            end: int | None = None,
            variant_type: str | None = None,
            ref_allele: str | None = None,
            alt_allele: str | None = None,
            confidence: float = 0.5,
            reasoning: str = "Inspect the available evidence.",
        ) -> dict[str, Any]:
            """Execute one environment action and return observation, reward, and done."""
            action = DnaMutationAction(
                action_type=action_type,
                locus=locus,
                end=end,
                variant_type=variant_type,
                ref_allele=ref_allele,
                alt_allele=alt_allele,
                confidence=confidence,
                reasoning=reasoning,
            )
            observation = self.step(action)
            return self._serialize_step_result(observation)

        return mcp

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DnaMutationObservation:
        """Reset the environment to a genomic detection task."""
        self._reset_rubric()
        if seed is not None:
            self._rng.seed(seed)

        task_id = kwargs.get("task_id")
        difficulty = kwargs.get("difficulty")
        self._task = self._select_task(task_id=task_id, difficulty=difficulty)
        self._max_steps = min(self._task.max_steps, SETTINGS.max_steps_per_episode)
        self._findings = []
        self._action_counter = Counter()
        self._completed = False
        self._last_reward = self._empty_reward("Episode reset. Inspect the evidence.")
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        return self._build_observation()

    def step(
        self,
        action: DnaMutationAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> DnaMutationObservation:
        """Apply an analysis action and return incremental feedback."""
        del timeout_s, kwargs
        if self._completed:
            return self._build_observation()

        if self._state.step_count >= self._max_steps:
            self._completed = True
            self._last_reward = DnaMutationReward(
                value=0.0,
                locus_accuracy=0.0,
                classification_accuracy=0.0,
                allele_accuracy=0.0,
                false_positive_penalty=0.0,
                loop_penalty=0.4,
                explanation="Analysis budget exhausted before a final answer was submitted.",
            )
            return self._build_observation()

        self._state.step_count += 1
        normalized_action = self._normalize_action(action)
        self._action_counter[normalized_action] += 1
        loop_penalty = 0.15 if self._action_counter[normalized_action] >= 3 else 0.0

        if action.locus is not None and action.locus >= len(self._task.observed_sequence):
            raise ValueError(
                f"locus {action.locus} is out of range for observed sequence length "
                f"{len(self._task.observed_sequence)}"
            )

        reward = self._empty_reward("Action processed.")
        reward.loop_penalty = loop_penalty
        prediction = self._prediction_from_action(action)
        locus_accuracy, classification_accuracy, allele_accuracy = self._partial_signal(
            prediction
        )
        reward.locus_accuracy = locus_accuracy
        reward.classification_accuracy = classification_accuracy
        reward.allele_accuracy = allele_accuracy

        if action.action_type == "inspect_region":
            reward.value = self._bounded_reward((0.12 * locus_accuracy) - loop_penalty)
            reward.explanation = (
                "Inspection moved toward the true locus."
                if locus_accuracy > 0.0
                else "Inspection did not add useful evidence."
            )
        elif action.action_type in {
            "flag_snv",
            "flag_indel",
            "flag_structural_variant",
            "categorize_variant",
        }:
            false_positive_penalty = 0.2 if locus_accuracy == 0.0 and classification_accuracy == 0.0 else 0.0
            reward.false_positive_penalty = false_positive_penalty
            reward.value = self._bounded_reward(
                (0.45 * locus_accuracy)
                + (0.30 * classification_accuracy)
                + (0.15 * allele_accuracy)
                - false_positive_penalty
                - loop_penalty
            )
            reward.explanation = "Variant evidence updated from the submitted call."
            if reward.value > 0:
                self._findings.append(prediction)
        elif action.action_type == "submit_answer":
            final_score = grade_prediction(self._task, prediction)
            false_positive_penalty = 0.1 if final_score < 0.4 else 0.0
            reward.false_positive_penalty = false_positive_penalty
            reward.value = self._bounded_reward(final_score - false_positive_penalty - loop_penalty)
            reward.explanation = "Final answer graded against the hidden ground truth."
            self._findings.append(prediction)
            self._completed = True
        else:
            raise ValueError(f"Unsupported action_type={action.action_type}")

        if self._state.step_count >= self._max_steps and action.action_type != "submit_answer":
            self._completed = True
            reward.loop_penalty = max(reward.loop_penalty, 0.25)
            reward.value = self._bounded_reward(reward.value - 0.25)
            reward.explanation = "Step budget exhausted; analysis terminated."

        self._last_reward = reward
        observation = self._build_observation()
        observation.metadata["last_action"] = action.model_dump()
        return observation

    @property
    def state(self) -> State:
        """Return the current environment state."""
        self._sync_state_fields()
        return self._state
