from fastapi.responses import JSONResponse
from pydantic import BaseModel


class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: object | None = None
    request_id: str | None = None


def success(
    data: object | None = None, request_id: str | None = None
) -> UTF8JSONResponse:
    return UTF8JSONResponse(
        ApiResponse(data=data, request_id=request_id).model_dump(mode="json")
    )
