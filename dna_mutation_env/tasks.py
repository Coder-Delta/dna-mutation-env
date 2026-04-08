"""Static genomic analysis tasks with increasing difficulty."""

from __future__ import annotations

try:
    from .models import CandidateRegion, TaskSpec, VariantCall
except ImportError:
    from models import CandidateRegion, TaskSpec, VariantCall


TASKS: dict[str, TaskSpec] = {
    "easy_snv_short_read": TaskSpec(
        task_id="easy_snv_short_read",
        difficulty="easy",
        description=(
            "Identify a single nucleotide variant in a short high-quality read."
        ),
        reference_sequence="ACCTGAGTCACT",
        observed_sequence="ACCTGGGTCACT",
        coverage=[32, 31, 35, 34, 30, 33, 34, 35, 32, 31, 30, 29],
        quality_scores=[37, 38, 39, 36, 37, 39, 38, 37, 36, 35, 36, 34],
        truth=VariantCall(
            locus=5,
            end=5,
            variant_type="snv",
            ref_allele="A",
            alt_allele="G",
            confidence=1.0,
        ),
        candidate_regions=[
            CandidateRegion(start=4, end=6, reason="High-confidence mismatch hotspot.")
        ],
        max_steps=5,
    ),
    "medium_indel_low_coverage": TaskSpec(
        task_id="medium_indel_low_coverage",
        difficulty="medium",
        description=(
            "Detect a low-coverage deletion event in a read with noisier evidence."
        ),
        reference_sequence="TTGACCTTAGGCTA",
        observed_sequence="TTGACTTAGGCTA",
        coverage=[26, 24, 25, 23, 12, 8, 9, 14, 18, 19, 21, 20, 22],
        quality_scores=[35, 34, 35, 33, 27, 19, 18, 24, 29, 30, 31, 30, 32],
        truth=VariantCall(
            locus=5,
            end=5,
            variant_type="deletion",
            ref_allele="C",
            alt_allele="-",
            confidence=1.0,
        ),
        candidate_regions=[
            CandidateRegion(start=4, end=7, reason="Coverage dip suggests a possible indel.")
        ],
        max_steps=6,
    ),
    "hard_repeat_structural_variant": TaskSpec(
        task_id="hard_repeat_structural_variant",
        difficulty="hard",
        description=(
            "Identify a complex mutation in a repetitive region with ambiguous mapping."
        ),
        reference_sequence="CAGCAGCAGTTACGGAATTC",
        observed_sequence="CAGCAGCAGCAGTTACGGACTTC",
        coverage=[
            27,
            28,
            27,
            25,
            23,
            19,
            17,
            16,
            15,
            14,
            12,
            11,
            13,
            15,
            18,
            19,
            21,
            22,
            20,
            18,
            17,
            16,
            15,
        ],
        quality_scores=[
            34,
            34,
            35,
            33,
            31,
            28,
            24,
            22,
            20,
            19,
            18,
            17,
            19,
            22,
            25,
            26,
            27,
            29,
            28,
            26,
            24,
            22,
            21,
        ],
        truth=VariantCall(
            locus=6,
            end=18,
            variant_type="structural_variant",
            ref_allele="CAGTTACGGAA",
            alt_allele="CAGCAGTTACGGA",
            confidence=1.0,
        ),
        candidate_regions=[
            CandidateRegion(start=5, end=13, reason="Repeat expansion signal in CAG tract."),
            CandidateRegion(
                start=14,
                end=18,
                reason="Possible breakpoint shift downstream of the repeat.",
            ),
        ],
        max_steps=8,
    ),
}


TASK_ORDER = [
    "easy_snv_short_read",
    "medium_indel_low_coverage",
    "hard_repeat_structural_variant",
]


def get_task(task_id: str) -> TaskSpec:
    """Return a validated task specification by id."""
    try:
        return TASKS[task_id].model_copy(deep=True)
    except KeyError as exc:
        raise ValueError(f"Unknown task_id={task_id}") from exc
