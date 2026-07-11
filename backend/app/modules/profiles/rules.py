from collections.abc import Iterable

DIMENSION_CODES = (
    "basic_knowledge",
    "character_identification",
    "similar_medicine",
    "pharmacopoeia_rules",
    "clinical_quality_control",
    "practical_review",
)

DIMENSION_LABELS = {
    "basic_knowledge": "Basic knowledge",
    "character_identification": "Character identification",
    "similar_medicine": "Similar medicine differentiation",
    "pharmacopoeia_rules": "Pharmacopoeia rules",
    "clinical_quality_control": "Clinical quality control",
    "practical_review": "Practical review",
}


def score_level(score: float) -> str:
    if score < 60:
        return "weak"
    if score < 75:
        return "basic"
    if score < 90:
        return "proficient"
    return "excellent"


def diagnose(scores: dict[str, float], weak_points: Iterable[dict] = ()) -> dict:
    normalized = {
        code: round(float(scores.get(code, 0)), 2) for code in DIMENSION_CODES
    }
    average = sum(normalized.values()) / len(DIMENSION_CODES)
    weak_dimensions = [code for code, score in normalized.items() if score < 60]
    weak_knowledge_points = [
        point["knowledge_point"]
        for point in weak_points
        if not point.get("is_resolved", False)
    ]
    if average < 60:
        resource_types, next_task = (
            ["lecture", "quiz"],
            "Complete a foundation review task",
        )
    elif average < 75:
        resource_types, next_task = (
            ["guide", "comparison_card"],
            "Complete a consolidation task",
        )
    else:
        resource_types, next_task = (
            ["quiz", "review_report"],
            "Complete a quality-control review task",
        )
    return {
        "dimension_scores": normalized,
        "overall_score": round(average, 2),
        "overall_level": score_level(average),
        "weak_dimensions": weak_dimensions,
        "weak_knowledge_points": weak_knowledge_points,
        "diagnosis_summary": f"Overall level: {score_level(average)}; weak dimensions: {len(weak_dimensions)}.",
        "recommended_resource_types": resource_types,
        "recommended_next_task": next_task,
    }
