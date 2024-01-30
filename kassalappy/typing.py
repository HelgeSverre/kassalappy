from __future__ import annotations

import logging
from enum import Enum
_LOGGER = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
class StrEnum(str, Enum):
    """A string enumeration of type `(str, Enum)`.
    All members are compared via `upper()`. Defaults to UNKNOWN.
    """
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
