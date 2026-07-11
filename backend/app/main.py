from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import close_database
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import close_redis, open_redis
from app.core.responses import UTF8ORJSONResponse
from app.modules.system.router import router as system_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await open_redis()
    yield
    await close_redis()
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        default_response_class=UTF8ORJSONResponse,
    )
    app.add_middleware(RequestContextMiddleware)
    install_exception_handlers(app)
    app.include_router(system_router)
    app.include_router(api_router)
    return app


app = create_app()
