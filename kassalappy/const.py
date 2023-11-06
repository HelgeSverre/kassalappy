"""Constants used by kassalapp."""
from http import HTTPStatus
from importlib.metadata import version
from typing import Final

VERSION = version("kassalappy")

API_ENDPOINT: Final = "https://kassal.app/api/v1"
DEFAULT_TIMEOUT: Final = 10

API_ERR_CODE_UNKNOWN: Final = "UNKNOWN"
HTTP_CODES_RETRYABLE: Final = [
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.PRECONDITION_REQUIRED,
]
HTTP_CODES_NO_ACCESS: Final = [
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.FORBIDDEN,
]
HTTP_CODES_FATAL: Final = [HTTPStatus.BAD_REQUEST]
