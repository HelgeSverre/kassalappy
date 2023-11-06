"""Exceptions."""
from kassalappy.const import API_ERR_CODE_UNKNOWN


class HttpException(Exception):
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
