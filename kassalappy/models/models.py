from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast, runtime_checkable

import pydantic
from pydantic import ConfigDict, TypeAdapter
import pydantic.generics
from pydantic.v1.datetime_parse import parse_date, parse_datetime
from pydantic.v1.typing import (
    get_args,
    get_origin,
    is_literal_type,
    is_union,
)
from pydantic_core import PydanticUndefined
from typing_extensions import (
    Protocol,
    override,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

_ModelT = TypeVar("_ModelT", bound=pydantic.BaseModel)
_T = TypeVar("_T")
ResponseT = TypeVar(
    "ResponseT",
    bound="Union[str, None, BaseModel, List[BaseModel], List[any], Dict[str, any]]",
)


@runtime_checkable
class _ConfigProtocol(Protocol):
    allow_population_by_field_name: bool


class BaseGenericModel(pydantic.BaseModel):
    ...


class BaseModel(pydantic.BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")

    @override
    def __str__(self) -> str:
        # mypy complains about an invalid self arg
        return f'{self.__repr_name__()}({self.__repr_str__(", ")})'  # type: ignore[misc]

    # Override the 'construct' method in a way that supports recursive parsing without validation.
    # Based on https://github.com/samuelcolvin/pydantic/issues/1168#issuecomment-817742836.
    @classmethod
    @override
    def construct(
        cls: type[_ModelT],
        _fields_set: set[str] | None = None,
        **values: object,
    ) -> _ModelT:
        m = cls.__new__(cls)
        fields_values: dict[str, object] = {}

        config = get_model_config(cls)
        populate_by_name = (
            config.allow_population_by_field_name
            if isinstance(config, _ConfigProtocol)
            else config.get("populate_by_name")
        )

        if _fields_set is None:
            _fields_set = set()

        model_fields = get_model_fields(cls)
        for name, field in model_fields.items():
            key = field.alias
            if key is None or (key not in values and populate_by_name):
                key = name

            if key in values:
                fields_values[name] = _construct_field(value=values[key], field=field, key=key)
                _fields_set.add(name)
            else:
                fields_values[name] = field_get_default(field)

        _extra = {}
        for key, value in values.items():
            if key not in model_fields:
                _extra[key] = value

        object.__setattr__(m, "__dict__", fields_values)

        # these properties are copied from Pydantic's `model_construct()` method
        object.__setattr__(m, "__pydantic_private__", None)
        object.__setattr__(m, "__pydantic_extra__", _extra)
        object.__setattr__(m, "__pydantic_fields_set__", _fields_set)

        return m

    if not TYPE_CHECKING:
        # type checkers incorrectly complain about this assignment
        # because the type signatures are technically different
        # although not in practice
        model_construct = construct


def parse_obj(model: type[_ModelT], value: object) -> _ModelT:
    return model.model_validate(value)


def get_model_config(model: type[pydantic.BaseModel]) -> Any:
    return model.model_config


def get_model_fields(model: type[pydantic.BaseModel]) -> dict[str, FieldInfo]:
    return model.model_fields


def model_copy(model: _ModelT) -> _ModelT:
    return model.model_copy()


def field_get_default(field: FieldInfo) -> Any:
    value = field.get_default()
    if value == PydanticUndefined:
        return None
    return value


def construct_type(*, value: object, type_: type) -> object:  # noqa: C901, PLR0911, PLR0912
    """Loose coercion to the expected type with construction of nested values.

    If the given value does not match the expected type then it is returned as-is.
    """
    # we need to use the origin class for any types that are subscripted generics e.g. Dict[str, object]
    origin = get_origin(type_) or type_
    args = get_args(type_)

    if is_union(origin):
        try:
            return validate_type(type_=type_, value=value)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001, S110
            pass

        # if the data is not valid, use the first variant that doesn't fail while deserializing
        for variant in args:
            try:
                return construct_type(value=value, type_=variant)
            except Exception:  # noqa: BLE001, PERF203, S112
                continue

        msg = f"Could not convert data into a valid instance of {type_}"
        raise RuntimeError(msg)

    if origin == dict:
        if not isinstance(value, Mapping):
            return value

        _, items_type = get_args(type_)  # Dict[_, items_type]
        return {key: construct_type(value=item, type_=items_type) for key, item in value.items()}

    if not is_literal_type(type_) and (issubclass(origin, BaseModel) or issubclass(origin, GenericModel)):
        if isinstance(value, list):
            return [cast(Any, type_).construct(**entry) if isinstance(entry, Mapping) else entry for entry in value]

        if isinstance(value, Mapping):
            if issubclass(type_, BaseModel):
                return type_.construct(**value)  # type: ignore[arg-type]

            return cast(Any, type_).construct(**value)

    if origin == list:
        if not isinstance(value, list):
            return value

        inner_type = args[0]  # List[inner_type]
        return [construct_type(value=entry, type_=inner_type) for entry in value]

    if origin == float:
        if isinstance(value, int):
            coerced = float(value)
            if coerced != value:
                return value
            return coerced

        return value

    if type_ == datetime:
        try:
            return parse_datetime(value)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return value

    if type_ == date:
        try:
            return parse_date(value)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return value

    return value


def validate_type(*, type_: type[_T], value: object) -> _T:
    """Strict validation that the given value matches the expected type."""
    if inspect.isclass(type_) and issubclass(type_, pydantic.BaseModel):
        return cast(_T, parse_obj(type_, value))

    return cast(_T, _validate_non_model_type(type_=type_, value=value))  # type: ignore[arg-type]


def _validate_non_model_type(*, type_: type[_T], value: object) -> _T:
    return TypeAdapter(type_).validate_python(value)


def _construct_field(value: object, field: FieldInfo, key: str) -> object:
    if value is None:
        return field_get_default(field)

    type_ = field.annotation

    if type_ is None:
        msg = f"Unexpected field type is None for {key}"
        raise RuntimeError(msg)

    return construct_type(value=value, type_=type_)


if TYPE_CHECKING:
    GenericModel = BaseModel
else:

    class GenericModel(BaseGenericModel, BaseModel):
        pass
