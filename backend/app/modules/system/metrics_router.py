from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.responses import ApiResponse, success
from app.modules.auth.service import get_current_user
from app.modules.knowledge.models import KnowledgeSource, MedicineItem
from app.modules.learning_paths.models import LearningPath
from app.modules.resources.business_models import ResourceOutput, ResourceReview
from app.modules.profiles.models import LearnerProfile
from app.modules.tasks.models import TaskRecord

router = APIRouter(
    prefix="/metrics", tags=["metrics"], dependencies=[Depends(get_current_user)]
)


async def _count(session: AsyncSession, model, *filters) -> int:
    return int(
        await session.scalar(select(func.count()).select_from(model).where(*filters))
        or 0
    )


@router.get(
    "/overview",
    response_model=ApiResponse,
    summary="Get overview metrics",
    description="Return counts based on database records; mock quality metrics are not official.",
)
async def overview(session: AsyncSession = Depends(get_session)):
    return success(
        {
            "learner_count": await _count(session, LearnerProfile),
            "medicine_count": await _count(session, MedicineItem),
            "task_count": await _count(session, TaskRecord),
            "successful_task_count": await _count(
                session, TaskRecord, TaskRecord.status == "success"
            ),
            "failed_task_count": await _count(
                session, TaskRecord, TaskRecord.status == "failed"
            ),
            "resource_count": await _count(session, ResourceOutput),
            "approved_resource_count": await _count(
                session, ResourceOutput, ResourceOutput.status == "approved"
            ),
            "review_count": await _count(session, ResourceReview),
            "path_update_count": await _count(session, LearningPath),
            "knowledge_source_count": await _count(session, KnowledgeSource),
            "data_source": "mixed",
            "is_official": False,
        }
    )


def _mock_metric(metric: str) -> dict:
    return {
        "metric_code": metric,
        "data_source": "mock",
        "is_official": False,
        "calculation_method": "Not evaluated in V0.2 mock mode",
        "sample_count": 0,
        "metric_value": None,
    }


@router.get(
    "/hallucination",
    response_model=ApiResponse,
    summary="Get hallucination metric",
    description="Return explicitly non-official mock metric metadata.",
)
async def hallucination():
    return success(_mock_metric("hallucination"))


@router.get(
    "/adaptation",
    response_model=ApiResponse,
    summary="Get adaptation metric",
    description="Return explicitly non-official mock metric metadata.",
)
async def adaptation():
    return success(_mock_metric("adaptation"))


@router.get(
    "/coverage",
    response_model=ApiResponse,
    summary="Get coverage metric",
    description="Return explicitly non-official mock metric metadata.",
)
async def coverage():
    return success(_mock_metric("coverage"))
