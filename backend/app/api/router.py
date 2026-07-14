from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.profiles.router import profiles_router, tests_router
from app.modules.knowledge.router import router as medicine_router
from app.modules.knowledge.rag_router import router as knowledge_router
from app.modules.knowledge.admin_rag_router import router as admin_rag_router
from app.modules.resources.business_router import (
    resource_jobs_router,
    resources_router,
    reviews_router,
)
from app.modules.learning_paths.router import (
    answers_router,
    paths_router,
    reports_router,
)
from app.modules.learning_paths.tasks_router import router as learning_tasks_router
from app.modules.learning_paths.plans_router import router as learning_plans_router
from app.modules.system.admin_router import router as admin_router
from app.modules.system.metrics_router import router as metrics_router
from app.modules.traces.router import router as traces_router
from app.modules.resources.router import router as resource_router
from app.modules.tasks.router import router as task_router
from app.modules.recognition.router import router as recognition_router
from app.modules.system.capabilities_router import router as capabilities_router
from app.modules.system.model_settings_router import router as model_settings_router

api_router = APIRouter(prefix=get_settings().api_prefix)
api_router.include_router(auth_router)
api_router.include_router(profiles_router)
api_router.include_router(tests_router)
api_router.include_router(medicine_router)
api_router.include_router(knowledge_router)
api_router.include_router(admin_rag_router)
api_router.include_router(resources_router)
api_router.include_router(resource_jobs_router)
api_router.include_router(reviews_router)
api_router.include_router(paths_router)
api_router.include_router(reports_router)
api_router.include_router(answers_router)
api_router.include_router(learning_tasks_router)
api_router.include_router(learning_plans_router)
api_router.include_router(admin_router)
api_router.include_router(metrics_router)
api_router.include_router(traces_router)
api_router.include_router(task_router)
api_router.include_router(recognition_router)
api_router.include_router(capabilities_router)
api_router.include_router(model_settings_router)
api_router.include_router(resource_router)
