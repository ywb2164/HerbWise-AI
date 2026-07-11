from fastapi.responses import ORJSONResponse
from pydantic import BaseModel


class UTF8ORJSONResponse(ORJSONResponse):
    media_type = "application/json; charset=utf-8"


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: object | None = None
    request_id: str | None = None


def success(
    data: object | None = None, request_id: str | None = None
) -> UTF8ORJSONResponse:
    return UTF8ORJSONResponse(
        ApiResponse(data=data, request_id=request_id).model_dump()
    )
