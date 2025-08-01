"""Tests for NrkPodcastAPI."""

from __future__ import annotations

import logging

from aiohttp import ClientSession
from aiohttp.web_response import json_response
from aresponses import Response, ResponsesMockServer

from kassalappy.models import Product, StatusResponse
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


async def test_product_search_basic(aresponses: ResponsesMockServer, kassalapp_client):
    """Test basic product search functionality."""
    aresponses.add(
        response=json_response(load_fixture_json("products")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        results = await client.product_search(search="milk")
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(product, Product) for product in results)
        assert results[0].name == "Test Product 1"
        assert results[0].current_price == 29.90


async def test_product_search_with_store_filter(aresponses: ResponsesMockServer, kassalapp_client):
    """Test product search with store filter."""
    aresponses.add(
        response=json_response(load_fixture_json("products")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        results = await client.product_search(search="milk", store="SPAR_NO")
        assert isinstance(results, list)
        assert len(results) == 2  # Mock returns same data regardless of filter


async def test_product_search_with_category_filter(aresponses: ResponsesMockServer, kassalapp_client):
    """Test product search with category filter."""
    aresponses.add(
        response=json_response(load_fixture_json("products")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        results = await client.product_search(search="milk", category="dairy")
        assert isinstance(results, list)
        assert len(results) == 2


async def test_product_search_with_has_labels_filter(aresponses: ResponsesMockServer, kassalapp_client):
    """Test product search with has_labels filter."""
    aresponses.add(
        response=json_response(load_fixture_json("products")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        results = await client.product_search(search="milk", has_labels=["euroleaf"])
        assert isinstance(results, list)
        assert len(results) == 2


async def test_product_search_with_all_new_filters(aresponses: ResponsesMockServer, kassalapp_client):
    """Test product search with all new filter parameters."""
    aresponses.add(
        response=json_response(load_fixture_json("products")),
    )
    async with ClientSession() as session:
        client = kassalapp_client(session=session)
        results = await client.product_search(
            search="milk",
            store="MENY_NO",
            category="dairy",
            category_id=1,
            has_labels=["euroleaf", "frysevare"]
        )
        assert isinstance(results, list)
        assert len(results) == 2
