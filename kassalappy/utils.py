"""Kassalapp utils."""
from __future__ import annotations

from typing import Type
from http import HTTPStatus
import logging
import re

import aiohttp

from .const import (
    API_ERR_CODE_UNKNOWN,
    HTTP_CODES_FATAL,
    HTTP_CODES_RETRYABLE,
)
from .exceptions import FatalHttpException, RetryableHttpException
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
) -> dict[any, any] | KassalappResource | list[KassalappResource]:
    """Extract the response as JSON and map to appropriate dataclass."""
    if response.content_type != "application/json":
        raise FatalHttpException(
            response.status,
            f"Unexpected content type: {response.content_type}",
            API_ERR_CODE_UNKNOWN,
        )

    result = await response.json()

    if response.status == HTTPStatus.OK:
        data = result.get("data")
        if map_to_model:
            model = path_to_model(response.url.path)
            if isinstance(data, list):
                return [model(**d) for d in data]
            return model(**data)
        return data

    if response.status in HTTP_CODES_RETRYABLE:
        error_message = result.get("message")

        raise RetryableHttpException(
            response.status, message=error_message
        )

    if response.status in HTTP_CODES_FATAL:
        error_message = result.get("message", "")
        # if error_code == API_ERR_CODE_UNAUTH:
        #     raise InvalidLogin(response.status, error_message)

        raise FatalHttpException(response.status, error_message)

    error_message = result.get("mesasge", "")
    # if reached here the HTTP response code is not currently handled
    raise FatalHttpException(
        response.status, f"Unhandled error: {error_message}"
    )
