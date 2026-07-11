import time
from collections.abc import Awaitable, Callable

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.database import async_session_factory
from app.integrations.factory import (
    get_llm_provider,
    get_rag_provider,
    get_vision_provider,
)
from app.modules.traces.models import TraceRecord
from app.workflows.events import record_agent_log, record_event
from app.workflows.state import WorkflowState

Operation = Callable[[WorkflowState], Awaitable[dict]]


async def execute_node(
    state: WorkflowState, name: str, progress: int, operation: Operation
) -> dict:
    await record_event(state["task_id"], name, "running", progress, f"{name} started")
    started = time.perf_counter()
    try:
        result = await operation(state)
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        await record_event(
            state["task_id"],
            name,
            "failed",
            progress,
            f"{name} failed",
            elapsed,
            {"error": str(exc)},
        )
        await record_agent_log(state["task_id"], name, "failed", elapsed, "", str(exc))
        raise
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    await record_event(
        state["task_id"],
        name,
        "success",
        progress,
        f"{name} completed",
        elapsed,
        result,
    )
    await record_agent_log(
        state["task_id"], name, "success", elapsed, "mock node completed"
    )
    return {**result, "current_node": name, "progress": progress}


async def load_profile(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("persistence_enabled"):
            from app.modules.profiles.service import (
                profile_data,
                profile_dimensions,
                require_profile,
            )

            async with async_session_factory() as session:
                try:
                    profile = await require_profile(session, current["learner_id"])
                except Exception:
                    fallback = await get_llm_provider().diagnose_profile(
                        current["learner_id"]
                    )
                    return {"profile": fallback, "fallback_used": True}
                return {
                    "profile": {
                        **profile_data(profile),
                        "dimensions": await profile_dimensions(
                            session, current["learner_id"]
                        ),
                    },
                    "fallback_used": False,
                }
        return {
            "profile": await get_llm_provider().diagnose_profile(current["learner_id"])
        }

    return await execute_node(state, "load_profile", 10, operation)


async def recognize_image(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("file_id"):
            from app.modules.recognition.service import (
                recognize_uploaded_file,
                record_data,
            )

            file_id = current["file_id"]
            if file_id is None:
                raise RuntimeError(
                    "A file identifier is required for persisted recognition"
                )
            async with async_session_factory() as session:
                record = await recognize_uploaded_file(
                    session,
                    learner_id=current["learner_id"],
                    file_id=file_id,
                    task_id=current["task_id"],
                    vision_mode=current.get("vision_mode"),
                )
            item = record_data(record)
            fusion = item["fusion_result"] or {}
            candidate = fusion.get("final_candidate")
            if candidate is None:
                raise RuntimeError("No usable recognition result")
            return {
                "recognition_id": record.recognition_id,
                "recognition_result": {
                    "candidate": candidate,
                    "top_candidates": (
                        item["local_result"] or item["qwen_result"] or {}
                    ).get("top_candidates", [candidate]),
                    "provider": current.get("vision_mode") or "mock",
                    "model_name": None,
                    "elapsed_ms": candidate.get("elapsed_ms", 0),
                },
                "fusion_result": fusion,
                "provider_failures": item["provider_failures"] or [],
            }
        return {
            "recognition_result": (
                await get_vision_provider().recognize(current["image_path"])
            ).model_dump()
        }

    return await execute_node(state, "recognize_image", 20, operation)


async def vision_review(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("fusion_result"):
            fusion = current["fusion_result"]
            return {
                "vision_review_result": {
                    "status": "manual_review"
                    if fusion.get("manual_review_required")
                    else "pass",
                    "confidence": fusion.get("confidence_after_adjustment", 0),
                    "agreement_status": fusion.get("agreement_status"),
                }
            }
        confidence = current["recognition_result"]["candidate"]["confidence"]
        return {
            "vision_review_result": {
                "status": "pass" if confidence >= 0.8 else "reject",
                "confidence": confidence,
            }
        }

    return await execute_node(state, "vision_review", 30, operation)


async def retrieve_knowledge(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        herb = current["recognition_result"]["candidate"]["herb_name"]
        if current.get("persistence_enabled"):
            from app.integrations.contracts import RAGQuery
            from app.modules.knowledge.models import MedicineItem
            from app.modules.knowledge.rag_service import (
                HybridKnowledgeService,
                KnowledgeQueryBuilder,
            )
            from app.modules.knowledge.service import find_medicine_by_name

            async with async_session_factory() as session:
                try:
                    medicine = await find_medicine_by_name(
                        session,
                        current["recognition_result"]["candidate"]["english_name"],
                    )
                    model = await session.get(MedicineItem, medicine["id"])
                    query = KnowledgeQueryBuilder().build(model, "identification")
                    retrieval_id, result = await HybridKnowledgeService().retrieve(
                        session,
                        RAGQuery(
                            query=query,
                            learner_id=current["learner_id"],
                            task_id=current["task_id"],
                            medicine_id=medicine["id"],
                            medicine_name=herb,
                        ),
                    )
                    return {
                        "knowledge_evidence": [
                            item.model_dump(mode="json") for item in result.evidences
                        ],
                        "medicine": medicine,
                        "retrieval_id": retrieval_id,
                        "rag_retrieval": result.model_dump(mode="json"),
                        "fallback_used": False,
                    }
                except Exception:
                    pass
        return {
            "knowledge_evidence": [
                item.model_dump() for item in await get_rag_provider().retrieve(herb)
            ]
        }

    return await execute_node(state, "retrieve_knowledge", 45, operation)


async def judge_result(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("fusion_result"):
            fusion = current["fusion_result"]
            candidate = fusion.get("final_candidate") or {}
            return {
                "judge_result": {
                    "status": "manual_review"
                    if fusion.get("manual_review_required")
                    else "pass",
                    "reason": fusion.get("decision_reason"),
                    "rule_version": fusion.get("rule_version"),
                    "final_medicine_id": candidate.get("medicine_id"),
                    "fusion_rule_version": fusion.get("rule_version"),
                    "manual_review_required": fusion.get(
                        "manual_review_required", False
                    ),
                    "provider_failures": current.get("provider_failures", []),
                    "data_source": "real"
                    if current.get("vision_mode") != "mock"
                    else "mock",
                }
            }
        return {
            "judge_result": {
                "status": "pass",
                "reason": "Mock confidence and knowledge evidence passed",
                "rule_version": "v0.2-mock-rule",
                "evidence_count": len(current["knowledge_evidence"]),
                "fallback_used": bool(current.get("fallback_used", False)),
            }
        }

    return await execute_node(state, "judge_result", 55, operation)


async def generate_resources(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("persistence_enabled"):
            from app.modules.resources.business_schemas import (
                GenerateResourceRequest,
                ResourceType,
            )
            from app.modules.resources.business_service import (
                generate_resource,
                resource_data,
            )

            medicine_name = (
                current.get("medicine", {}).get("standard_name_en")
                or current["recognition_result"]["candidate"]["english_name"]
            )
            async with async_session_factory() as session:
                item = await generate_resource(
                    session,
                    GenerateResourceRequest(
                        learner_id=current["learner_id"],
                        medicine_name=medicine_name,
                        resource_type=ResourceType.lecture,
                        difficulty="basic",
                        task_id=current["task_id"],
                        retrieval_id=str(current["retrieval_id"])
                        if current.get("retrieval_id")
                        else None,
                        evidence_ids=[
                            str(item["evidence_id"])
                            for item in current.get("knowledge_evidence", [])
                            if item.get("evidence_id")
                        ],
                    ),
                )
                return {
                    "resource_ids": [item.resource_id],
                    "generated_resources": [resource_data(item)],
                    "resource_citations": item.citations_json or [],
                }
        from app.integrations.contracts import KnowledgeEvidence

        evidence = [
            KnowledgeEvidence.model_validate(item)
            for item in current["knowledge_evidence"]
        ]
        return {
            "generated_resources": [
                item.model_dump()
                for item in await get_llm_provider().generate_resource(evidence)
            ]
        }

    return await execute_node(state, "generate_resources", 70, operation)


async def review_resources(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("persistence_enabled") and current.get("resource_ids"):
            from app.modules.resources.business_service import (
                review_data,
                review_resource,
            )

            async with async_session_factory() as session:
                persisted_review = await review_resource(
                    session, current["resource_ids"][0]
                )
                result = review_data(persisted_review)
                return {
                    "review_result": result,
                    "review_id": persisted_review.review_id,
                    "retry_count": current["retry_count"]
                    + (1 if persisted_review.status == "reject" else 0),
                }
        from app.integrations.contracts import GeneratedResource

        resources = [
            GeneratedResource.model_validate(item)
            for item in current["generated_resources"]
        ]
        review = await get_llm_provider().review_resource(resources)
        return {
            "review_result": review.model_dump(),
            "retry_count": current["retry_count"]
            + (1 if review.status == "reject" else 0),
        }

    return await execute_node(state, "review_resources", 80, operation)


async def update_learning_path(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        if current.get("persistence_enabled"):
            from app.modules.learning_paths.service import path_data, update_path

            async with async_session_factory() as session:
                return {
                    "path_update": path_data(
                        await update_path(
                            session, current["learner_id"], "workflow_update"
                        )
                    )
                }
        from app.integrations.contracts import ReviewResult

        result = await get_llm_provider().update_learning_path(
            current["learner_id"], ReviewResult.model_validate(current["review_result"])
        )
        return {"path_update": result.model_dump()}

    return await execute_node(state, "update_learning_path", 90, operation)


async def save_trace(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        trace_id = new_id("trace")
        data = {
            key: value for key, value in current.items() if key not in {"image_path"}
        }
        async with async_session_factory() as session:
            session.add(
                TraceRecord(
                    trace_id=trace_id,
                    task_id=current["task_id"],
                    learner_id=current["learner_id"],
                    trace_data_json=json_safe(data),
                )
            )
            await session.commit()
        return {"trace_id": trace_id}

    return await execute_node(state, "save_trace", 100, operation)
