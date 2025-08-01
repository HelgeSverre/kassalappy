"""Library to handle connection with kassalapp web API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
import json
import logging
from types import NoneType
from typing import Literal, Self, TypeVar, cast

from aiohttp import ClientError, ClientResponse, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_PATCH, METH_POST
import async_timeout
from mashumaro.exceptions import MissingField

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
    ValidationError,
)
from .models import (
    KassalappBaseModel,
    PhysicalStore,
    PhysicalStoreGroup,
    Product,
    ProductComparison,
    ProximitySearch,
    ProximitySearchDict,
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
@dataclass
class Kassalapp:
    """Class to communicate with the Kassalapp API."""

    access_token: str
    request_timeout: int = DEFAULT_TIMEOUT
    user_agent: str = f"python kassalappy/{VERSION}"

    websession: ClientSession | None = None

    _close_session: bool = False

    async def __aenter__(self) -> Self:
        if self.websession is None:
            self.websession = ClientSession()
            self._close_websession = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._close_websession:
            await self.websession.close()

    @property
    def request_header(self) -> dict[str, str]:
        """Generate a header for HTTP requests to the server."""
        return {
            "Authorization": "Bearer " + self.access_token,
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    def _ensure_websession(self) -> None:
        if self.websession is None or self.websession.closed:
            self.websession = ClientSession()
            _LOGGER.debug("New session created.")
            self._close_websession = True

    async def _process_response(
        self,
        cast_to: type[ResponseT],
        response: ClientResponse,
    ) -> R:
        response_data = await response.json()

        data = response_data.get("data") if response.ok and "data" in response_data else response_data

        try:
            return await self._process_response_data(
                data=data,
                cast_to=cast_to,
            )
        except (MissingField, TypeError) as err:
            msg = "Unable to deserialize or validate response data"
            raise ValidationError(msg) from err

    async def _process_response_data(
        self,
        data: dict | list[dict],
        cast_to: type[ResponseT],
    ) -> ResponseT | list[ResponseT]:
        if cast_to is NoneType:
            return cast(R, None)

        if cast_to is str:
            return cast(R, data)

        if data is None:
            return cast(ResponseT, None)

        if isinstance(data, list):
            return [cast(ResponseT, cast_to.from_dict(d)) for d in data]

        return cast(ResponseT, cast_to.from_dict(data))

    async def _request_check_status(self, response: ClientResponse):
        err = self._make_status_error_from_response(response)
        if err is not None:
            raise err

    def _make_status_error_from_response(
        self,
        response: ClientResponse,
        err_text: str | None = None,
    ) -> APIStatusError | None:
        if err_text is None:
            err_text = ""
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
        response: ClientResponse,
    ) -> APIStatusError | None:
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

        if not HTTPStatus(response.status).is_success:
            return APIStatusError(err_msg, response=response, body=body)

        return None

    async def execute(
        self,
        endpoint: str,
        cast_to: type[ResponseT] | None = None,
        method: str = METH_GET,
        params: dict[str, any] | None = None,
        data: dict[any, any] | None = None,
    ) -> ResponseT | list[ResponseT] | None:
        """Execute a API request and return the data."""
        request_args = {
            "headers": self.request_header,
            "json": data,
            "params": params,
        }
        request_url = f"{API_ENDPOINT}/{endpoint}"
        response = None
        body = None

        _LOGGER.debug(f"Doing {method} request to '{request_url}' with params: %s", request_args)
        self._ensure_websession()
        try:
            async with async_timeout.timeout(self.request_timeout):
                response = await self.websession.request(
                    method,
                    request_url,
                    **request_args,
                    raise_for_status=self._request_check_status,
                )
                body = await response.text("utf-8")
                _LOGGER.debug("Got response: %s", body)
        except asyncio.TimeoutError as err:
            raise APITimeoutError(request=response.request_info) from err
        except (
            ClientError,
            ClientResponseError,
        ) as err:
            raise self._make_status_error_from_response(response, body) from err

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

    async def get_shopping_list(self, list_id: int, include_items: bool = True) -> ShoppingList:
        """Get a shopping list."""
        params = {}
        if include_items:
            params["include"] = "items"
        return await self.execute(f"shopping-lists/{list_id}", ShoppingList, params=params)

    async def create_shopping_list(self, title: str) -> ShoppingList:
        """Create a new shopping list."""
        return await self.execute("shopping-lists", ShoppingList, METH_POST, data={"title": title})

    async def delete_shopping_list(self, list_id: int):
        """Delete a shopping list."""
        await self.execute(f"shopping-lists/{list_id}", method=METH_DELETE)

    async def update_shopping_list(self, list_id: int, title: str) -> ShoppingList:
        """Update a new shopping list."""
        return await self.execute(
            f"shopping-lists/{list_id}",
            ShoppingList,
            METH_PATCH,
            data={"title": title},
        )

    async def get_shopping_list_items(self, list_id: int) -> list[ShoppingListItem]:
        """Shorthand method to get all items from a shopping list."""
        shopping_list = await self.get_shopping_list(list_id, include_items=True)
        return shopping_list.items or []

    async def add_shopping_list_item(
        self, list_id: int, text: str, product_id: int | None = None
    ) -> ShoppingListItem:
        """Add an item to an existing shopping list."""
        item = {
            "text": text,
            "product_id": product_id,
        }
        return await self.execute(
            f"shopping-lists/{list_id}/items",
            ShoppingListItem,
            METH_POST,
            data=item,
        )

    async def delete_shopping_list_item(self, list_id: int, item_id: int):
        """Remove an item from the shopping list."""
        await self.execute(f"shopping-lists/{list_id}/items/{item_id}", method=METH_DELETE)

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
            METH_PATCH,
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
        sort: Literal["date_asc", "date_desc", "name_asc", "name_desc", "price_asc", "price_desc"]
        | None = None,
        unique: bool = False,
        store: str | None = None,
        has_labels: list[str] | None = None,
        category: str | None = None,
        category_id: int | None = None,
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
        :param store: Filter products by store code (e.g., "SPAR_NO", "MENY_NO").
        :param has_labels: Filter products that have the specified labels (e.g., ["euroleaf", "frysevare"]).
        :param category: Filter products by category name (e.g., "bakeri").
        :param category_id: Filter products by category ID.
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
            "store": store,
            "has_labels": has_labels,
            "category": category,
            "category_id": category_id,
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
        """Get a specific product by id."""
        return await self.execute(
            f"products/id/{product_id}",
            Product,
        )

    async def product_get_by_ean(self, ean: str) -> ProductComparison:
        """Get a specific product by EAN (barcode) number."""
        return await self.execute(
            f"products/ean/{ean}",
            ProductComparison,
        )

    async def physical_stores(
        self,
        search: str | None = None,
        group: PhysicalStoreGroup | None = None,
        proximity: ProximitySearch | ProximitySearchDict | None = None,
        size: int | None = None,
    ) -> list[PhysicalStore]:
        """Search for physical stores.

        Useful for finding a grocery store by name, location or based on the group (grocery store chain),
        returns name, address, contact information and opening hours for each store.

        :param search: Perform a search based on a keyword.
        :param group: Filter by group name.
        :param proximity: Filter by proximity to a specific location.
        :param size: The number of results to be displayed per page. Must be an integer between 1 and 100.
        :return:
        """
        params = {
            "search": search,
            "group": group.value if group is not None else None,
            "size": size,
        }
        if isinstance(proximity, ProximitySearch):
            proximity = proximity.to_dict()

        if proximity is not None:
            params.update(proximity)

        return await self.execute(
            "physical-stores",
            PhysicalStore,
            params={k: v for k, v in params.items() if v is not None},
        )

    async def physical_store(self, store_id: int) -> PhysicalStore:
        """Find a grocery store by ID."""
        return await self.execute(
            f"physical-stores/{store_id}",
            PhysicalStore,
        )

    async def get_webhooks(self) -> list[Webhook]:
        """Retrieve a collection of webhooks associated with the authenticated user."""
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
            METH_PATCH,
            data=data,
        )

    async def delete_webhook(self, webhook_id: int):
        """Remove an existing webhook from the system."""
        await self.execute(f"webhooks/{webhook_id}", method=METH_DELETE)
