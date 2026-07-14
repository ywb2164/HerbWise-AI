from __future__ import annotations

from dataclasses import dataclass


PROFESSIONAL_RESOURCE_TYPES = frozenset(
    {"quality_control_case", "professional_guide", "detailed_comparison"}
)


@dataclass(frozen=True)
class RagDecision:
    requires_rag: bool
    reason_codes: list[str]
    query_plan: list[str]


class RagDecisionService:
    """Hard rules for RAG use; a model may not override this decision."""

    def decide(
        self,
        *,
        resource_type: str,
        requires_citation: bool,
        knowledge_points: list[str],
        additional_instruction: str | None,
    ) -> RagDecision:
        reasons: list[str] = []
        if requires_citation:
            reasons.append("citation_required")
        if resource_type in PROFESSIONAL_RESOURCE_TYPES:
            reasons.append("professional_resource")
        instruction = (additional_instruction or "").casefold()
        if any(
            term in instruction for term in ("药典", "来源", "原文", "引用", "标准")
        ):
            reasons.append("explicit_source_request")
        topics = [item.strip() for item in knowledge_points if item.strip()][:3]
        queries = [f"{topic} 中药饮片 性状 鉴别" for topic in topics]
        if resource_type in {"comparison_card", "detailed_comparison"} and topics:
            queries.insert(0, f"{'与'.join(topics[:2])} 饮片性状鉴别区别")
        return RagDecision(bool(reasons), reasons, queries[:5])
