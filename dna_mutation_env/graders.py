"""Programmatic graders for genomic mutation detection tasks."""

from __future__ import annotations

try:
    from .models import TaskSpec, VariantCall
except ImportError:
    from models import TaskSpec, VariantCall


def _safe_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def _span_overlap(truth: VariantCall, prediction: VariantCall) -> float:
    truth_end = truth.end if truth.end is not None else truth.locus
    pred_end = prediction.end if prediction.end is not None else prediction.locus

    intersection = max(0, min(truth_end, pred_end) - max(truth.locus, prediction.locus) + 1)
    truth_len = truth_end - truth.locus + 1
    pred_len = pred_end - prediction.locus + 1
    union = truth_len + pred_len - intersection
    if union <= 0:
        return 0.0
    return _safe_ratio(intersection / union)


def _allele_score(truth: VariantCall, prediction: VariantCall) -> float:
    ref_match = truth.ref_allele == prediction.ref_allele
    alt_match = truth.alt_allele == prediction.alt_allele
    if ref_match and alt_match:
        return 1.0
    if ref_match or alt_match:
        return 0.5
    return 0.0


def grade_easy_task(task: TaskSpec, prediction: VariantCall) -> float:
    """Strict grading for a simple SNV task."""
    locus_score = 1.0 if prediction.locus == task.truth.locus else 0.0
    type_score = 1.0 if prediction.variant_type == "snv" else 0.0
    allele_score = _allele_score(task.truth, prediction)
    return _safe_ratio((0.5 * locus_score) + (0.25 * type_score) + (0.25 * allele_score))


def grade_medium_task(task: TaskSpec, prediction: VariantCall) -> float:
    """Moderately forgiving grading for lower-coverage indel calls."""
    distance = abs(prediction.locus - task.truth.locus)
    locus_score = 1.0 if distance == 0 else 0.6 if distance == 1 else 0.0
    type_score = 1.0 if prediction.variant_type == task.truth.variant_type else 0.4
    allele_score = _allele_score(task.truth, prediction)
    return _safe_ratio((0.45 * locus_score) + (0.35 * type_score) + (0.20 * allele_score))


def grade_hard_task(task: TaskSpec, prediction: VariantCall) -> float:
    """Overlap-aware grading for structural or repetitive-region events."""
    overlap_score = _span_overlap(task.truth, prediction)
    if prediction.variant_type == task.truth.variant_type:
        type_score = 1.0
    elif prediction.variant_type == "repeat_expansion":
        type_score = 0.8
    else:
        type_score = 0.2

    allele_score = _allele_score(task.truth, prediction)
    return _safe_ratio((0.50 * overlap_score) + (0.35 * type_score) + (0.15 * allele_score))


def grade_prediction(task: TaskSpec, prediction: VariantCall) -> float:
    """Dispatch to the appropriate task-specific grader."""
    if task.difficulty == "easy":
        return grade_easy_task(task, prediction)
    if task.difficulty == "medium":
        return grade_medium_task(task, prediction)
    return grade_hard_task(task, prediction)
