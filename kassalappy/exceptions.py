"""Exceptions."""
from __future__ import annotations

from typing import Literal, cast

import aiohttp


class APIError(Exception):
    message: str
    request: aiohttp.ClientRequest

    body: object | None
    """The API response body.

    If the API responded with a valid JSON structure then this property will be the
    decoded result.

    If it isn't a valid JSON structure then this will be the raw response.

    If there was no response associated with this error then it will be `None`.
    """

    code: str | None
    param: str | None
    type: str | None

    def __init__(self, message: str, request: aiohttp.ClientRequest | aiohttp.RequestInfo, *,
                 body: object | None) -> None:
        super().__init__(message)
        self.request = request
        self.message = message

        if isinstance(body, dict):
            self.code = cast(any, body.get("code"))
            self.param = cast(any, body.get("param"))
            self.type = cast(any, body.get("type"))
        else:
            self.code = None
            self.param = None
            self.type = None


class APIStatusError(APIError):
    """Raised when an API response has a status code of 4xx or 5xx."""

    response: aiohttp.ClientResponse
    status_code: int

    def __init__(self, message: str, *, response: aiohttp.ClientResponse, body: object | None) -> None:
        super().__init__(message, response.request_info, body=body)
        self.response = response
        self.status_code = response.status


class APIConnectionError(APIError):
    def __init__(self, *, message: str = "Connection error.",
                 request: aiohttp.ClientRequest | aiohttp.RequestInfo) -> None:
        super().__init__(message, request, body=None)


class APITimeoutError(APIConnectionError):
    def __init__(self, request: aiohttp.ClientRequest | aiohttp.RequestInfo) -> None:
        super().__init__(message="Request timed out.", request=request)


class BadRequestError(APIStatusError):
    status_code: Literal[400] = 400


class AuthenticationError(APIStatusError):
    status_code: Literal[401] = 401


class PermissionDeniedError(APIStatusError):
    status_code: Literal[403] = 403


class NotFoundError(APIStatusError):
    status_code: Literal[404] = 404


class ConflictError(APIStatusError):
    status_code: Literal[409] = 409


class UnprocessableEntityError(APIStatusError):
    status_code: Literal[422] = 422


class RateLimitError(APIStatusError):
    status_code: Literal[429] = 429


class InternalServerError(APIStatusError):
    pass


class HttpException(Exception):  # noqa: N818
    """Exception base for HTTP errors."""

    def __init__(
        self,
        status: int,
        message: str = "HTTP error",
        errors: dict[str, str] | None = None,
    ):
        self.status = status
        self.message = message
        self.errors = errors
        super().__init__(self.message)


class FatalHttpException(HttpException):
    """Exception raised for HTTP codes that are non-retryable."""


class RetryableHttpException(HttpException):
    """Exception raised for HTTP codes that are possible to retry."""


class AuthorizationError(FatalHttpException):
    """Invalid login exception."""
