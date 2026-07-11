from app.core.config import get_settings
from app.integrations.contracts import FusionResult, VisionRecognitionResult


def fuse_recognition(
    local: VisionRecognitionResult | None,
    qwen: VisionRecognitionResult | None,
) -> FusionResult:
    settings = get_settings()
    local_candidate = local.candidate if local else None
    qwen_candidate = qwen.candidate if qwen else None
    if local_candidate and qwen_candidate:
        same = (
            local_candidate.medicine_id is not None
            and local_candidate.medicine_id == qwen_candidate.medicine_id
        ) or (
            local_candidate.in_supported_catalog
            and qwen_candidate.in_supported_catalog
            and local_candidate.herb_name == qwen_candidate.herb_name
        )
        baseline = max(local_candidate.confidence, qwen_candidate.confidence)
        if same:
            confidence = min(
                settings.fusion_confidence_cap,
                baseline + settings.fusion_agreement_bonus,
            )
            selected = (
                local_candidate
                if local_candidate.confidence >= qwen_candidate.confidence
                else qwen_candidate
            )
            return FusionResult(
                final_candidate=selected.model_copy(update={"confidence": confidence}),
                local_result=local,
                qwen_result=qwen,
                agreement_status="agree",
                confidence_before_adjustment=baseline,
                confidence_after_adjustment=confidence,
                adjustment=settings.fusion_agreement_bonus,
                decision_reason="Both normalized providers identified the same catalog medicine",
                in_supported_catalog=True,
            )
        confidence = max(
            0, local_candidate.confidence - settings.fusion_conflict_penalty
        )
        return FusionResult(
            final_candidate=local_candidate.model_copy(
                update={"confidence": confidence}
            ),
            local_result=local,
            qwen_result=qwen,
            agreement_status="conflict",
            confidence_before_adjustment=local_candidate.confidence,
            confidence_after_adjustment=confidence,
            adjustment=-settings.fusion_conflict_penalty,
            decision_reason="Providers disagree after database name normalization; local result is retained conservatively",
            manual_review_required=True,
            in_supported_catalog=local_candidate.in_supported_catalog,
        )
    if local_candidate:
        return FusionResult(
            final_candidate=local_candidate,
            local_result=local,
            qwen_result=qwen,
            agreement_status="local_only",
            confidence_before_adjustment=local_candidate.confidence,
            confidence_after_adjustment=local_candidate.confidence,
            decision_reason="Qwen provider unavailable or returned no candidate",
            manual_review_required=local_candidate.confidence
            < settings.fusion_local_accept_threshold,
            in_supported_catalog=local_candidate.in_supported_catalog,
            fallback_used=True,
        )
    if qwen_candidate:
        return FusionResult(
            final_candidate=qwen_candidate,
            local_result=local,
            qwen_result=qwen,
            agreement_status="qwen_only",
            confidence_before_adjustment=qwen_candidate.confidence,
            confidence_after_adjustment=qwen_candidate.confidence,
            decision_reason="Local provider unavailable or returned no candidate",
            manual_review_required=not qwen_candidate.in_supported_catalog,
            in_supported_catalog=qwen_candidate.in_supported_catalog,
            fallback_used=True,
        )
    return FusionResult(
        local_result=local,
        qwen_result=qwen,
        agreement_status="no_result",
        decision_reason="Neither vision provider returned a usable candidate",
        manual_review_required=True,
        fallback_used=True,
    )
