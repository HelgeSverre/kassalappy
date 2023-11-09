"""Library to handle connection with kassalapp web API."""
from __future__ import annotations

from http import HTTPStatus
import json
import logging
from types import NoneType
from typing import Literal, TypeVar, cast

import aiohttp
from pydantic import ValidationError
from typing_extensions import ParamSpec

from .const import (
    API_ENDPOINT,
    DEFAULT_TIMEOUT,
    VERSION,
)
from .exceptions import (
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from .models import (
    MessageResponse,
    Product,
    ShoppingList,
    ShoppingListItem,
)
from .models.models import ResponseT, construct_type

P = ParamSpec("P")
R = TypeVar("R")

_LOGGER = logging.getLogger(__name__)


class Kassalapp:
    """Class to communicate with the Kassalapp API."""

    def __init__(
        self,
        access_token: str,
        timeout: int = DEFAULT_TIMEOUT,
        websession: aiohttp.ClientSession | None = None,
    ):
        """Initialize the Kassalapp connection."""
        if websession is None:
            websession = aiohttp.ClientSession()

        self._user_agent: str = f"python kassalappy/{VERSION}"
        self.websession = websession
        self.timeout: int = timeout
        self._access_token: str = access_token

    async def close_connection(self) -> None:
        """Close the client connection."""
        await self.websession.close()

    async def _process_response(
        self,
        cast_to: type[ResponseT],
        options: dict[str, any],
        response: aiohttp.ClientResponse,
    ) -> R:
        response_data = await response.json()

        if response.ok:
            data = response_data.get("data") or response_data
        else:
            data = response_data

        try:
            return await self._process_response_data(
                data=data,
                cast_to=cast_to,
            )
        except ValidationError:
            _LOGGER.exception("Error validating response data")
            raise

    async def _process_response_data(
        self,
        data: object,
        cast_to: type[ResponseT],
    ) -> ResponseT:
        if cast_to is NoneType:
            return cast(R, None)

        if cast_to == str:
            return cast(R, data)

        if data is None:
            return cast(ResponseT, None)

        return cast(ResponseT, construct_type(type_=cast_to, value=data))

    def _make_status_error_from_response(
        self,
        response: aiohttp.ClientResponse,
        err_text: str
    ) -> APIStatusError:
        # err_text = await response.text()
        body = err_text.strip()

        try:
            body = json.loads(err_text)
            err_msg = f"Error code: {response.status} - {body}"
        except Exception:  # noqa: BLE001
            err_msg = err_text or f"Error code: {response.status}"

        return self._make_status_error(err_msg, body=body, response=response)

    def _make_status_error(  # noqa: PLR0911
        self,
        err_msg: str,
        *,
        body: object,
        response: aiohttp.ClientResponse,
    ) -> APIStatusError:
        if response.status == HTTPStatus.BAD_REQUEST:
            return BadRequestError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.UNAUTHORIZED:
            return AuthenticationError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.FORBIDDEN:
            return PermissionDeniedError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.NOT_FOUND:
            return NotFoundError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.CONFLICT:
            return ConflictError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.UNPROCESSABLE_ENTITY:
            return UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status == HTTPStatus.TOO_MANY_REQUESTS:
            return RateLimitError(err_msg, response=response, body=body)

        if response.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
            return InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)

    async def execute(
        self,
        endpoint: str,
        cast_to: type[ResponseT],
        method: str = aiohttp.hdrs.METH_GET,
        params: dict[str, any] | None = None,
        data: dict[any, any] | None = None,
        timeout: int | None = None,
    ) -> ResponseT:
        """"Execute a API request and return the data."""
        timeout = timeout or self.timeout

        request_args = {
            "headers": {
                "Authorization": "Bearer " + self._access_token,
                aiohttp.hdrs.USER_AGENT: self._user_agent,
            },
            "json": data,
            "params": params,
            "timeout": aiohttp.ClientTimeout(total=timeout),
        }
        request_url = f"{API_ENDPOINT}/{endpoint}"
        options = {}
        try:
            async with self.websession as session:
                response = await session.request(method, request_url, **request_args)
                body = await response.text()
                response.raise_for_status()
        except aiohttp.ServerTimeoutError as err:
            raise APITimeoutError(request=response.request_info) from err
        except (aiohttp.ClientResponseError, aiohttp.ClientError):
            raise self._make_status_error_from_response(response, body) from None

        return await self._process_response(
            cast_to=cast_to,
            options=options,
            response=response,
        )

    async def healthy(self):
        """Check if the Kassalapp API is working."""
        return await self.execute("health", MessageResponse)

    async def get_shopping_lists(self, include_items: bool = False):
        """Get shopping lists."""
        params = {}
        if include_items:
            params["include"] = "items"
        return await self.execute("shopping-lists", ShoppingList, params=params)

    async def get_shopping_list(self, list_id: int, include_items: bool = False):
        """Get a shopping list."""
        params = {}
        if include_items:
            params["include"] = "items"
        return await self.execute(f"shopping-lists/{list_id}", ShoppingList, params=params)

    async def create_shopping_list(self, title: str):
        """Create a new shopping list."""
        return await self.execute("shopping-lists", ShoppingList, "post", data={"title": title})

    async def delete_shopping_list(self, list_id: int):
        """Delete a shopping list."""
        return await self.execute(f"shopping-lists/{list_id}", ShoppingList, "delete")

    async def update_shopping_list(self, list_id: int, title: str):
        """Update a new shopping list."""
        return await self.execute(f"shopping-lists/{list_id}", ShoppingList, "patch", data={"title": title})

    async def get_shopping_list_items(self, list_id: int):
        """Shorthand method to get all items from a shopping list."""
        shopping_list = await self.get_shopping_list(list_id, include_items=True)
        return shopping_list.get("items", [])

    async def add_shopping_list_item(self, list_id: int, text: str, product_id: int | None = None):
        """Add an item to an existing shopping list."""
        item = {
            "text": text,
            "product_id": product_id,
        }
        return await self.execute(f"shopping-lists/{list_id}/items", ShoppingListItem, "post", data=item)

    async def delete_shopping_list_item(self, list_id: int, item_id: int):
        """Remove an item from the shopping list."""
        return await self.execute(
            f"shopping-lists/{list_id}/items/{item_id}",
            MessageResponse,
            "delete",
        )

    async def update_shopping_list_item(
        self,
        list_id: int,
        item_id: int,
        text: str | None = None,
        checked: bool | None = None,
    ):
        """Update an item in the shopping list."""
        data = {
            "text": text,
            "checked": checked,
        }
        return await self.execute(
            f"shopping-lists/{list_id}/items/{item_id}",
            ShoppingListItem,
            "patch",
            data={k: v for k, v in data.items() if v is not None},
        )

    async def product_search(
        self,
        search: str | None = None,
        brand: str | None = None,
        vendor: str | None = None,
        excl_allergens: list[str] | None = None,
        incl_allergens: list[str] | None = None,
        exclude_without_ean: bool = False,
        price_max: float | None = None,
        price_min: float | None = None,
        size: int | None = None,
        sort: Literal["date_asc", "date_desc", "name_asc", "name_desc", "price_asc", "price_desc"] | None = None,
        unique: bool = False,
    ):
        """Search for groceries and various product to find price, ingredients and nutritional information.

        :param search: Search for products based on a keyword.
                       The keyword must be a string with a minimum length of 3 characters.
        :param brand: Filter products by brand name.
        :param vendor: Filter products by vendor (leverandør).
        :param excl_allergens: Exclude specific allergens from the products.
        :param incl_allergens: Include only specific allergens in the products.
        :param exclude_without_ean: If true, products without an EAN number are excluded from the results.
        :param price_max: Filter products by maximum price.
        :param price_min: Filter products by minimum price.
        :param size: The number of products to be displayed per page.
                     Must be an integer between 1 and 100.
        :param sort: Sort the products by a specific criteria.
        :param unique: If true, the product list will be collapsed based on the EAN number of the product;
                       in practice, set this to true if you don't want duplicate results.
        :return:
        """
        params = {
            "search": search,
            "brand": brand,
            "vendor": vendor,
            "excl_allergens": excl_allergens,
            "incl_allergens": incl_allergens,
            "exclude_without_ean": 1 if exclude_without_ean is True else None,
            "price_min": price_min,
            "price_max": price_max,
            "size": size,
            "sort": sort,
            "unique": 1 if unique is True else None,
        }

        return await self.execute(
            "products",
            Product,
            params={k: v for k, v in params.items() if v is not None},
        )

    async def product_find_by_url(self, url: str):
        """Will look up product information based on a URL."""
        params = {
            "url": url,
        }
        return await self.execute(
            "products/find-by-url/single",
            Product,
            params=params,
        )
