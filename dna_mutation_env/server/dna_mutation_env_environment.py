# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""DNA mutation environment implementation."""

import logging
import random
from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import DnaMutationAction, DnaMutationObservation
    from .config import SETTINGS
except ImportError:
    from models import DnaMutationAction, DnaMutationObservation
    from server.config import SETTINGS

LOGGER = logging.getLogger(__name__)

class DnaMutationEnvironment(Environment):
    """Environment where an agent mutates a DNA string toward a target sequence."""

    SEQUENCE_LENGTH: int = SETTINGS.sequence_length
    DNA_BASES: tuple[str, ...] = ("A", "T", "C", "G")

    # Enable concurrent WebSocket sessions.
    # Set to True if your environment isolates state between instances.
    # When True, multiple WebSocket clients can connect simultaneously, each
    # getting their own environment instance (when using factory mode in app.py).
    SUPPORTS_CONCURRENT_SESSIONS: bool = SETTINGS.max_concurrent_envs > 1

    def __init__(self):
        """Initialize environment state."""
        super().__init__()
        self._rng = random.Random()
        self._max_steps = SETTINGS.max_steps_per_episode
        self._reveal_target = SETTINGS.reveal_target_sequence
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_sequence = self._generate_sequence()
        self._target_sequence = self._generate_sequence()
        self._sync_state_fields()

    def _generate_sequence(self) -> str:
        """Generate a random DNA sequence of the configured length."""
        return "".join(self._rng.choice(self.DNA_BASES) for _ in range(self.SEQUENCE_LENGTH))

    def _calculate_distance(self) -> int:
        """Compute the Hamming distance between current and target sequences."""
        return sum(
            current_base != target_base
            for current_base, target_base in zip(
                self._current_sequence, self._target_sequence, strict=True
            )
        )

    def _calculate_reward(self, distance: int) -> float:
        """Compute the normalized reward based on sequence similarity."""
        return 1.0 - (distance / self.SEQUENCE_LENGTH)

    def _sync_state_fields(self) -> None:
        """Mirror the active episode data into the exposed environment state."""
        distance = self._calculate_distance()
        self._state.current_sequence = self._current_sequence
        self._state.target_sequence = self._target_sequence
        self._state.distance = distance
        self._state.sequence_length = self.SEQUENCE_LENGTH

    def _build_observation(self) -> DnaMutationObservation:
        """Create an observation reflecting the current environment state."""
        distance = self._calculate_distance()
        reward = self._calculate_reward(distance)
        done = distance == 0 or self._state.step_count >= self._max_steps

        self._sync_state_fields()
        target_sequence = self._target_sequence if self._reveal_target else ""

        return DnaMutationObservation(
            current_sequence=self._current_sequence,
            target_sequence=target_sequence,
            distance=distance,
            reward=reward,
            done=done,
            metadata={
                "sequence_length": self.SEQUENCE_LENGTH,
                "step_count": self._state.step_count,
                "max_steps": self._max_steps,
                "target_revealed": self._reveal_target,
            },
        )

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DnaMutationObservation:
        """Reset the environment with new random current and target sequences."""
        del kwargs
        self._reset_rubric()
        if seed is not None:
            self._rng.seed(seed)

        self._current_sequence = self._generate_sequence()
        self._target_sequence = self._generate_sequence()
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        return self._build_observation()

    def step(
        self,
        action: DnaMutationAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> DnaMutationObservation:
        """Mutate the selected position and return the updated observation."""
        del timeout_s, kwargs
        if self._state.step_count >= self._max_steps:
            LOGGER.warning("Step called after max steps reached.")
            return self._build_observation()

        if action.position >= self.SEQUENCE_LENGTH:
            raise ValueError(
                f"Position {action.position} is out of range for sequence length {self.SEQUENCE_LENGTH}."
            )

        self._state.step_count += 1
        sequence = list(self._current_sequence)
        sequence[action.position] = action.new_base
        self._current_sequence = "".join(sequence)

        observation = self._build_observation()
        observation.metadata["reasoning"] = action.reasoning
        observation.metadata["mutation"] = {
            "position": action.position,
            "new_base": action.new_base,
        }
        return observation

    @property
    def state(self) -> State:
        """Return the current environment state."""
        return self._state
