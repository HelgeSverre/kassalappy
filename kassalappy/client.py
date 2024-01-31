"""Library to handle connection with kassalapp web API."""
from __future__ import annotations

import json
import logging
from http import HTTPStatus
from types import NoneType
from typing import Literal, TypeVar, cast

import aiohttp
from pydantic import ValidationError

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
    KassalappBaseModel,
    PhysicalStore,
    PhysicalStoreGroup,
    Product,
    ProductComparison,
    ProximitySearch,
    ShoppingList,
    ShoppingListItem,
    StatusResponse,
    Webhook,
)

R = TypeVar("R")

ResponseT = TypeVar(
    "ResponseT",
    bound=KassalappBaseModel | dict[str, any],
)

_LOGGER = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
class Kassalapp:
    """Class to communicate with the Kassalapp API."""

    def __init__(
        self,
        access_token: str,
        timeout: int = DEFAULT_TIMEOUT,
        websession: aiohttp.ClientSession | None = None,
    ):
        """Initialize the Kassalapp connection."""
        self._user_agent: str = f"python kassalappy/{VERSION}"
        self.websession = websession
        self.timeout: int = timeout
        self._access_token: str = access_token
        self._close_websession = False

    async def __aenter__(self) -> Kassalapp:
        if self.websession is None:
            self.websession = aiohttp.ClientSession()
            self._close_websession = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._close_websession:
            await self.websession.close()

    async def _process_response(
        self,
        cast_to: type[ResponseT],
        response: aiohttp.ClientResponse,
    ) -> R:
        response_data = await response.json()

        if response.ok and "data" in response_data:
            data = response_data.get("data")
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
        data: object | list[object],
        cast_to: type[ResponseT],
    ) -> ResponseT | list[ResponseT]:
        if cast_to is NoneType:
            return cast(R, None)

        if cast_to == str:
            return cast(R, data)

        if data is None:
            return cast(ResponseT, None)

        if type(data) is list:
            return [cast(ResponseT, cast_to.model_validate(d)) for d in data]

        return cast(ResponseT, cast_to.model_validate(data))

    def _make_status_error_from_response(
        self,
        response: aiohttp.ClientResponse,
        err_text: str
    ) -> APIStatusError:
        body = err_text.strip()
        try:
            body = json.loads(err_text)
            err_msg = f"Error code: {response.status} - {body}"
        except Exception:  # noqa: BLE001
            err_msg = err_text or f"Error code: {response.status}"

        return self._make_status_error(err_msg, body=body, response=response)

    def _make_status_error(
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
        cast_to: type[ResponseT] | None = None,
        method: str = aiohttp.hdrs.METH_GET,
        params: dict[str, any] | None = None,
        data: dict[any, any] | None = None,
        timeout: int | None = None,
    ) -> ResponseT | list[ResponseT] | None:
        """"Execute a API request and return the data."""
        timeout = timeout or self.timeout

        request_args = {
            "headers": {
                "Authorization": "Bearer " + self._access_token,
                aiohttp.hdrs.USER_AGENT: self._user_agent,
                aiohttp.hdrs.ACCEPT: "application/json",
            },
            "json": data,
            "params": params,
            "timeout": aiohttp.ClientTimeout(total=timeout),
        }
        request_url = f"{API_ENDPOINT}/{endpoint}"
        response = None
        body = None
        try:
            response = await self.websession.request(method, request_url, **request_args)
            body = await response.text()
            response.raise_for_status()
        except aiohttp.ServerTimeoutError as err:
            raise APITimeoutError(request=response.request_info) from err
        except (aiohttp.ClientResponseError, aiohttp.ClientError):
            raise self._make_status_error_from_response(response, body) from None

        if response.status == HTTPStatus.NO_CONTENT:
            return None

        return await self._process_response(
            cast_to=cast_to,
            response=response,
        )

    async def healthy(self) -> StatusResponse:
        """Check if the Kassalapp API is working."""
        return await self.execute("health", StatusResponse)

    async def get_shopping_lists(self, include_items: bool = False) -> list[ShoppingList]:
        """Get shopping lists."""
        params = {}
        if include_items:
            params["include"] = "items"
        return await self.execute("shopping-lists", ShoppingList, params=params)

    async def get_shopping_list(self, list_id: int, include_items: bool = False) -> ShoppingList:
        """Get a shopping list."""
        params = {}
        if include_items:
            params["include"] = "items"
        return await self.execute(f"shopping-lists/{list_id}", ShoppingList, params=params)

    async def create_shopping_list(self, title: str) -> ShoppingList:
        """Create a new shopping list."""
        return await self.execute("shopping-lists", ShoppingList, "post", data={"title": title})

    async def delete_shopping_list(self, list_id: int):
        """Delete a shopping list."""
        await self.execute(f"shopping-lists/{list_id}", method="delete")

    async def update_shopping_list(self, list_id: int, title: str) -> ShoppingList:
        """Update a new shopping list."""
        return await self.execute(
            f"shopping-lists/{list_id}",
            ShoppingList,
            "patch",
            data={"title": title},
        )

    async def get_shopping_list_items(self, list_id: int) -> list[ShoppingListItem]:
        """Shorthand method to get all items from a shopping list."""
        shopping_list = await self.get_shopping_list(list_id, include_items=True)
        return shopping_list.items or []

    async def add_shopping_list_item(self, list_id: int, text: str, product_id: int | None = None) -> ShoppingListItem:
        """Add an item to an existing shopping list."""
        item = {
            "text": text,
            "product_id": product_id,
        }
        return await self.execute(
            f"shopping-lists/{list_id}/items",
            ShoppingListItem,
            "post",
            data=item,
        )

    async def delete_shopping_list_item(self, list_id: int, item_id: int):
        """Remove an item from the shopping list."""
        await self.execute(f"shopping-lists/{list_id}/items/{item_id}", method="delete")

    async def update_shopping_list_item(
        self,
        list_id: int,
        item_id: int,
        text: str | None = None,
        checked: bool | None = None,
    ) -> ShoppingListItem:
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
    ) -> list[Product]:
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

    async def product_find_by_url(self, url: str) -> Product:
        """Will look up product information based on a URL.
        Returns the product price, nutritional information, ingredients, allergens for the product.
        """
        params = {
            "url": url,
        }
        return await self.execute(
            "products/find-by-url/single",
            Product,
            params=params,
        )

    async def products_find_by_url(self, url: str) -> ProductComparison:
        """Will look up product information based on a URL.
        Returns all matching prices from other stores that stock that item.
        """
        params = {
            "url": url,
        }
        return await self.execute(
            "products/find-by-url/compare",
            ProductComparison,
            params=params,
        )

    async def product_get_by_id(self, product_id: int) -> Product:
        """Gets a specific product by id."""
        return await self.execute(
            f"products/id/{product_id}",
            Product,
        )

    async def product_get_by_ean(self, ean: str) -> ProductComparison:
        """Gets a specific product by EAN (barcode) number."""
        return await self.execute(
            f"products/ean/{ean}",
            ProductComparison,
        )

    async def physical_stores(
        self,
        search: str | None = None,
        group: PhysicalStoreGroup | None = None,
        proximity: ProximitySearch | None = None,
        size: int | None = None,
    ) -> list[PhysicalStore]:
        """Search for physical stores.

        Useful for finding a grocery store by name, location or based on the group (grocery store chain),
        returns name, address, contact information and opening hours for each store.

        :param search: Perform a search based on a keyword.
        :param group: Filter by group name.
        :param proximity: Search radius in kilometers for proximity search.
        :param size: The number of results to be displayed per page. Must be an integer between 1 and 100.
        :return:
        """
        params = {
            "search": search,
            "group": group.value if group is not None else None,
            "size": size,
        }
        if proximity is not None:
            params['km'] = proximity['km']
            params['lat'] = proximity['lat']
            params['lng'] = proximity['lng']

        return await self.execute(
            "physical-stores",
            PhysicalStore,
            params={k: v for k, v in params.items() if v is not None},
        )

    async def physical_store(self, store_id: int) -> PhysicalStore:
        """Finds a grocery store by ID."""
        return await self.execute(
            f"physical-stores/{store_id}",
            PhysicalStore,
        )

    async def get_webhooks(self) -> list[Webhook]:
        """Retrieves a collection of webhooks associated with the authenticated user."""
        return await self.execute("webhooks", Webhook)

    async def create_webhook(
        self,
        url: str,
        name: str | None = None,
        ids: list[str] | None = None,
        eans: list[str] | None = None,
    ) -> Webhook:
        """Create and store a new webhook associated with the authenticated user."""
        params = {
            "url": url,
            "name": name,
            "ids": ids,
            "eans": eans,
        }
        return await self.execute(
            "webhooks",
            Webhook,
            params={k: v for k, v in params.items() if v is not None},
        )

    async def update_webhook(
        self,
        webhook_id: int,
        url: str,
        name: str | None = None,
        ids: list[str] | None = None,
        eans: list[str] | None = None,
    ) -> Webhook:
        """Create and store a new webhook associated with the authenticated user."""
        data = {
            "url": url,
            "name": name,
            "ids": ids,
            "eans": eans,
        }
        return await self.execute(
            f"webhooks/{webhook_id}",
            Webhook,
            "patch",
            data=data,
        )

    async def delete_webhook(self, webhook_id: int):
        """Remove an existing webhook from the system."""
        await self.execute(f"webhooks/{webhook_id}", method="delete")
