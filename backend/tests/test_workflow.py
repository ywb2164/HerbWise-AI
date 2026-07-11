from app.workflows.graph import review_route


def test_review_allows_one_regeneration() -> None:
    state = {"review_result": {"status": "reject"}, "retry_count": 1}
    assert review_route(state) == "generate_resources"


def test_review_stops_after_retry() -> None:
    state = {"review_result": {"status": "reject"}, "retry_count": 2}
    assert review_route(state) == "update_learning_path"
