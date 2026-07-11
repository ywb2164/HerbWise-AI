from typing import NotRequired, TypedDict


class WorkflowState(TypedDict):
    task_id: str
    learner_id: str
    image_id: str | None
    image_path: str | None
    profile: NotRequired[dict]
    recognition_result: NotRequired[dict]
    vision_review_result: NotRequired[dict]
    knowledge_evidence: NotRequired[list[dict]]
    judge_result: NotRequired[dict]
    generated_resources: NotRequired[list[dict]]
    review_result: NotRequired[dict]
    path_update: NotRequired[dict]
    trace_id: NotRequired[str]
    current_node: NotRequired[str]
    progress: NotRequired[int]
    retry_count: int
    errors: list[str]
