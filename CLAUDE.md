# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

kassalappy is a Python client library for the Kassal.app API, providing both programmatic access and CLI functionality for Norwegian grocery store data. It focuses on product search, shopping lists, store information, and webhooks.

## Development Commands

- **Setup**: `make setup` or `poetry install`
- **Testing**: `make test` (run all tests) or `make test-coverage` (with coverage)
- **Linting**: `make format-check` (check) or `make format` (fix)
- **Coverage Report**: `make coverage` (generates HTML report)
- **REPL**: `make repl` (Python shell with project loaded)

## Architecture

### Core Components

- **Client (`kassalappy/client.py`)**: Main `Kassalapp` class handling API communication
  - Async HTTP client using aiohttp
  - Bearer token authentication
  - Comprehensive error handling with custom exceptions
  - Request/response processing with automatic serialization

- **Models (`kassalappy/models.py`)**: Data models using mashumaro for serialization
  - Base classes: `KassalappBaseModel`, `KassalappResource`
  - Product models: `Product`, `ProductComparison`, `ProductCategory`
  - Store models: `PhysicalStore`, `Store`, `PhysicalStoreGroup` enum
  - Shopping list models: `ShoppingList`, `ShoppingListItem`
  - Utility models: `Position`, `ProximitySearch`, `Webhook`

- **CLI (`kassalappy/cli.py`)**: Command-line interface using asyncclick
  - Tabulated output for better readability
  - Commands: health, shopping lists, product search, store search, webhooks

### Key API Endpoints

- **Product Search** (`/products`): Complex filtering by search term, brand, vendor, allergens, price range, store codes, categories, and labels
- **Physical Stores** (`/physical-stores`): Store lookup by name, group, or proximity
- **Shopping Lists** (`/shopping-lists`): CRUD operations for lists and items
- **Webhooks** (`/webhooks`): Webhook management for product updates

### Product Search Filtering

The product search endpoint now supports comprehensive filtering options:
- **Store filtering**: Filter by store codes using `PhysicalStoreGroup` values (e.g., `SPAR_NO`, `MENY_NO`)
- **Category filtering**: Filter by category name or category ID
- **Label filtering**: Filter products that have specific labels (e.g., `euroleaf`, `frysevare`)
- **CLI support**: Store and category filters available via `--store` and `--category` options

## Technical Details

- **Python Version**: 3.10-3.12
- **Async Framework**: aiohttp with async/await patterns
- **Serialization**: mashumaro (migrated from pydantic) with orjson for performance
- **CLI Framework**: asyncclick for async command handling
- **Testing**: pytest with aresponses for HTTP mocking
- **Code Quality**: ruff for linting/formatting, pylint for additional checks

## Recent Updates

The `product_search` method in `client.py` has been enhanced with full API parameter support including:
- Store code filtering via `store` parameter
- Category filtering via `category` and `category_id` parameters  
- Label filtering via `has_labels` parameter
- CLI integration with `--store` and `--category` options

## Testing

- Mock HTTP responses using aresponses
- Fixtures stored in `tests/fixtures/`
- Test helper functions in `tests/helpers.py`
- Coverage configuration in pyproject.toml