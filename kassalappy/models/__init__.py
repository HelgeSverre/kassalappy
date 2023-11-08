"""Kassalapp schemas."""
from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from typing import Literal

from typing_extensions import TypedDict

from .models import BaseModel

Unit = Literal[
    "cl", "cm", "dl", "l",
    "g", "hg", "kg",
    "m", "m100", "ml",
    "pair", "dosage",
    "piece", "portion", "squareMeter"
]


class KassalappResource(BaseModel):
    """Kassalapp resource."""

    id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class AllergenItem(BaseModel):
    code: str
    display_name: str
    contains: str


class Icon(TypedDict):
    svg: str | None
    png: str | None


class LabelItem(BaseModel):
    name: str | None
    display_name: str | None
    description: str | None
    organization: str | None
    alternative_names: str | None
    type: str | None
    year_established: int | None
    about: str | None
    note: str | None
    icon: Icon | None


class NutritionItem(BaseModel):
    code: str
    display_name: str
    amount: float
    unit: str


class OpeningHours(TypedDict):
    monday: str
    tuesday: str
    wednesday: str
    thursday: str
    friday: str
    saturday: str
    sunday: str


class Position(TypedDict):
    lat: float
    lng: float


class PhysicalStore(BaseModel):
    id: int | None
    group: str | None
    name: str | None
    address: str | None
    phone: str | None
    email: str | None
    fax: str | None
    logo: str | None
    website: str | None
    detailUrl: str | None  # noqa: N815
    position: Position | None
    openingHours: OpeningHours | None  # noqa: N815


class ProductCategory(TypedDict):
    id: int
    depth: int
    name: str


class Store(TypedDict):
    name: str
    code: str | None
    url: str | None
    logo: str | None


class Price(TypedDict):
    price: float
    date: datetime


class CurrentPrice(Price):
    unit_price: float | None


class ProductBase(KassalappResource):
    name: str | None
    vendor: str | None
    brand: str | None
    description: str | None
    ingredients: str | None
    url: str | None
    image: str | None
    category: list[ProductCategory] | None
    store: Store | None
    weight: float | None
    weight_unit: Unit | None
    price_history: list[Price] | None


class Product(ProductBase):
    ean: int | None
    current_price: float | None
    current_unit_price: float | None
    allergens: list[AllergenItem] | None
    nutrition: list[NutritionItem] | None
    labels: list[LabelItem] | None


class ProductComparisonItem(ProductBase):
    current_price: CurrentPrice | None
    kassalapp: dict[str, str]


class ProductComparison(ProductBase):
    ean: int | None
    products: list[ProductComparisonItem] | None
    allergens: list[AllergenItem] | None
    nutrition: list[NutritionItem] | None
    labels: list[LabelItem] | None


class ShoppingListItem(KassalappResource):
    text: str | None
    checked: bool
    product: ProductComparison | None


class ShoppingList(KassalappResource):
    title: str
    items: list[ShoppingListItem]


class MessageResponse(TypedDict):
    message: str
