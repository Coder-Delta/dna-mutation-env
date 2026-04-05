# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Data models for the DNA mutation environment."""

from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class DnaMutationAction(Action):
    """Mutation action applied to a single position in the DNA sequence."""

    position: int = Field(
        ...,
        ge=0,
        description="Zero-based index in the DNA sequence to mutate.",
    )
    new_base: Literal["A", "T", "C", "G"] = Field(
        ...,
        description="Replacement nucleotide for the selected position.",
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        description="Short explanation describing why this mutation was chosen.",
    )


class DnaMutationObservation(Observation):
    """Observation returned after each environment reset or mutation step."""

    current_sequence: str = Field(
        ...,
        min_length=1,
        description="The agent's current DNA sequence after the latest mutation.",
    )
    target_sequence: str = Field(
        ...,
        min_length=0,
        description="The hidden target DNA sequence the agent is trying to match.",
    )
    distance: int = Field(
        ...,
        ge=0,
        description="Hamming distance between the current and target sequences.",
    )
    reward: float = Field(
        ...,
        description="Reward computed from the normalized sequence similarity.",
    )
