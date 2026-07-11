def build_path(average_score: float, consecutive_errors: int = 0) -> dict:
    if average_score < 60:
        tasks, stage = ["lecture", "simplified_explanation", "quiz"], "foundation"
    elif average_score < 85:
        tasks, stage = ["quiz", "comparison_card"], "consolidation"
    else:
        tasks, stage = ["quality_control_task", "low_confidence_review"], "advanced"
    if consecutive_errors >= 2 and "comparison_card" not in tasks:
        tasks.append("comparison_card")
    return {
        "current_stage": stage,
        "recommended_task_types": tasks,
        "average_score": round(average_score, 2),
        "rule_version": "v0.2-deterministic",
    }
