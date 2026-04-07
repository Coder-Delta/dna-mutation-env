"""Typed data models for the genomic analysis OpenEnv environment."""

from __future__ import annotations

from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field, model_validator


Difficulty = Literal["easy", "medium", "hard"]
ActionType = Literal[
    "inspect_region",
    "flag_snv",
    "flag_indel",
    "flag_structural_variant",
    "categorize_variant",
    "submit_answer",
]
VariantType = Literal[
    "snv",
    "insertion",
    "deletion",
    "structural_variant",
    "repeat_expansion",
    "unknown",
]


class VariantCall(BaseModel):
    """Structured description of a detected mutation."""

    locus: int = Field(..., ge=0, description="Zero-based start coordinate.")
    end: int | None = Field(
        default=None,
        ge=0,
        description="Inclusive end coordinate for multi-base events.",
    )
    variant_type: VariantType = Field(..., description="Predicted mutation class.")
    ref_allele: str = Field(
        default="",
        description="Reference allele or sequence at the called locus.",
    )
    alt_allele: str = Field(
        default="",
        description="Observed alternate allele or sequence at the called locus.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence assigned to the call.",
    )

    @model_validator(mode="after")
    def validate_interval(self) -> "VariantCall":
        if self.end is not None and self.end < self.locus:
            raise ValueError("end must be greater than or equal to locus")
        return self


class CandidateRegion(BaseModel):
    """Region surfaced to the agent as potentially interesting."""

    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    reason: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_region(self) -> "CandidateRegion":
        if self.end < self.start:
            raise ValueError("candidate region end must be >= start")
        return self


class DnaMutationReward(BaseModel):
    """Detailed reward breakdown for incremental feedback."""

    value: float = Field(..., ge=0.0, le=1.0)
    locus_accuracy: float = Field(..., ge=0.0, le=1.0)
    classification_accuracy: float = Field(..., ge=0.0, le=1.0)
    allele_accuracy: float = Field(..., ge=0.0, le=1.0)
    false_positive_penalty: float = Field(..., ge=0.0, le=1.0)
    loop_penalty: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., min_length=1)


class DnaMutationAction(Action):
    """Agent action used to inspect and classify genomic variation."""

    action_type: ActionType = Field(..., description="Analysis action to perform.")
    locus: int | None = Field(
        default=None,
        ge=0,
        description="Primary genomic coordinate used by the action.",
    )
    end: int | None = Field(
        default=None,
        ge=0,
        description="Optional end coordinate for region-based actions.",
    )
    variant_type: VariantType | None = Field(
        default=None,
        description="Optional variant classification supplied by the agent.",
    )
    ref_allele: str | None = Field(
        default=None,
        description="Reference allele hypothesis for the selected locus.",
    )
    alt_allele: str | None = Field(
        default=None,
        description="Alternate allele hypothesis for the selected locus.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence attached to the current step.",
    )
    reasoning: str = Field(
        ...,
        min_length=3,
        description="Short explanation for the analysis action.",
    )

    @model_validator(mode="after")
    def validate_shape(self) -> "DnaMutationAction":
        if self.end is not None and self.locus is not None and self.end < self.locus:
            raise ValueError("end must be >= locus")

        needs_locus = {
            "inspect_region",
            "flag_snv",
            "flag_indel",
            "flag_structural_variant",
            "categorize_variant",
            "submit_answer",
        }
        if self.action_type in needs_locus and self.locus is None:
            raise ValueError(f"locus is required for action_type={self.action_type}")
        return self


class DnaMutationObservation(Observation):
    """Observation returned by the genomic analysis environment."""

    task_id: str = Field(..., min_length=1)
    difficulty: Difficulty = Field(...)
    task_description: str = Field(..., min_length=1)
    reference_sequence: str = Field(..., min_length=1)
    observed_sequence: str = Field(..., min_length=1)
    coverage: list[int] = Field(..., min_length=1)
    quality_scores: list[int] = Field(..., min_length=1)
    candidate_regions: list[CandidateRegion] = Field(default_factory=list)
    prior_findings: list[VariantCall] = Field(default_factory=list)
    action_budget_remaining: int = Field(..., ge=0)
    reward: float = Field(..., ge=0.0, le=1.0)
    reward_details: DnaMutationReward = Field(...)


class TaskSpec(BaseModel):
    """Canonical task definition used by the environment and graders."""

    task_id: str = Field(..., min_length=1)
    difficulty: Difficulty = Field(...)
    description: str = Field(..., min_length=1)
    reference_sequence: str = Field(..., min_length=1)
    observed_sequence: str = Field(..., min_length=1)
    coverage: list[int] = Field(..., min_length=1)
    quality_scores: list[int] = Field(..., min_length=1)
    truth: VariantCall = Field(...)
    candidate_regions: list[CandidateRegion] = Field(default_factory=list)
    max_steps: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_vectors(self) -> "TaskSpec":
        observed_length = len(self.observed_sequence)
        if len(self.coverage) != observed_length:
            raise ValueError("coverage length must match observed_sequence length")
        if len(self.quality_scores) != observed_length:
            raise ValueError("quality_scores length must match observed_sequence length")
        return self
