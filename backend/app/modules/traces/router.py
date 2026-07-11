from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundException
from app.core.responses import ApiResponse, success
from app.modules.auth.service import get_current_user
from app.modules.traces.models import TraceRecord

router = APIRouter(
    prefix="/traces", tags=["traces"], dependencies=[Depends(get_current_user)]
)


def _data(item: TraceRecord) -> dict:
    return {
        "trace_id": item.trace_id,
        "task_id": item.task_id,
        "learner_id": item.learner_id,
        "trace_data": item.trace_data_json,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get(
    "",
    response_model=ApiResponse,
    summary="List traces",
    description="List evidence-chain traces with pagination.",
)
async def list_traces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    total = await session.scalar(select(func.count()).select_from(TraceRecord)) or 0
    records = list(
        (
            await session.scalars(
                select(TraceRecord)
                .order_by(TraceRecord.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return success(
        {
            "items": [_data(item) for item in records],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }
    )


@router.get(
    "/by-task/{task_id}",
    response_model=ApiResponse,
    summary="Get trace by task",
    description="Get all evidence-chain traces for one task.",
)
async def by_task(task_id: str, session: AsyncSession = Depends(get_session)):
    records = list(
        (
            await session.scalars(
                select(TraceRecord)
                .where(TraceRecord.task_id == task_id)
                .order_by(TraceRecord.id)
            )
        ).all()
    )
    if not records:
        raise NotFoundException("Trace not found")
    return success([_data(item) for item in records])


@router.get(
    "/{trace_id}",
    response_model=ApiResponse,
    summary="Get trace",
    description="Get one evidence-chain trace.",
)
async def get_trace(trace_id: str, session: AsyncSession = Depends(get_session)):
    item = await session.scalar(
        select(TraceRecord).where(TraceRecord.trace_id == trace_id)
    )
    if item is None:
        raise NotFoundException("Trace not found")
    return success(_data(item))
