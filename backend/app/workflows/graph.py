from langgraph.graph import END, START, StateGraph

from app.workflows.nodes.main import (
    generate_resources,
    judge_result,
    load_profile,
    recognize_image,
    retrieve_knowledge,
    review_resources,
    save_trace,
    update_learning_path,
    vision_review,
)
from app.workflows.state import WorkflowState


def review_route(state: WorkflowState) -> str:
    if state["review_result"]["status"] == "reject" and state["retry_count"] <= 1:
        return "generate_resources"
    return "update_learning_path"


def build_workflow():
    graph = StateGraph(WorkflowState)
    graph.add_node("load_profile", load_profile)
    graph.add_node("recognize_image", recognize_image)
    graph.add_node("vision_review", vision_review)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("judge_result", judge_result)
    graph.add_node("generate_resources", generate_resources)
    graph.add_node("review_resources", review_resources)
    graph.add_node("update_learning_path", update_learning_path)
    graph.add_node("save_trace", save_trace)
    graph.add_edge(START, "load_profile")
    graph.add_edge("load_profile", "recognize_image")
    graph.add_edge("recognize_image", "vision_review")
    graph.add_edge("vision_review", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "judge_result")
    graph.add_edge("judge_result", "generate_resources")
    graph.add_edge("generate_resources", "review_resources")
    graph.add_conditional_edges(
        "review_resources",
        review_route,
        {
            "generate_resources": "generate_resources",
            "update_learning_path": "update_learning_path",
        },
    )
    graph.add_edge("update_learning_path", "save_trace")
    graph.add_edge("save_trace", END)
    return graph.compile()


workflow = build_workflow()
