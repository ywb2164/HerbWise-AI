from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.core.config import get_settings
from app.core.exceptions import NotFoundException
from app.integrations.contracts import ModelCallContext, VisionRecognitionResult
from app.integrations.factory import (
    get_local_vision_provider,
    get_qwen_vision_provider,
    get_vision_provider,
)
from app.modules.knowledge.models import MedicineAlias, MedicineItem
from app.modules.knowledge.catalog import KnowledgeCatalog
from app.modules.knowledge.normalizer import MedicineNameNormalizer
from app.modules.recognition.fusion import fuse_recognition
from app.modules.recognition.models import ModelCallRecord, RecognitionRecord
from app.modules.resources.models import UploadedFile


async def supported_catalog(session: AsyncSession) -> list[dict[str, object]]:
    medicines = list(
        (
            await session.scalars(
                select(MedicineItem).where(MedicineItem.is_active.is_(True))
            )
        ).all()
    )
    aliases = list((await session.scalars(select(MedicineAlias))).all())
    alias_by_medicine: dict[int, list[str]] = {}
    for alias in aliases:
        alias_by_medicine.setdefault(alias.medicine_id, []).append(alias.alias_name)
    return [
        {
            "medicine_id": item.id,
            "standard_name_zh": item.standard_name_zh,
            "standard_name_en": item.standard_name_en,
            "training_class_name": item.training_class_name,
            "aliases": alias_by_medicine.get(item.id, []),
        }
        for item in medicines
    ]


async def _normalize_result(
    session: AsyncSession, result: VisionRecognitionResult
) -> VisionRecognitionResult:
    normalizer = MedicineNameNormalizer()
    candidates = []
    for candidate in result.top_candidates:
        raw_name = (
            candidate.raw_name
            or candidate.training_class_name
            or candidate.english_name
            or candidate.herb_name
        )
        normalized = await normalizer.normalize(session, raw_name)
        candidates.append(
            candidate.model_copy(
                update={
                    "medicine_id": normalized.medicine_id,
                    "herb_name": normalized.standard_name_zh or candidate.herb_name,
                    "english_name": normalized.standard_name_en
                    or candidate.english_name,
                    "training_class_name": normalized.training_class_name
                    or candidate.training_class_name,
                    "in_supported_catalog": normalized.matched,
                    "matched_by": normalized.matched_by,
                    "raw_name": raw_name,
                }
            )
        )
    if result.candidate is not None and not candidates:
        candidates = [result.candidate]
    return result.model_copy(
        update={
            "top_candidates": candidates,
            "candidate": candidates[0] if candidates else None,
        }
    )


def _catalog_match_data(result: VisionRecognitionResult | None) -> dict[str, object]:
    if result is None or result.candidate is None:
        return {"status": "not_available", "profile": None}
    name_zh = result.candidate.herb_name
    name_en = result.candidate.english_name or result.candidate.raw_name
    match = KnowledgeCatalog.match(name_zh=name_zh, name_en=name_en)
    if match.profile is None:
        return {
            "status": "out_of_catalog",
            "original_name_zh": name_zh,
            "original_name_en": name_en,
            "standard_name_en": name_en,
            "standard_name_zh": name_zh,
            "class_id": None,
            "profile": None,
        }
    return {
        "status": "matched",
        "class_id": match.profile.get("class_id"),
        "training_class_name": match.profile.get("training_class_name"),
        "standard_name_en": match.standard_name_en,
        "standard_name_zh": match.profile.get("standard_name_zh"),
        "aliases": match.profile.get("aliases") or [],
        "review_status": match.profile.get("review_status"),
        "profile": match.profile,
    }


def _profile_material_type(profile: dict[str, object]) -> str | None:
    text = " ".join(
        str(profile.get(key) or "")
        for key in ("botanical_or_zoological_source", "medicinal_part")
    ).casefold()
    for token, material_type in (
        ("animal", "animal"),
        ("insect", "animal"),
        ("fungus", "fungus"),
        ("rhizome", "plant_rhizome"),
        ("root", "plant_root"),
        ("fruit", "plant_fruit"),
        ("seed", "plant_seed"),
        ("bark", "plant_bark"),
        ("flower", "plant_flower"),
    ):
        if token in text:
            return material_type
    return None


def _knowledge_verification(
    qwen: VisionRecognitionResult | None, knowledge_match: dict[str, object]
) -> dict[str, object]:
    profile = knowledge_match.get("profile")
    if not isinstance(profile, dict):
        return {
            "status": "not_available",
            "gross_type_match": None,
            "matched_features": [],
            "conflicting_features": [],
            "reason": "The recognized material is not in the loaded 45-class knowledge package.",
        }
    expected = _profile_material_type(profile)
    actual = qwen.material_type if qwen else "unknown"
    mismatch = bool(
        expected and actual not in {"unknown", "processed_material", expected}
    )
    return {
        "status": "gross_mismatch" if mismatch else "pass",
        "gross_type_match": not mismatch,
        "matched_features": []
        if mismatch
        else list(qwen.visible_evidence if qwen else []),
        "conflicting_features": [
            f"Qwen material_type={actual}; profile type={expected}"
        ]
        if mismatch
        else [],
        "reason": "Basic material type conflicts with the matched knowledge profile."
        if mismatch
        else "No gross material-type conflict detected.",
    }


async def _record_call(
    session: AsyncSession,
    context: ModelCallContext,
    result: VisionRecognitionResult | None,
    *,
    call_type: str,
    error: Exception | None = None,
    elapsed_ms: float,
) -> None:
    session.add(
        ModelCallRecord(
            call_id=new_id("mcall"),
            task_id=context.task_id,
            learner_id=context.learner_id,
            file_id=context.file_id,
            agent_code=context.agent_code,
            prompt_template_code=context.prompt_template_code,
            prompt_version=context.prompt_version,
            provider=result.provider if result else (context.provider or "unknown"),
            model_name=result.model_name if result else context.model_name,
            call_type=call_type,
            success=error is None,
            latency_ms=elapsed_ms,
            error_code=getattr(error, "error_code", "unknown_error") if error else None,
            error_message=str(error)[:512] if error else None,
        )
    )


async def _run_provider(
    session: AsyncSession,
    provider_kind: str,
    image_path: str,
    context: ModelCallContext,
) -> VisionRecognitionResult | Exception:
    started = time.perf_counter()
    if context.task_id:
        from app.workflows.events import record_event

        await record_event(
            context.task_id,
            f"vision.{provider_kind}",
            "running",
            20,
            f"{provider_kind} vision started",
            payload={"provider": provider_kind},
            event_type=f"vision.{provider_kind}.started",
        )
    try:
        if provider_kind == "local":
            result = await get_local_vision_provider().predict_image(
                image_path, context
            )
        elif provider_kind == "qwen":
            result = await get_qwen_vision_provider().recognize(image_path, context)
        else:
            result = await get_vision_provider().recognize(image_path, context)
        # The current primary path uses the model's cleaned Chinese answer as
        # its final name.  Do not normalize, translate, or catalog-map it.
        normalized = (
            result
            if provider_kind == "qwen"
            else await _normalize_result(session, result)
        )
        await _record_call(
            session,
            context,
            normalized,
            call_type=f"vision_{provider_kind}",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        if context.task_id:
            from app.workflows.events import record_event

            await record_event(
                context.task_id,
                f"vision.{provider_kind}",
                "success",
                20,
                f"{provider_kind} vision completed",
                elapsed_ms=normalized.elapsed_ms,
                payload={
                    "provider": normalized.provider,
                    "model_name": normalized.model_name,
                    "confidence": normalized.candidate.confidence
                    if normalized.candidate
                    else None,
                },
                event_type=f"vision.{provider_kind}.completed",
            )
        return normalized
    except Exception as exc:
        await _record_call(
            session,
            context,
            None,
            call_type=f"vision_{provider_kind}",
            error=exc,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        if context.task_id:
            from app.workflows.events import record_event

            await record_event(
                context.task_id,
                f"vision.{provider_kind}",
                "failed",
                20,
                f"{provider_kind} vision failed",
                payload={
                    "provider": provider_kind,
                    "error_code": getattr(exc, "error_code", "unknown_error"),
                },
                event_type=f"vision.{provider_kind}.failed",
            )
        return exc


async def recognize_uploaded_file(
    session: AsyncSession,
    *,
    learner_id: str,
    file_id: str,
    task_id: str | None = None,
    vision_mode: str | None = None,
) -> RecognitionRecord:
    file = await session.scalar(
        select(UploadedFile).where(UploadedFile.file_id == file_id)
    )
    if file is None:
        raise NotFoundException("Uploaded file not found")
    settings = get_settings()
    # The request field remains accepted for legacy clients, but cannot select the
    # primary recognizer.  Real recognition always uses Qwen plus parallel YOLO.
    requested_mode = vision_mode or settings.effective_vision_mode()
    mode = "mock" if requested_mode == "mock" else "fixed_pipeline"
    image_path = str(settings.upload_dir.parent / file.relative_path)
    catalog = await supported_catalog(session)
    local: VisionRecognitionResult | None = None
    qwen: VisionRecognitionResult | None = None
    failures: list[dict[str, str]] = []
    if mode == "fixed_pipeline":
        local_outcome, qwen_outcome = await asyncio.gather(
            _run_provider(
                session,
                "local",
                image_path,
                ModelCallContext(
                    task_id=task_id,
                    learner_id=learner_id,
                    file_id=file_id,
                    supported_catalog=catalog,
                    agent_code="vision_local",
                ),
            ),
            _run_provider(
                session,
                "qwen",
                image_path,
                ModelCallContext(
                    task_id=task_id,
                    learner_id=learner_id,
                    file_id=file_id,
                    agent_code="vision_qwen",
                ),
            ),
            return_exceptions=True,
        )
        if isinstance(local_outcome, BaseException):
            failures.append(
                {
                    "provider": "local",
                    "error_code": getattr(local_outcome, "error_code", "unknown_error"),
                }
            )
        else:
            local = local_outcome
        if isinstance(qwen_outcome, BaseException):
            failures.append(
                {
                    "provider": "qwen",
                    "error_code": getattr(qwen_outcome, "error_code", "unknown_error"),
                }
            )
        else:
            qwen = qwen_outcome
        fusion = fuse_recognition(local, qwen)
        # The knowledge package remains available for other features but is
        # deliberately outside the single-name primary recognition result.
        knowledge_match = {"status": "not_used"}
        knowledge_verification = {"status": "not_used"}
        final = fusion.final_candidate
        fusion = fusion.model_copy(
            update={
                "knowledge_match": knowledge_match,
                "knowledge_verification": knowledge_verification,
                "yolo_reference": local.model_dump(mode="json")
                if local
                else {"status": "failed"},
                "final_identification": {
                    "display_name_zh": final.herb_name if final else None,
                    "medicinal_name_zh": final.herb_name if final else None,
                    "confidence": final.confidence if final else None,
                    "catalog_status": "not_used",
                    "manual_review_required": fusion.manual_review_required,
                },
                "manual_review_required": fusion.manual_review_required,
            }
        )
        if task_id:
            from app.workflows.events import record_event

            fusion_event = (
                "vision.pipeline.disagree"
                if fusion.agreement_status == "disagree"
                else "vision.fusion.completed"
            )
            await record_event(
                task_id,
                "vision.fusion",
                "success",
                20,
                f"fixed vision pipeline {fusion.agreement_status}",
                payload={
                    "confidence": fusion.confidence_after_adjustment,
                    "candidate": fusion.final_candidate.herb_name
                    if fusion.final_candidate
                    else None,
                },
                event_type=fusion_event,
            )
    else:
        kind = "mock" if mode == "mock" else mode
        outcome = await _run_provider(
            session,
            kind,
            image_path,
            ModelCallContext(
                task_id=task_id,
                learner_id=learner_id,
                file_id=file_id,
                supported_catalog=catalog,
                agent_code=f"vision_{kind}",
            ),
        )
        if isinstance(outcome, Exception):
            failures.append(
                {
                    "provider": kind,
                    "error_code": getattr(outcome, "error_code", "unknown_error"),
                }
            )
            fusion = fuse_recognition(None, None)
        else:
            fusion = fuse_recognition(
                outcome if kind == "local" else None,
                outcome if kind in {"qwen", "mock"} else None,
            )
            if kind == "mock":
                fusion = fusion.model_copy(
                    update={
                        "agreement_status": "mock",
                        "decision_reason": "Mock vision result",
                        "manual_review_required": False,
                    }
                )
    final = fusion.final_candidate
    record = RecognitionRecord(
        recognition_id=new_id("recognition"),
        task_id=task_id,
        learner_id=learner_id,
        file_id=file_id,
        vision_mode=mode,
        status="success" if final else fusion.status,
        final_medicine_id=final.medicine_id if final else None,
        final_name=final.herb_name if final else None,
        confidence=final.confidence if final else None,
        agreement_status=fusion.agreement_status,
        manual_review_required=fusion.manual_review_required,
        local_result_json=local.model_dump(mode="json") if local else None,
        qwen_result_json=qwen.model_dump(mode="json") if qwen else None,
        fusion_result_json=fusion.model_dump(mode="json"),
        provider_failures_json=failures or None,
        data_source="mock" if mode == "mock" else "real",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


def record_data(item: RecognitionRecord) -> dict:
    fusion = item.fusion_result_json or {}
    return {
        "recognition_id": item.recognition_id,
        "task_id": item.task_id,
        "learner_id": item.learner_id,
        "file_id": item.file_id,
        "vision_mode": item.vision_mode,
        "status": item.status,
        "recognition_status": "completed" if item.status == "success" else item.status,
        "final_medicine_id": item.final_medicine_id,
        "final_name": item.final_name,
        "confidence": item.confidence,
        "agreement_status": item.agreement_status,
        "manual_review_required": item.manual_review_required,
        "local_result": item.local_result_json,
        "qwen_result": item.qwen_result_json,
        "fusion_result": fusion,
        "final_identification": fusion.get("final_identification"),
        "yolo_reference": fusion.get("yolo_reference"),
        "knowledge_match": fusion.get("knowledge_match"),
        "knowledge_verification": fusion.get("knowledge_verification"),
        "provider_failures": item.provider_failures_json,
        "data_source": item.data_source,
        "created_at": item.created_at,
    }


def single_name_response_data(item: RecognitionRecord) -> dict:
    """Student recognition response: expose only the final name and detector aid."""

    fusion = item.fusion_result_json or {}
    return {
        "recognition_id": item.recognition_id,
        "status": "success" if item.status == "success" else item.status,
        "recognition_status": "completed" if item.status == "success" else item.status,
        "final_name": item.final_name,
        "confidence": item.confidence,
        "final_identification": fusion.get("final_identification"),
        "yolo_reference": fusion.get("yolo_reference"),
        "created_at": item.created_at,
    }


async def require_record(
    session: AsyncSession, recognition_id: str
) -> RecognitionRecord:
    item = await session.scalar(
        select(RecognitionRecord).where(
            RecognitionRecord.recognition_id == recognition_id
        )
    )
    if item is None:
        raise NotFoundException("Recognition record not found")
    return item


async def list_records(
    session: AsyncSession,
    learner_id: str | None,
    task_id: str | None,
    page: int,
    page_size: int,
) -> dict:
    stmt = select(RecognitionRecord)
    if learner_id:
        stmt = stmt.where(RecognitionRecord.learner_id == learner_id)
    if task_id:
        stmt = stmt.where(RecognitionRecord.task_id == task_id)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    records = list(
        (
            await session.scalars(
                stmt.order_by(RecognitionRecord.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return {
        "items": [record_data(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }
