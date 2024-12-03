from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import ClassVar, Literal

from mashumaro import field_options
from mashumaro.config import ADD_SERIALIZATION_CONTEXT, BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin
from typing_extensions import TypedDict

_LOGGER = logging.getLogger()


# noinspection PyUnresolvedReferences
class StrEnum(str, Enum):
    """A string enumeration of type `(str, Enum)`.
    All members are compared via `upper()`. Defaults to UNKNOWN.
    """

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: str) -> bool:
        other = other.upper()
        return super().__eq__(other)

    @classmethod
    def _missing_(cls, value) -> str:
        has_unknown = False
        for member in cls:
            if member.name.upper() == "UNKNOWN":
                has_unknown = True
            if member.name.upper() == value.upper():
                return member
        if has_unknown:
            _LOGGER.warning("'%s' is not a valid '%s'", value, cls.__name__)
            return cls.UNKNOWN
        raise ValueError(f"'{value}' is not a valid {cls.__name__}")


Unit = Literal[
    "cl",
    "cm",
    "dl",
    "l",
    "g",
    "hg",
    "kg",
    "m",
    "m100",
    "ml",
    "pair",
    "dosage",
    "piece",
    "portion",
    "squareMeter",
]


# noinspection SpellCheckingInspection
class PhysicalStoreGroup(StrEnum):
    MENY_NO = "MENY_NO"
    SPAR_NO = "SPAR_NO"
    JOKER_NO = "JOKER_NO"
    ODA_NO = "ODA_NO"
    ENGROSSNETT_NO = "ENGROSSNETT_NO"
    NAERBUTIKKEN = "NAERBUTIKKEN"
    BUNNPRIS = "BUNNPRIS"
    KIWI = "KIWI"
    REMA_1000 = "REMA_1000"
    EUROPRIS_NO = "EUROPRIS_NO"
    HAVARISTEN = "HAVARISTEN"
    HOLDBART = "HOLDBART"
    FUDI = "FUDI"
    COOP_NO = "COOP_NO"
    COOP_MARKED = "COOP_MARKED"
    MATKROKEN = "MATKROKEN"
    COOP_MEGA = "COOP_MEGA"
    COOP_PRIX = "COOP_PRIX"
    COOP_OBS = "COOP_OBS"
    COOP_EXTRA = "COOP_EXTRA"
    COOP_BYGGMIX = "COOP_BYGGMIX"
    COOP_OBS_BYGG = "COOP_OBS_BYGG"
    COOP_ELEKTRO = "COOP_ELEKTRO"
    ARK = "ARK"
    NORLI = "NORLI"
    ADLIBRIS = "ADLIBRIS"


@dataclass
class BaseModel(DataClassORJSONMixin):
    class Config(BaseConfig):
        omit_none = True
        # omit_default = True
        allow_deserialization_not_by_alias = True
        serialize_by_alias = True
        code_generation_options = [ADD_SERIALIZATION_CONTEXT]


@dataclass
class KassalappBaseModel(BaseModel):
    """Kassalapp base model."""

    BASE_FIELDS: ClassVar[list[str]] = []

    def __post_serialize__(self, d: dict[str, any], context: dict | None = None):
        base_fields = self.get_base_fields()
        if context and context.get("base_fields_only"):
            return {k: v for k, v in d.items() if k in base_fields}
        return d

    @classmethod
    def get_base_fields(cls) -> list[str]:
        fields = []
        for base in cls.__mro__:
            if hasattr(base, "BASE_FIELDS"):
                fields.extend(base.BASE_FIELDS)
        return fields

    def to_base_dict(self) -> dict[str, any]:
        return self.to_dict(
            context={
                "base_fields_only": True,
            }
        )


@dataclass
class KassalappResource(KassalappBaseModel, ABC):
    """Kassalapp resource."""

    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    BASE_FIELDS = ["id", "created_at", "updated_at"]


@dataclass
class AllergenItem(BaseModel):
    code: str
    display_name: str
    contains: str


class Icon(TypedDict):
    svg: str | None
    png: str | None


@dataclass(kw_only=True)
class LabelItem(KassalappBaseModel):
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

    BASE_FIELDS = ["name"]


@dataclass
class NutritionItem(BaseModel):
    code: str
    display_name: str
    amount: float
    unit: str


class OpeningHours(TypedDict):
    monday: str | None
    tuesday: str | None
    wednesday: str | None
    thursday: str | None
    friday: str | None
    saturday: str | None
    sunday: str | None


@dataclass
class Position(BaseModel):
    lat: float
    lng: float


@dataclass
class ProximitySearch(Position):
    km: float


class ProximitySearchDict(TypedDict):
    lat: float
    lng: float
    km: float


@dataclass(kw_only=True)
class PhysicalStore(KassalappResource):
    id: int | None
    group: PhysicalStoreGroup | None
    name: str | None
    address: str | None
    phone: str | None
    email: str | None
    fax: str | None
    logo: str | None
    website: str | None
    detail_url: str | None = field(default=None, metadata=field_options(alias="detailUrl"))
    position: Position | None
    opening_hours: OpeningHours | None = field(default=None, metadata=field_options(alias="openingHours"))

    BASE_FIELDS = ["id", "group"]


@dataclass
class ProductCategory(BaseModel):
    id: int
    depth: int
    name: str


@dataclass(kw_only=True)
class Store(KassalappResource):
    name: str
    code: str | None
    url: str | None
    logo: str | None

    BASE_FIELDS = ["name"]


@dataclass
class Price(BaseModel):
    price: float
    date: datetime


@dataclass
class CurrentPrice(BaseModel):
    unit_price: float | None


@dataclass
class ProductBase(KassalappResource):
    name: str | None = None
    vendor: str | None = None
    brand: str | None = None
    description: str | None = None
    ingredients: str | None = None
    url: str | None = None
    image: str | None = None
    category: list[ProductCategory] | None = None
    store: Store | None = None
    weight: float | None = None
    weight_unit: Unit | None = None
    price_history: list[Price] | None = None

    BASE_FIELDS = ["name"]


@dataclass(kw_only=True)
class Product(ProductBase):
    ean: str | None
    current_price: float | None
    current_unit_price: float | None
    allergens: list[AllergenItem] | None
    nutrition: list[NutritionItem] | None
    labels: list[LabelItem] | None

    BASE_FIELDS = ["ean", "current_price", "current_unit_price"]


@dataclass(kw_only=True)
class ProductComparisonItem(ProductBase):
    current_price: CurrentPrice | None
    kassalapp: dict[str, str]


@dataclass(kw_only=True)
class ProductComparison(KassalappBaseModel):
    ean: str | None
    products: list[ProductComparisonItem] | None
    allergens: list[AllergenItem] | None
    nutrition: list[NutritionItem] | None
    labels: list[LabelItem] | None

    BASE_FIELDS = ["products"]


@dataclass(kw_only=True)
class ShoppingListItem(KassalappResource):
    text: str | None
    checked: bool
    product: ProductComparison | None

    BASE_FIELDS = ["text", "checked", "product"]


@dataclass(kw_only=True)
class ShoppingList(KassalappResource):
    title: str
    items: list[ShoppingListItem] = field(default_factory=list)

    BASE_FIELDS = ["title", "items"]


@dataclass(kw_only=True)
class MessageResponse(KassalappBaseModel):
    message: str


@dataclass(kw_only=True)
class StatusResponse(KassalappBaseModel):
    status: str


@dataclass(kw_only=True)
class Webhook(KassalappResource):
    name: str | None = None
    url: str
    secret: str | None = None
    eans: list[str] | None = None
    ids: list[str] | None = None
