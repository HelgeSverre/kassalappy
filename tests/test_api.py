"""Tests for NrkPodcastAPI."""

from __future__ import annotations

import logging

from aiohttp import ClientSession
from aiohttp.web_response import json_response
from aresponses import Response, ResponsesMockServer

from kassalappy.models import StatusResponse
from .helpers import load_fixture_json

logger = logging.getLogger(__name__)


async def test_health(aresponses: ResponsesMockServer, kassalapp_client):
    aresponses.add(
        response=json_response(load_fixture_json("health")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        result = await client.healthy()
        assert isinstance(result, StatusResponse)
        assert result.status == "ok"
