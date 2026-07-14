from fastapi import FastAPI, Request

from app.core.responses import UTF8JSONResponse


class AppException(Exception):
    status_code = 400
    code = 1000
    error_code: str | None = None

    def __init__(self, message: str, *, code: int | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code


class NotFoundException(AppException):
    status_code = 404
    code = 1404


class PermissionDeniedException(AppException):
    status_code = 403
    code = 1403


class ExternalServiceException(AppException):
    status_code = 503
    code = 1503


class TaskExecutionException(AppException):
    status_code = 500
    code = 1500


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> UTF8JSONResponse:
        return UTF8JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "error_code": exc.error_code,
                "message": exc.message,
                "data": None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request, _: Exception
    ) -> UTF8JSONResponse:
        return UTF8JSONResponse(
            status_code=500,
            content={
                "code": 1500,
                "message": "Internal server error",
                "data": None,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
