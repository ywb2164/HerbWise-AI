"""Bounded LangGraph workflow for personalised learning plans."""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import new_id
from app.common.json import json_safe
from app.core.config import get_settings
from app.integrations.contracts import ModelCallContext
from app.integrations.factory import get_llm_provider
from app.modules.learning_paths.plan_schemas import (
    LearningPlanProposal,
    ProfileAnalysis,
)
from app.modules.learning_paths.plan_service import (
    PROMPT_VERSION,
    PlanValidationError,
    PlanValidationService,
    bind_learning_tasks,
    deterministic_fallback_plan,
    load_learning_context,
    persist_plan,
)
from app.modules.traces.models import TraceRecord

SYSTEM_PROMPT = """You are a Chinese herbal medicine personalised learning planner.
Return only schema-valid JSON. Propose a short plan; never score answers, change
profiles, generate IDs, decide learner identity, or access databases. Prioritise
the weakest dimension, avoid pending-task duplication, and keep total minutes
within daily_minutes."""


class PlanState(TypedDict, total=False):
    session: AsyncSession
    learner_id: str
    daily_minutes: int
    context: dict[str, Any]
    analysis: str
    proposal: LearningPlanProposal
    validation_errors: list[str]
    linked_task_ids: list[str | None]
    provider: str | None
    model_name: str | None
    data_source: str
    fallback_used: bool
    fallback_reason: str | None
    trace_id: str
    trace_nodes: list[dict[str, Any]]
    result: dict[str, Any]


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"keys": sorted(value)[:12]}
    if isinstance(value, LearningPlanProposal):
        return {"items": len(value.items), "daily_minutes": value.daily_minutes}
    return {"type": type(value).__name__}


async def _run_node(state: PlanState, node_code: str, operation):
    started = time.perf_counter()
    try:
        output = await operation()
        status, error = "success", None
    except Exception as exc:  # record the safe failure summary before propagating
        output, status, error = {}, "failed", type(exc).__name__
        raise
    finally:
        state.setdefault("trace_nodes", []).append(
            {
                "node_code": node_code,
                "node_type": "deterministic"
                if node_code
                in {
                    "load_context",
                    "validate_plan",
                    "bind_learning_tasks",
                    "persist_plan",
                }
                else "llm",
                "status": status,
                "input_summary": _summary(state.get("context", {})),
                "output_summary": _summary(output),
                "provider": state.get("provider"),
                "model_name": state.get("model_name"),
                "prompt_version": PROMPT_VERSION,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "retry_count": 1 if node_code == "repair_plan" else 0,
                "data_source": state.get("data_source", "database"),
                "fallback_reason": state.get("fallback_reason"),
                "error_code": error,
            }
        )
    return output


async def load_context(state: PlanState) -> dict[str, Any]:
    result = await _run_node(
        state,
        "load_context",
        lambda: load_learning_context(
            state["session"], state["learner_id"], state["daily_minutes"]
        ),
    )
    return {"context": result, "data_source": "database"}


async def analyze_profile(state: PlanState) -> dict[str, Any]:
    async def operation():
        settings = get_settings()
        if settings.llm_mode == "mock":
            return {"summary": deterministic_fallback_plan(state["context"]).summary}
        provider = get_llm_provider(learner_id=state["learner_id"])
        result = await provider.complete_structured(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(state["context"])},
            ],
            ProfileAnalysis,
            ModelCallContext(
                agent_code="learning_plan",
                learner_id=state["learner_id"],
                prompt_version=PROMPT_VERSION,
            ),
        )
        return result.model_dump()

    result = await _run_node(state, "analyze_profile", operation)
    return {"analysis": result["summary"]}


async def generate_plan(state: PlanState) -> dict[str, Any]:
    settings = get_settings()

    async def operation():
        if settings.llm_mode == "mock":
            return {
                "proposal": deterministic_fallback_plan(state["context"]),
                "fallback": "LLM_MODE=mock",
            }
        provider = get_llm_provider(learner_id=state["learner_id"])
        result = await provider.complete_structured(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": str(state["context"])},
            ],
            LearningPlanProposal,
            ModelCallContext(
                agent_code="learning_plan",
                learner_id=state["learner_id"],
                prompt_version=PROMPT_VERSION,
            ),
        )
        return {"proposal": result, "fallback": None}

    try:
        result = await _run_node(state, "generate_plan", operation)
    except Exception:
        result = {
            "proposal": deterministic_fallback_plan(state["context"]),
            "fallback": "LLM unavailable",
        }
    fallback = result["fallback"]
    return {
        "proposal": result["proposal"],
        "data_source": "deterministic_fallback" if fallback else "llm",
        "fallback_used": bool(fallback),
        "fallback_reason": fallback,
        "provider": "deterministic" if fallback else type(get_llm_provider()).__name__,
        "model_name": None
        if fallback
        else (settings.generation_model or settings.text_model or None),
    }


async def validate_plan(state: PlanState) -> dict[str, Any]:
    errors = await _run_node(
        state,
        "validate_plan",
        lambda: PlanValidationService().validate(
            state["session"], state["learner_id"], state["proposal"], state["context"]
        ),
    )
    return {"validation_errors": errors}


def after_validation(state: PlanState) -> str:
    return "repair_plan" if state.get("validation_errors") else "bind_learning_tasks"


async def repair_plan(state: PlanState) -> dict[str, Any]:
    async def operation():
        # Exactly one bounded repair.  A fallback is already deterministic and safe.
        if state.get("fallback_used"):
            proposal = deterministic_fallback_plan(state["context"])
        else:
            provider = get_llm_provider(learner_id=state["learner_id"])
            result = await provider.complete_structured(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Context: {state['context']} Validation errors: {state['validation_errors']}",
                    },
                ],
                LearningPlanProposal,
                ModelCallContext(
                    agent_code="learning_plan_repair",
                    learner_id=state["learner_id"],
                    prompt_version=PROMPT_VERSION,
                ),
            )
            proposal = result
        errors = await PlanValidationService().validate(
            state["session"], state["learner_id"], proposal, state["context"]
        )
        return {"proposal": proposal, "errors": errors}

    result = await _run_node(state, "repair_plan", operation)
    return {"proposal": result["proposal"], "validation_errors": result["errors"]}


def after_repair(state: PlanState) -> str:
    return "bind_learning_tasks" if not state.get("validation_errors") else "save_trace"


async def bind_tasks(state: PlanState) -> dict[str, Any]:
    linked = await _run_node(
        state,
        "bind_learning_tasks",
        lambda: bind_learning_tasks(
            state["session"], state["learner_id"], state["proposal"]
        ),
    )
    return {"linked_task_ids": linked}


async def persist(state: PlanState) -> dict[str, Any]:
    plan = await _run_node(
        state,
        "persist_plan",
        lambda: persist_plan(
            state["session"],
            state["learner_id"],
            state["proposal"],
            state["context"],
            state["linked_task_ids"],
            provider=state.get("provider"),
            model_name=state.get("model_name"),
            data_source=state["data_source"],
            fallback_used=state["fallback_used"],
        ),
    )
    from app.modules.learning_paths.plan_service import get_plan

    return {
        "result": await get_plan(state["session"], plan.plan_id, state["learner_id"])
    }


async def save_trace(state: PlanState) -> dict[str, Any]:
    async def operation():
        trace_id = state["trace_id"]
        state["session"].add(
            TraceRecord(
                trace_id=trace_id,
                task_id=trace_id,
                learner_id=state["learner_id"],
                trace_data_json=json_safe(
                    {
                        "trace_kind": "learning_plan_agent",
                        "nodes": state.get("trace_nodes", []),
                        "context_summary": {
                            "dimension_count": len(
                                state.get("context", {}).get("dimensions", [])
                            ),
                            "weak_point_count": len(
                                state.get("context", {}).get("weak_points", [])
                            ),
                        },
                    }
                ),
            )
        )
        await state["session"].commit()
        return {"trace_id": trace_id}

    result = await _run_node(state, "save_trace", operation)
    return result


def build_learning_plan_workflow():
    graph = StateGraph(PlanState)
    graph.add_node("load_context", load_context)
    graph.add_node("analyze_profile", analyze_profile)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("validate_plan", validate_plan)
    graph.add_node("repair_plan", repair_plan)
    graph.add_node("bind_learning_tasks", bind_tasks)
    graph.add_node("persist_plan", persist)
    graph.add_node("save_trace", save_trace)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "analyze_profile")
    graph.add_edge("analyze_profile", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")
    graph.add_conditional_edges("validate_plan", after_validation)
    graph.add_conditional_edges("repair_plan", after_repair)
    graph.add_edge("bind_learning_tasks", "persist_plan")
    graph.add_edge("persist_plan", "save_trace")
    graph.add_edge("save_trace", END)
    return graph.compile()


learning_plan_workflow = build_learning_plan_workflow()


async def generate_learning_plan(
    session: AsyncSession, learner_id: str, daily_minutes: int
) -> dict[str, Any]:
    result = await learning_plan_workflow.ainvoke(
        {
            "session": session,
            "learner_id": learner_id,
            "daily_minutes": daily_minutes,
            "trace_id": new_id("trace"),
            "trace_nodes": [],
            "fallback_used": False,
            "data_source": "database",
        }
    )
    if result.get("validation_errors"):
        raise PlanValidationError(result["validation_errors"])
    return result["result"]
