from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.resources.router import router as resource_router
from app.modules.tasks.router import router as task_router

api_router = APIRouter(prefix=get_settings().api_prefix)
api_router.include_router(task_router)
api_router.include_router(resource_router)
