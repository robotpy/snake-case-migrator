from __future__ import annotations

from typing import Literal

from semiwrap.name_transform import resolve_name_transform

NameKind = Literal["function", "method", "attribute", "enum_value", "parameter"]

DEFAULT_KNOWN_WORDS: tuple[str, ...] = (
    "mDNS",
    "L1",
    "L2",
    "L3",
    "R1",
    "R2",
    "R3",
    "DS",
    "CAN",
    "PWM",
    "I2C",
    "SPI",
    "NT",
    "JSON",
    "PID",
    "IMU",
    "HAL",
    "JNI",
    "USB",
    "HTTP",
    "URI",
    "URL",
    "CPU",
    "FPGA",
    "FMS",
    "PCM",
    "PDP",
    "PDH",
    "RIO",
    "OpMode",
    "Pose2d",
    "Translation2d",
    "Rotation2d",
    "Rotation3d",
)

_SNAKE_TRANSFORM = resolve_name_transform("snake_case", known_words=DEFAULT_KNOWN_WORDS)
_CAPS_TRANSFORM = resolve_name_transform("CAPS_CASE", known_words=DEFAULT_KNOWN_WORDS)


def is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def is_probably_type_name(name: str) -> bool:
    if not name or "_" in name or is_dunder(name):
        return False
    return name[0].isupper() and any(ch.islower() for ch in name[1:])


def to_snake_case(name: str, kind: NameKind = "method") -> str:
    if is_dunder(name):
        return name
    return _SNAKE_TRANSFORM(name, kind)


def to_caps_case(name: str) -> str:
    if is_dunder(name):
        return name

    leading_underscores = len(name) - len(name.lstrip("_"))
    prefix = name[:leading_underscores]
    stem = name[leading_underscores:]
    if len(stem) > 1 and stem.startswith("k") and stem[1].isupper():
        return f"{prefix}K_{_CAPS_TRANSFORM(stem[1:], 'enum_value')}"

    return _CAPS_TRANSFORM(name, "enum_value")


def to_caps_case_without_k_prefix(name: str) -> str:
    if name.startswith("K_") and len(name) > 2:
        return name[2:]
    return to_caps_case(name)
