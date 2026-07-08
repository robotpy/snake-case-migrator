from pathlib import Path

from snake_case_migration.manifest import Manifest
from snake_case_migration.names import NameTransforms
from snake_case_migration.scan_py import scan_caps_constants_file, scan_python_file


def _mapping_dict(manifest: Manifest) -> dict[tuple[str, str, str], str]:
    return {
        (mapping.scope, mapping.kind, mapping.old): mapping.new
        for mapping in manifest.mappings
    }


def _empty_transforms() -> NameTransforms:
    return NameTransforms.from_known_words([])


def test_scan_caps_constants_file_finds_module_class_and_local_constants(
    tmp_path: Path,
):
    source_path = tmp_path / "constants.py"
    source_path.write_text("""\
K_MODULE_PORT = 1

class DriveConstants:
    K_LIGHT_MOTOR_1_PORT = 0
    NORMAL_NAME = 2


def make():
    K_LOCAL_TIMEOUT = 3
    return K_LOCAL_TIMEOUT
""")
    manifest = Manifest()

    scan_caps_constants_file(source_path, manifest, _empty_transforms())

    mappings = _mapping_dict(manifest)
    assert mappings[("global", "attribute", "K_MODULE_PORT")] == "MODULE_PORT"
    assert (
        mappings[("global", "attribute", "K_LIGHT_MOTOR_1_PORT")]
        == "LIGHT_MOTOR_1_PORT"
    )
    assert mappings[("global", "attribute", "K_LOCAL_TIMEOUT")] == "LOCAL_TIMEOUT"
    assert ("global", "attribute", "NORMAL_NAME") not in mappings


def test_scan_caps_constants_file_finds_instance_attribute_constants(tmp_path: Path):
    source_path = tmp_path / "robot.py"
    source_path.write_text("""\
class MyRobot:
    def __init__(self):
        self.K_LED_SPACING = 1 / 120.0
        self.normal_name = 1
        external.K_NOT_OURS = 2
""")
    manifest = Manifest()

    scan_caps_constants_file(source_path, manifest, _empty_transforms())

    mappings = _mapping_dict(manifest)
    assert mappings[("global", "attribute", "K_LED_SPACING")] == "LED_SPACING"
    assert ("global", "attribute", "normal_name") not in mappings
    assert ("global", "attribute", "K_NOT_OURS") not in mappings


def test_scan_caps_constants_file_classifies_enum_members(tmp_path: Path):
    source_path = tmp_path / "modes.py"
    source_path.write_text("""\
from enum import Enum, IntEnum
import enum

class Direction(Enum):
    K_UP = 1
    K_BACK = -1
    ALREADY_GOOD = 0

class Axis(enum.IntEnum):
    K_Z_AXIS = 0
""")
    manifest = Manifest()

    scan_caps_constants_file(source_path, manifest, _empty_transforms())

    mappings = _mapping_dict(manifest)
    assert mappings[("global", "enum_value", "K_UP")] == "UP"
    assert mappings[("global", "enum_value", "K_BACK")] == "BACK"
    assert mappings[("global", "enum_value", "K_Z_AXIS")] == "Z_AXIS"
    assert ("global", "enum_value", "ALREADY_GOOD") not in mappings
    assert ("global", "attribute", "K_UP") not in mappings


def test_scan_caps_constants_file_merges_duplicate_global_mappings(tmp_path: Path):
    source_path = tmp_path / "duplicate.py"
    source_path.write_text("""\
K_WAIT = 1

class Other:
    K_WAIT = 2
""")
    manifest = Manifest()

    scan_caps_constants_file(source_path, manifest, _empty_transforms())

    matches = [
        mapping
        for mapping in manifest.mappings
        if mapping.scope == "global"
        and mapping.kind == "attribute"
        and mapping.old == "K_WAIT"
    ]
    assert len(matches) == 1
    assert matches[0].new == "WAIT"


def test_scan_python_file_uses_manifest_known_words(tmp_path: Path):
    source_path = tmp_path / "robot.py"
    source_path.write_text("""\
def GetOpMode():
    pass
""")
    manifest = Manifest(known_words=["OpMode"])
    transforms = NameTransforms.from_known_words(manifest.known_words)

    scan_python_file(source_path, manifest, str(source_path), transforms)

    mappings = _mapping_dict(manifest)
    assert mappings[(str(source_path), "method", "GetOpMode")] == "get_opmode"
