"""Custom API exception hierarchy complying with docs/API_CONTRACT.md error format."""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    """Base API exception that renders {'detail': msg, 'code': code}."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class AssetNotFoundError(APIError):
    def __init__(self, asset_id: str) -> None:
        super().__init__(
            status_code=404,
            detail=f"unknown asset_id {asset_id!r}",
            code="asset_not_found",
        )


class SignalNotFoundError(APIError):
    def __init__(self, signal: str) -> None:
        super().__init__(
            status_code=404,
            detail=f"unknown signal {signal!r}",
            code="signal_not_found",
        )


class ScenarioNotFoundError(APIError):
    def __init__(self, scenario: str) -> None:
        super().__init__(
            status_code=404,
            detail=f"unknown scenario {scenario!r}",
            code="scenario_not_found",
        )


class ModelNotTrainedError(APIError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=503, detail=detail, code="model_not_trained")


class IndexNotBuiltError(APIError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=503, detail=detail, code="index_not_built")


class AgentUnavailableError(APIError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=503, detail=detail, code="agent_unavailable")


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


async def generic_http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "internal_error"
    if exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 400:
        code = "bad_request"
    elif exc.status_code == 503:
        code = "service_unavailable"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail), "code": code},
    )
