from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from typing import Literal

from semiwrap.name_transform import resolve_name_transform

NameKind = Literal["function", "method", "attribute", "enum_value", "parameter"]

_NameTransform = Callable[[str, str], str]


@dataclasses.dataclass(frozen=True, slots=True)
class NameTransforms:
    _snake_transform: _NameTransform
    _caps_transform: _NameTransform

    @classmethod
    def from_known_words(cls, known_words: Sequence[str]) -> NameTransforms:
        known_words_tuple = tuple(known_words)
        return cls(
            _snake_transform=resolve_name_transform(
                "snake_case", known_words=known_words_tuple
            ),
            _caps_transform=resolve_name_transform(
                "CAPS_CASE", known_words=known_words_tuple
            ),
        )

    def to_snake_case(self, name: str, kind: NameKind = "method") -> str:
        if is_dunder(name):
            return name
        return self._snake_transform(name, kind)

    def to_caps_case(self, name: str) -> str:
        if is_dunder(name):
            return name

        leading_underscores = len(name) - len(name.lstrip("_"))
        prefix = name[:leading_underscores]
        stem = name[leading_underscores:]
        if len(stem) > 1 and stem.startswith("k") and stem[1].isupper():
            return f"{prefix}K_{self._caps_transform(stem[1:], 'enum_value')}"

        return self._caps_transform(name, "enum_value")

    def to_caps_case_without_k_prefix(self, name: str) -> str:
        if name.startswith("K_") and len(name) > 2:
            return name[2:]
        return self.to_caps_case(name)


def is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def is_probably_type_name(name: str) -> bool:
    if not name or "_" in name or is_dunder(name):
        return False
    return name[0].isupper() and any(ch.islower() for ch in name[1:])
