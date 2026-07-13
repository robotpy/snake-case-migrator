from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import tomlkit

from .audit import audit_python_source, audit_semiwrap_yaml_source, iter_audit_files
from .manifest import Manifest, load_manifest, save_manifest
from .names import NameTransforms
from .rewrite_py import rewrite_python_source
from .rewrite_rst import audit_rst_python_source, iter_rst_files, rewrite_rst_python_source
from .rewrite_text import iter_text_files, rewrite_text_source
from .scan_py import iter_python_files, scan_caps_constants_file, scan_python_file
from .scope import manifest_with_global_mapping_scopes


def _add_write_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--write", action="store_true", help="Write changes to disk")
    parser.add_argument("paths", nargs="+", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snake-migrator",
        description="Migrate semiwrap-based Python projects to snake_case APIs.",
    )
    parser.add_argument("--manifest", default="snake_case_migration.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="Create or update manifest files")
    manifest_sub = manifest.add_subparsers(dest="manifest_command", required=True)
    manifest_sub.add_parser("init", help="Create a new manifest")
    manifest_sub.add_parser("check", help="Validate an existing manifest")

    pyproject = subparsers.add_parser(
        "pyproject", help="Apply semiwrap name_transform settings"
    )
    _add_write_paths(pyproject)

    scan_py = subparsers.add_parser(
        "scan-py", help="Scan Python files and update mappings"
    )
    _add_write_paths(scan_py)

    scan_caps_constants = subparsers.add_parser(
        "scan-caps-constants",
        help="Scan Python files and add K_* -> * CAPS_CASE mappings",
    )
    _add_write_paths(scan_caps_constants)

    rewrite_py = subparsers.add_parser(
        "rewrite-py", help="Rewrite Python files using mappings"
    )
    _add_write_paths(rewrite_py)

    rewrite_text = subparsers.add_parser(
        "rewrite-text", help="Rewrite docs/examples text using mappings"
    )
    _add_write_paths(rewrite_text)

    rewrite_rst_python = subparsers.add_parser(
        "rewrite-rst-python",
        help="Rewrite only Python-labeled RST docs/examples using mappings",
    )
    rewrite_rst_python.add_argument(
        "--all-scopes",
        action="store_true",
        help="Apply all manifest mappings regardless of scope for documentation migration",
    )
    _add_write_paths(rewrite_rst_python)

    audit_rst_python = subparsers.add_parser(
        "audit-rst-python",
        help="Report remaining old-style names in Python-labeled RST docs/examples",
    )
    audit_rst_python.add_argument(
        "--all-scopes",
        action="store_true",
        help="Apply all manifest mappings regardless of scope for documentation migration",
    )
    audit_rst_python.add_argument("paths", nargs="+", type=Path)

    audit = subparsers.add_parser("audit", help="Report remaining old-style names")
    audit.add_argument("paths", nargs="+", type=Path)
    return parser


def _load_or_new_manifest(path: Path) -> Manifest:
    if path.exists():
        return load_manifest(path)
    return Manifest()


def _ensure_table(parent: tomlkit.items.Table, key: str) -> tomlkit.items.Table:
    table = parent.get(key)
    if table is None:
        table = tomlkit.table()
        parent.add(key, table)
    return table


def _set_name_transform(semiwrap: tomlkit.items.Table) -> None:
    if semiwrap.get("name_transform") is None:
        semiwrap[tomlkit.key(["name_transform", "default"])] = "snake_case"
    name_transform = semiwrap["name_transform"]
    name_transform["default"] = "snake_case"
    name_transform["enum_value"] = "CAPS_CASE"
    name_transform["known_words"] = []


def _run_pyproject(paths: list[Path], write: bool) -> int:
    changed: list[Path] = []
    for path in paths:
        original = path.read_text()
        doc = tomlkit.parse(original)
        tool = _ensure_table(doc, "tool")
        semiwrap = _ensure_table(tool, "semiwrap")
        _set_name_transform(semiwrap)
        updated = tomlkit.dumps(doc)
        if updated != original:
            changed.append(path)
            if write:
                path.write_text(updated)
    if not write:
        for path in changed:
            print(path)
    return 0


def _run_scan_py(paths: list[Path], manifest_path: Path, write: bool) -> int:
    manifest = _load_or_new_manifest(manifest_path)
    name_transforms = NameTransforms.from_known_words(manifest.known_words)
    before = {
        (mapping.scope, mapping.kind, mapping.old, mapping.new)
        for mapping in manifest.mappings
    }
    for path in iter_python_files(paths):
        scan_python_file(path, manifest, str(path), name_transforms)
    after = {
        (mapping.scope, mapping.kind, mapping.old, mapping.new)
        for mapping in manifest.mappings
    }
    if write:
        save_manifest(manifest_path, manifest)
    else:
        for scope, kind, old, new in sorted(after - before):
            print(f"{scope}: {kind} {old} -> {new}")
    return 0


def _run_scan_caps_constants(
    paths: list[Path], manifest_path: Path, write: bool
) -> int:
    manifest = _load_or_new_manifest(manifest_path)
    name_transforms = NameTransforms.from_known_words(manifest.known_words)
    before = {
        (mapping.scope, mapping.kind, mapping.old, mapping.new)
        for mapping in manifest.mappings
    }
    for path in iter_python_files(paths):
        scan_caps_constants_file(path, manifest, name_transforms)
    after = {
        (mapping.scope, mapping.kind, mapping.old, mapping.new)
        for mapping in manifest.mappings
    }
    if write:
        save_manifest(manifest_path, manifest)
    else:
        for scope, kind, old, new in sorted(after - before):
            print(f"{scope}: {kind} {old} -> {new}")
    return 0


def _run_rewrite_py(paths: list[Path], manifest_path: Path, write: bool) -> int:
    manifest = load_manifest(manifest_path)
    changed: list[Path] = []
    for path in iter_python_files(paths):
        source = path.read_text()
        updated = rewrite_python_source(
            source, manifest, path=path, root_path=manifest_path.parent
        )
        if updated != source:
            changed.append(path)
            if write:
                path.write_text(updated)
    if not write:
        for path in changed:
            print(path)
    return 0


def _run_rewrite_text(paths: list[Path], manifest_path: Path, write: bool) -> int:
    manifest = load_manifest(manifest_path)
    changed: list[Path] = []
    for path in iter_text_files(paths):
        source = path.read_text()
        updated = rewrite_text_source(
            source, manifest, path=path, root_path=manifest_path.parent
        )
        if updated != source:
            changed.append(path)
            if write:
                path.write_text(updated)
    if not write:
        for path in changed:
            print(path)
    return 0


def _load_rst_manifest(manifest_path: Path, all_scopes: bool) -> Manifest:
    manifest = load_manifest(manifest_path)
    if all_scopes:
        return manifest_with_global_mapping_scopes(manifest)
    return manifest


def _run_rewrite_rst_python(
    paths: list[Path], manifest_path: Path, write: bool, all_scopes: bool
) -> int:
    manifest = _load_rst_manifest(manifest_path, all_scopes)
    changed: list[Path] = []
    for path in iter_rst_files(paths):
        source = path.read_text()
        updated = rewrite_rst_python_source(
            source, manifest, path=path, root_path=manifest_path.parent
        )
        if updated != source:
            changed.append(path)
            if write:
                path.write_text(updated)
    if not write:
        for path in changed:
            print(path)
    return 0


def _run_audit_rst_python(
    paths: list[Path], manifest_path: Path, all_scopes: bool
) -> int:
    manifest = _load_rst_manifest(manifest_path, all_scopes)
    found = False
    for path in iter_rst_files(paths):
        source = path.read_text()
        messages = audit_rst_python_source(
            source, manifest, path=path, root_path=manifest_path.parent
        )
        for message in messages:
            print(f"{path}: {message}")
            found = True
    return 1 if found else 0


def _run_audit(paths: list[Path], manifest_path: Path) -> int:
    manifest = load_manifest(manifest_path)
    found = False
    for path in iter_audit_files(paths):
        source = path.read_text()
        if path.suffix in {".yml", ".yaml"}:
            messages = audit_semiwrap_yaml_source(
                source, manifest, path=path, root_path=manifest_path.parent
            )
        else:
            messages = audit_python_source(
                source, manifest, path=path, root_path=manifest_path.parent
            )
        for message in messages:
            print(f"{path}: {message}")
            found = True
    return 1 if found else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest)

    if args.command == "manifest" and args.manifest_command == "init":
        if manifest_path.exists():
            load_manifest(manifest_path)
        else:
            save_manifest(manifest_path, Manifest())
        return 0

    if args.command == "manifest" and args.manifest_command == "check":
        load_manifest(manifest_path)
        return 0

    if args.command == "pyproject":
        return _run_pyproject(args.paths, args.write)

    if args.command == "scan-py":
        return _run_scan_py(args.paths, manifest_path, args.write)

    if args.command == "scan-caps-constants":
        return _run_scan_caps_constants(args.paths, manifest_path, args.write)

    if args.command == "rewrite-py":
        return _run_rewrite_py(args.paths, manifest_path, args.write)

    if args.command == "rewrite-text":
        return _run_rewrite_text(args.paths, manifest_path, args.write)

    if args.command == "rewrite-rst-python":
        return _run_rewrite_rst_python(
            args.paths, manifest_path, args.write, args.all_scopes
        )

    if args.command == "audit-rst-python":
        return _run_audit_rst_python(args.paths, manifest_path, args.all_scopes)

    if args.command == "audit":
        return _run_audit(args.paths, manifest_path)

    return 0
