def test_resource_generation_workflow_imports_and_builds() -> None:
    from app.workflows.resource_generation_graph import (
        build_resource_generation_workflow,
    )

    workflow = build_resource_generation_workflow()

    assert workflow is not None
