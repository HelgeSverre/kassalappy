"""Kassalapp schemas."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel


class KassalappResource(BaseModel):
    """Kassalapp resource."""

    id: int  # noqa: A003
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ShoppingListItem(KassalappResource):
    """Shopping list item."""

    text: str
    checked: bool


class ShoppingList(KassalappResource):
    """Shopping list."""

    title: str
    items: list[ShoppingListItem] = []


ShoppingList.update_forward_refs()
