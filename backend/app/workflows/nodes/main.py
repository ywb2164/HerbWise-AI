import time
from collections.abc import Awaitable, Callable

from app.common.ids import new_id
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
        return {
            "profile": await get_llm_provider().diagnose_profile(current["learner_id"])
        }

    return await execute_node(state, "load_profile", 10, operation)


async def recognize_image(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        return {
            "recognition_result": (
                await get_vision_provider().recognize(current["image_path"])
            ).model_dump()
        }

    return await execute_node(state, "recognize_image", 20, operation)


async def vision_review(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
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
        return {
            "knowledge_evidence": [
                item.model_dump() for item in await get_rag_provider().retrieve(herb)
            ]
        }

    return await execute_node(state, "retrieve_knowledge", 45, operation)


async def judge_result(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
        return {
            "judge_result": {
                "status": "pass",
                "reason": "Mock confidence and knowledge evidence passed",
            }
        }

    return await execute_node(state, "judge_result", 55, operation)


async def generate_resources(state: WorkflowState) -> dict:
    async def operation(current: WorkflowState) -> dict:
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
                    trace_data_json=data,
                )
            )
            await session.commit()
        return {"trace_id": trace_id}

    return await execute_node(state, "save_trace", 100, operation)
