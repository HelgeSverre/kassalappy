from __future__ import annotations

import logging
from typing import Callable

from aiohttp import ClientSession

import pytest

from kassalappy import Kassalapp

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def kassalapp_client(default_access_token) -> Callable[..., Kassalapp]:
    """Return Politikontroller Client."""

    def _kassalapp_client(
        access_token: str | None = None,
        session: ClientSession | None = None,
    ) -> Kassalapp:
        token = access_token if access_token is not None else default_access_token
        return Kassalapp(access_token=token, websession=session)

    return _kassalapp_client


@pytest.fixture
def default_access_token():
    return "baba"
