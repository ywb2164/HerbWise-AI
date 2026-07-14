"""Explainable comparison of independent Qwen and YOLO outcomes.

Qwen-VL is the sole source of a final material name.  YOLO is intentionally
kept as a parallel reference and can never replace or re-score that decision.
"""

from app.integrations.contracts import FusionResult, VisionRecognitionResult


def fuse_recognition(
    local: VisionRecognitionResult | None,
    qwen: VisionRecognitionResult | None,
) -> FusionResult:
    qwen_candidate = qwen.candidate if qwen and qwen.recognized else None
    local_candidate = local.candidate if local else None
    if qwen_candidate is None:
        return FusionResult(
            local_result=local,
            qwen_result=qwen,
            agreement_status="qwen_unavailable",
            decision_reason="Primary Qwen-VL recognition is unavailable; YOLO remains reference-only.",
            manual_review_required=True,
            fallback_used=local_candidate is not None,
            status="primary_recognition_unavailable",
        )

    same = bool(
        local_candidate
        and (
            local_candidate.medicine_id is not None
            and local_candidate.medicine_id == qwen_candidate.medicine_id
            or local_candidate.raw_name
            and qwen_candidate.raw_name
            and local_candidate.raw_name.casefold()
            == qwen_candidate.raw_name.casefold()
        )
    )
    if local_candidate is None:
        agreement = "yolo_unavailable"
    elif same:
        agreement = "agree"
    else:
        agreement = "disagree"
    return FusionResult(
        final_candidate=qwen_candidate,
        local_result=local,
        qwen_result=qwen,
        agreement_status=agreement,
        confidence_before_adjustment=qwen_candidate.confidence,
        confidence_after_adjustment=qwen_candidate.confidence,
        adjustment=0,
        decision_reason="Primary single-name result is authoritative; the detector is reference-only.",
        manual_review_required=(
            (qwen is not None and qwen.needs_review) or agreement == "disagree"
        ),
        in_supported_catalog=qwen_candidate.in_supported_catalog,
        rule_version="v1-fixed-qwen-primary",
        status="success",
    )
