"""Kassalapp utils."""
from __future__ import annotations

import logging
import re
import aiohttp

from http import HTTPStatus

from .const import (
    API_ERR_CODE_UNKNOWN,
    HTTP_CODES_NO_ACCESS,
    HTTP_CODES_FATAL,
    HTTP_CODES_RETRYABLE,
)
from .exceptions import (
    AuthorizationError,
    FatalHttpException,
    RetryableHttpException,
)
from .models import (
    KassalappResource,
    ShoppingList,
    ShoppingListItem,
)

_LOGGER = logging.getLogger(__name__)

API_ENDPOINTS = {
    r"^/api/v1/shopping-lists$": ShoppingList,
    r"^/api/v1/shopping-lists/(\d+)/items": ShoppingListItem,
}


def path_to_model(req_path: str) -> type[KassalappResource] | None:
    """Resolve path to the expected response model."""
    for path, model in API_ENDPOINTS.items():
        if re.match(path, req_path):
            return model

    return None


async def extract_response_data(
    response: aiohttp.ClientResponse,
    map_to_model: bool = False,
) -> dict[any, any] | KassalappResource | list[KassalappResource] | None:
    """Extract the response as JSON and map to appropriate dataclass."""
    if response.ok and response.content_length == 0:
        _LOGGER.debug("Got an empty OK-like response, returning.")
        return

    if response.content_type != "application/json":
        raise FatalHttpException(
            response.status,
            f"Unexpected content type: {response.content_type}",
            API_ERR_CODE_UNKNOWN,
        )

    result = await response.json()
    if response.ok:
        data = result.get("data") or result
        if map_to_model:
            model = path_to_model(response.url.path)
            if isinstance(data, list):
                return [model(**d) for d in data]
            return model(**data)
        return data

    error_message = result.get("message")
    errors = result.get("errors", {})

    if response.status == HTTPStatus.NOT_FOUND:
        raise FatalHttpException(response.status, error_message)

    if response.status == HTTPStatus.UNPROCESSABLE_ENTITY:
        raise FatalHttpException(response.status, error_message, errors)

    if response.status in HTTP_CODES_NO_ACCESS:
        raise AuthorizationError(response.status, error_message, errors)

    if response.status in HTTP_CODES_RETRYABLE:
        raise RetryableHttpException(response.status, error_message)

    if response.status in HTTP_CODES_FATAL:
        raise FatalHttpException(response.status, error_message, errors)

    # if reached here the HTTP response code is not currently handled
    raise FatalHttpException(
        response.status,
        f"Unhandled error: {error_message}",
        errors,
    )
