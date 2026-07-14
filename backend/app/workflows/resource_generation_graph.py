"""Independent, bounded LangGraph workflow for personalised learning resources."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.integrations.contracts import RAGQuery
from app.modules.knowledge.rag_service import (
    HybridKnowledgeService,
    KnowledgeQueryBuilder,
)
from app.modules.learning_paths.models import LearningPlanItem, LearningTask
from app.modules.resources.agent_service import (
    PROMPT_VERSION,
    SEVERE_REVIEW_ISSUES,
    _can_use_text_model,
    _fallback_resource,
    _generate_with_text_model,
    _load_context,
    _load_structured_knowledge,
    _model_review,
    _persist_resource,
    deterministic_review,
)
from app.modules.resources.agent_schemas import (
    GeneratedResourcePayload,
    ModelResourceReview,
)
from app.modules.resources.business_models import ResourceGenerationJob, ResourceOutput
from app.modules.resources.rag_decision import RagDecisionService
from app.modules.traces.models import TraceRecord


class ResourceState(TypedDict, total=False):
    session: AsyncSession
    job: ResourceGenerationJob
    requires_citation: bool
    context: dict[str, Any]
    knowledge: dict[str, Any]
    requires_rag: bool
    rag_reason_codes: list[str]
    query_plan: list[str]
    evidence: list[dict[str, Any]]
    output: GeneratedResourcePayload
    deterministic_issues: list[str]
    model_review: ModelResourceReview
    resource: ResourceOutput
    rewrite_count: int
    fallback_used: bool
    fallback_reason: str | None
    terminal_status: str | None
    trace_nodes: list[dict[str, Any]]


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"keys": sorted(value)[:12]}
    if isinstance(value, list):
        return {"count": len(value)}
    return {"type": type(value).__name__}


async def _node(
    state: ResourceState, code: str, operation, node_type: str = "deterministic"
):
    started = time.perf_counter()
    output: Any = {}
    status = "success"
    error_code = None
    try:
        output = await operation()
        return output
    except Exception as exc:
        status = "failed"
        error_code = getattr(exc, "error_code", type(exc).__name__)
        raise
    finally:
        state.setdefault("trace_nodes", []).append(
            {
                "node_code": code,
                "node_type": node_type,
                "status": status,
                "input_summary": _summary(state.get("context", {})),
                "output_summary": _summary(output),
                "provider": "text" if node_type == "llm" else None,
                "model_name": None,
                "prompt_version": PROMPT_VERSION,
                "evidence_count": len(state.get("evidence", [])),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "retry_count": state.get("rewrite_count", 0),
                "data_source": "deterministic_fallback"
                if state.get("fallback_used")
                else "database",
                "fallback_reason": state.get("fallback_reason"),
                "error_code": error_code,
            }
        )


async def _set_job_status(job: ResourceGenerationJob, status: str) -> None:
    job.status = status


async def load_resource_context(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    await _set_job_status(job, "loading_context")
    context = await _node(
        state,
        "load_resource_context",
        lambda: _load_context(state["session"], job, state["requires_citation"]),
    )
    return {"context": context}


async def load_structured_knowledge(state: ResourceState) -> dict[str, Any]:
    knowledge = await _node(
        state,
        "load_structured_knowledge",
        lambda: _load_structured_knowledge(state["session"], state["context"]),
    )
    context = {**state["context"], "knowledge": knowledge}
    return {"knowledge": knowledge, "context": context}


async def decide_rag(state: ResourceState) -> dict[str, Any]:
    decision = await _node(
        state,
        "decide_rag",
        lambda: _decide(state),
    )
    state["job"].requires_rag = decision.requires_rag
    state["job"].rag_reason_json = decision.reason_codes
    return {
        "requires_rag": decision.requires_rag,
        "rag_reason_codes": decision.reason_codes,
        "query_plan": decision.query_plan,
    }


async def _decide(state: ResourceState):
    request = state["context"]["resource_request"]
    return RagDecisionService().decide(
        resource_type=request["resource_type"],
        requires_citation=state["requires_citation"],
        knowledge_points=state["context"]["targets"]["knowledge_points"],
        additional_instruction=request.get("additional_instruction"),
    )


async def retrieve_evidence(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    if not state.get("requires_rag"):
        return {"evidence": []}
    await _set_job_status(job, "retrieving")

    async def operation() -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        for text in state.get("query_plan", []) or [job.resource_type]:
            query = KnowledgeQueryBuilder().build(None, job.resource_type, text)
            retrieval_id, result = await HybridKnowledgeService().retrieve(
                state["session"],
                RAGQuery(
                    query=query,
                    learner_id=job.learner_id,
                    task_id=job.task_id,
                    task_type=job.resource_type,
                    top_k=8,
                ),
            )
            job.retrieval_id = retrieval_id
            collected.extend(item.model_dump(mode="json") for item in result.evidences)
            if len(collected) >= 6:
                break
        unique: dict[str, dict[str, Any]] = {}
        for item in collected:
            unique.setdefault(str(item["evidence_id"]), item)
        return list(unique.values())[:6]

    try:
        evidence = await _node(state, "retrieve_evidence", operation)
    except Exception as exc:
        if state["requires_citation"]:
            return {
                "evidence": [],
                "terminal_status": "degraded",
                "fallback_reason": getattr(exc, "error_code", "rag_unavailable"),
            }
        return {
            "evidence": [],
            "fallback_used": True,
            "fallback_reason": "rag_unavailable",
        }
    if state["requires_citation"] and not evidence:
        return {
            "evidence": [],
            "terminal_status": "degraded",
            "fallback_reason": "citation_evidence_unavailable",
        }
    return {"evidence": evidence}


async def validate_evidence(state: ResourceState) -> dict[str, Any]:
    async def operation() -> list[str]:
        evidence = state.get("evidence", [])
        ids = [item.get("evidence_id") for item in evidence]
        issues = []
        if len(ids) != len(set(ids)):
            issues.append("duplicate_evidence")
        if any(not item.get("citation") for item in evidence):
            issues.append("invalid_evidence")
        return issues

    issues = await _node(state, "validate_evidence", operation)
    if issues and state["requires_citation"]:
        return {"terminal_status": "rejected", "deterministic_issues": issues}
    return {"deterministic_issues": issues}


def _continue_after_evidence(state: ResourceState) -> str:
    return "save_trace" if state.get("terminal_status") else "generate_resource"


async def generate_resource(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    await _set_job_status(job, "generating")

    async def operation():
        if not _can_use_text_model(job.learner_id):
            return _fallback_resource(
                state["context"], reason="文字模型不可用，已使用确定性学习模板。"
            )
        return await _generate_with_text_model(
            job, state["context"], state.get("evidence", [])
        )

    try:
        output = await _node(state, "generate_resource", operation, "llm")
        return {
            "output": output,
            "fallback_used": not _can_use_text_model(job.learner_id),
            "fallback_reason": "text_model_unavailable"
            if not _can_use_text_model(job.learner_id)
            else None,
        }
    except Exception as exc:
        if state["requires_citation"]:
            return {
                "terminal_status": "degraded",
                "fallback_reason": getattr(exc, "error_code", "text_model_unavailable"),
            }
        return {
            "output": _fallback_resource(
                state["context"], reason="文字模型不可用，已使用确定性学习模板。"
            ),
            "fallback_used": True,
            "fallback_reason": getattr(exc, "error_code", "text_model_unavailable"),
        }


async def deterministic_review_node(state: ResourceState) -> dict[str, Any]:
    issues = await _node(
        state,
        "deterministic_review",
        lambda: _deterministic(state),
    )
    return {"deterministic_issues": issues}


async def _deterministic(state: ResourceState) -> list[str]:
    return deterministic_review(
        state["output"],
        state["context"],
        state.get("evidence", []),
        state["requires_rag"],
    )


def _after_deterministic_review(state: ResourceState) -> str:
    issues = set(state.get("deterministic_issues", []))
    if issues & SEVERE_REVIEW_ISSUES:
        state["terminal_status"] = "rejected"
        return "save_trace"
    if issues:
        if state.get("rewrite_count", 0) == 0:
            return "rewrite_if_required"
        state["terminal_status"] = "rejected"
        return "save_trace"
    return "model_review"


async def model_review(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    await _set_job_status(job, "reviewing")
    try:
        review = await _node(
            state,
            "model_review",
            lambda: _model_review(
                job,
                state["output"],
                state["context"],
                state.get("evidence", []),
                state.get("deterministic_issues", []),
            ),
            "llm",
        )
    except Exception as exc:
        if state["requires_citation"]:
            return {
                "terminal_status": "degraded",
                "fallback_reason": getattr(
                    exc, "error_code", "model_review_unavailable"
                ),
            }
        review = ModelResourceReview(decision="pass", score=1, issues=[])
        return {
            "model_review": review,
            "fallback_used": True,
            "fallback_reason": "model_review_unavailable",
        }
    return {"model_review": review}


def _after_model_review(state: ResourceState) -> str:
    review = state.get("model_review")
    if state.get("terminal_status") or review is None:
        return "save_trace"
    if review.decision == "pass":
        return "persist_resource"
    if review.decision == "rewrite" and state.get("rewrite_count", 0) == 0:
        return "rewrite_if_required"
    state["terminal_status"] = "rejected"
    return "save_trace"


async def rewrite_if_required(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    await _set_job_status(job, "rewriting")
    instructions = list(state.get("deterministic_issues", []))
    review = state.get("model_review")
    if review:
        instructions.extend(review.rewrite_instructions)

    async def operation():
        if not _can_use_text_model(job.learner_id):
            return _fallback_resource(
                state["context"], reason="审核后使用确定性模板重写。"
            )
        return await _generate_with_text_model(
            job, state["context"], state.get("evidence", []), instructions
        )

    try:
        output = await _node(state, "rewrite", operation, "llm")
    except Exception:
        return {"terminal_status": "rejected", "rewrite_count": 1}
    return {"output": output, "rewrite_count": 1, "deterministic_issues": []}


async def persist_resource(state: ResourceState) -> dict[str, Any]:
    resource = await _node(
        state,
        "persist_resource",
        lambda: _persist_resource(
            state["session"],
            state["job"],
            state["context"],
            state["output"],
            state.get("evidence", []),
            state["model_review"],
            fallback_used=state.get("fallback_used", False),
            rewrite_count=state.get("rewrite_count", 0),
        ),
    )
    state["job"].resource_id = resource.resource_id
    return {"resource": resource}


async def link_resource(state: ResourceState) -> dict[str, Any]:
    async def operation() -> dict[str, Any]:
        resource = state["resource"]
        if resource.status != "approved":
            return {"linked": False}
        if resource.plan_item_id:
            item = await state["session"].scalar(
                select(LearningPlanItem).where(
                    LearningPlanItem.item_id == resource.plan_item_id,
                    LearningPlanItem.plan_id == resource.plan_id,
                )
            )
            if item:
                item.linked_resource_id = resource.resource_id
        if resource.task_id:
            task = await state["session"].scalar(
                select(LearningTask).where(
                    LearningTask.learning_task_id == resource.task_id,
                    LearningTask.learner_id == resource.learner_id,
                )
            )
            if task:
                task.related_resource_id = resource.resource_id
                task.resource_ids_json = list(
                    dict.fromkeys(
                        [*(task.resource_ids_json or []), resource.resource_id]
                    )
                )
        return {"linked": True}

    return await _node(state, "link_resource", operation)


async def save_trace(state: ResourceState) -> dict[str, Any]:
    job = state["job"]
    if (
        not job.resource_id
        and state.get("terminal_status") != "degraded"
        and state.get("output") is not None
    ):
        rejected_review = state.get("model_review") or ModelResourceReview(
            decision="reject",
            score=0,
            issues=state.get("deterministic_issues", []),
        )
        rejected_resource = await _persist_resource(
            state["session"],
            job,
            state["context"],
            state["output"],
            state.get("evidence", []),
            rejected_review,
            fallback_used=state.get("fallback_used", False),
            rewrite_count=state.get("rewrite_count", 0),
            resource_status="rejected",
        )
        job.resource_id = rejected_resource.resource_id
    if state.get("terminal_status") == "degraded":
        job.status = "degraded"
        job.error_code = state.get("fallback_reason") or "resource_degraded"
        job.error_message = (
            "Required professional evidence or text review is unavailable."
        )
    elif state.get("terminal_status") == "rejected":
        job.status = "rejected"
        job.error_code = "resource_review_failed"
        job.error_message = (
            "Resource did not pass deterministic or professional review."
        )
    elif not job.resource_id:
        job.status = "rejected"
        job.error_code = "resource_review_failed"
        job.error_message = "Resource was not persisted after review."
    else:
        job.status = "completed"
    job.completed_at = datetime.now(UTC)
    state["session"].add(
        TraceRecord(
            trace_id=new_id("trace"),
            task_id=job.task_id or job.job_id,
            learner_id=job.learner_id,
            trace_data_json=json_safe(
                {
                    "trace_kind": "learning_resource_agent",
                    "job_id": job.job_id,
                    "resource_id": job.resource_id,
                    "nodes": state.get("trace_nodes", []),
                }
            ),
        )
    )
    await state["session"].commit()
    await state["session"].refresh(job)
    return {"job_id": job.job_id}


def build_resource_generation_workflow():
    graph = StateGraph(ResourceState)
    graph.add_node("load_resource_context", load_resource_context)
    graph.add_node("load_structured_knowledge", load_structured_knowledge)
    graph.add_node("decide_rag", decide_rag)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("generate_resource", generate_resource)
    graph.add_node("deterministic_review", deterministic_review_node)
    graph.add_node("model_review", model_review)
    graph.add_node("rewrite_if_required", rewrite_if_required)
    graph.add_node("persist_resource", persist_resource)
    graph.add_node("link_resource", link_resource)
    graph.add_node("save_trace", save_trace)
    graph.add_edge(START, "load_resource_context")
    graph.add_edge("load_resource_context", "load_structured_knowledge")
    graph.add_edge("load_structured_knowledge", "decide_rag")
    graph.add_edge("decide_rag", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "validate_evidence")
    graph.add_conditional_edges("validate_evidence", _continue_after_evidence)
    graph.add_edge("generate_resource", "deterministic_review")
    graph.add_conditional_edges("deterministic_review", _after_deterministic_review)
    graph.add_conditional_edges("model_review", _after_model_review)
    graph.add_edge("rewrite_if_required", "deterministic_review")
    graph.add_edge("persist_resource", "link_resource")
    graph.add_edge("link_resource", "save_trace")
    graph.add_edge("save_trace", END)
    return graph.compile()


resource_generation_workflow = build_resource_generation_workflow()


async def run_resource_generation(
    session: AsyncSession,
    job: ResourceGenerationJob,
    *,
    requires_citation: bool = False,
) -> None:
    job.started_at = datetime.now(UTC)
    await resource_generation_workflow.ainvoke(
        {
            "session": session,
            "job": job,
            "requires_citation": requires_citation,
            "trace_nodes": [],
            "rewrite_count": 0,
            "fallback_used": False,
        }
    )
