import subprocess
import sys

from snake_case_migration import names
from snake_case_migration.names import (
    NameTransforms,
    is_probably_type_name,
)


def test_default_known_words_symbol_is_removed():
    assert not hasattr(names, "DEFAULT_KNOWN_WORDS")


def test_name_transforms_use_empty_known_words_when_given_empty_list():
    transforms = NameTransforms.from_known_words([])

    assert transforms.to_snake_case("GetOpMode") == "get_op_mode"
    assert transforms.to_snake_case("OpModeOption") == "op_mode_option"
    assert transforms.to_snake_case("mDNSResolver") == "m_dns_resolver"


def test_name_transforms_use_explicit_known_words():
    transforms = NameTransforms.from_known_words(["OpMode", "mDNS"])

    assert transforms.to_snake_case("GetOpMode") == "get_opmode"
    assert transforms.to_snake_case("OpModeOption") == "opmode_option"
    assert transforms.to_snake_case("PublishOpModes") == "publish_opmodes"
    assert transforms.to_snake_case("mDNSResolver") == "mdns_resolver"


def test_controller_button_and_geometry_names_still_convert_with_empty_known_words():
    transforms = NameTransforms.from_known_words([])

    assert transforms.to_snake_case("GetL1Button") == "get_l1_button"
    assert transforms.to_snake_case("L2Axis") == "l2_axis"
    assert transforms.to_snake_case("getR3") == "get_r3"
    assert transforms.to_caps_case("L1") == "L1"
    assert transforms.to_caps_case("R2") == "R2"
    assert transforms.to_snake_case("Pose2d") == "pose2d"
    assert transforms.to_snake_case("Translation2d") == "translation2d"
    assert transforms.to_snake_case("Rotation2d") == "rotation2d"
    assert transforms.to_snake_case("Rotation3d") == "rotation3d"
    assert transforms.to_snake_case("ToPose2d") == "to_pose2d"
    assert transforms.to_snake_case("getRotation2d") == "get_rotation2d"
    assert transforms.to_snake_case("getRotation3d") == "get_rotation3d"


def test_caps_case_conversion_methods():
    transforms = NameTransforms.from_known_words([])

    assert transforms.to_caps_case("kHTTPServer") == "K_HTTP_SERVER"
    assert transforms.to_caps_case("valueOne") == "VALUE_ONE"
    assert transforms.to_caps_case_without_k_prefix("K_BLUE") == "BLUE"
    assert transforms.to_caps_case_without_k_prefix("K_EXAMPLE_SELF") == "EXAMPLE_SELF"
    assert (
        transforms.to_caps_case_without_k_prefix("K_LIGHT_MOTOR_1_PORT")
        == "LIGHT_MOTOR_1_PORT"
    )
    assert transforms.to_caps_case_without_k_prefix("K_L1_BUTTON") == "L1_BUTTON"
    assert transforms.to_caps_case_without_k_prefix("valueOne") == "VALUE_ONE"


def test_name_transforms_preserve_leading_underscores():
    transforms = NameTransforms.from_known_words([])

    assert transforms.to_snake_case("_now") == "_now"
    assert transforms.to_snake_case("_GetFPGATime") == "_get_fpga_time"
    assert transforms.to_snake_case("__privateName") == "__private_name"
    assert transforms.to_caps_case("_kValue") == "_K_VALUE"


def test_type_name_detection_keeps_pascal_case_types():
    assert is_probably_type_name("TimedRobot") is True
    assert is_probably_type_name("NetworkTableInstance") is True
    assert is_probably_type_name("getDefault") is False
    assert is_probably_type_name("robotInit") is False


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "snake_case_migration", "--help"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert "snake_case_migration" in result.stdout
    assert "manifest" in result.stdout
    assert "rewrite-py" in result.stdout
