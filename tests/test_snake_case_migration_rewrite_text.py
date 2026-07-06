from pathlib import Path

from snake_case_migration.manifest import Manifest, Mapping
from snake_case_migration.rewrite_text import rewrite_text_source


def test_rewrite_text_scopes_mappings_by_path_and_keeps_no_path_global_only():
    manifest = Manifest(
        mappings=[
            Mapping(
                scope="subprojects/robotpy-commands-v2/commands2/button",
                kind="method",
                old="r_1",
                new="r1",
                source="test",
            ),
            Mapping(
                scope="global",
                kind="method",
                old="robotInit",
                new="robot_init",
                source="test",
            ),
        ]
    )
    source = "Use robotInit and r_1.\n"

    assert (
        rewrite_text_source(
            source,
            manifest,
            path="subprojects/robotpy-commands-v2/commands2/button/foo.md",
        )
        == "Use robot_init and r1.\n"
    )
    assert (
        rewrite_text_source(
            source,
            manifest,
            path="subprojects/robotpy-wpimath/tests/geometry/test_rotation3d.md",
        )
        == "Use robot_init and r_1.\n"
    )
    assert rewrite_text_source(source, manifest) == "Use robot_init and r_1.\n"


def test_rewrite_text_does_not_replace_inside_larger_identifiers():
    manifest = Manifest(
        mappings=[
            Mapping(
                scope="global",
                kind="attribute",
                old="K_Q",
                new="Q",
                source="test",
            ),
        ]
    )

    assert (
        rewrite_text_source("Use K_Q but leave K_QUOTIENT unchanged.\n", manifest)
        == "Use Q but leave K_QUOTIENT unchanged.\n"
    )


def test_rewrite_text_does_not_cascade_replacements():
    manifest = Manifest(
        mappings=[
            Mapping(
                scope="global",
                kind="attribute",
                old="kZ",
                new="K_Z",
                source="test",
            ),
            Mapping(
                scope="global",
                kind="attribute",
                old="K_Z",
                new="Z",
                source="test",
            ),
        ]
    )

    assert rewrite_text_source("Use kZ and K_Z.\n", manifest) == "Use K_Z and Z.\n"


def test_rewrite_text_matches_absolute_paths_relative_to_root(tmp_path: Path):
    source_path = tmp_path / "pkg" / "button" / "docs.md"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("Use r_1.\n")

    assert (
        rewrite_text_source(
            source_path.read_text(),
            Manifest(
                mappings=[
                    Mapping(
                        scope="pkg/button",
                        kind="method",
                        old="r_1",
                        new="r1",
                        source="test",
                    ),
                ]
            ),
            path=source_path,
            root_path=tmp_path,
        )
        == "Use r1.\n"
    )
