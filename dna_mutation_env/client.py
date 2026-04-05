# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""DNA mutation environment client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import DnaMutationAction, DnaMutationObservation


class DnaMutationEnv(
    EnvClient[DnaMutationAction, DnaMutationObservation, State]
):
    """Client for interacting with the DNA mutation environment server."""

    def _step_payload(self, action: DnaMutationAction) -> Dict:
        """Convert a mutation action into the server payload."""
        return action.model_dump()

    def _parse_result(self, payload: Dict) -> StepResult[DnaMutationObservation]:
        """Parse a reset or step response into a typed observation result."""
        obs_data = payload.get("observation", {})
        observation_payload = {
            **obs_data,
            "done": payload.get("done", obs_data.get("done", False)),
            "reward": payload.get("reward", obs_data.get("reward")),
        }
        observation = DnaMutationObservation.model_validate(observation_payload)

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
