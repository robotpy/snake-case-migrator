from __future__ import annotations

import ast
import re
from pathlib import Path

from .manifest import Manifest, Mapping, merge_mapping
from .names import (
    is_dunder,
    is_probably_type_name,
    to_caps_case_without_k_prefix,
    to_snake_case,
)

_K_CAPS_RE = re.compile(r"^K_[A-Z0-9_]+$")


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _base_name(node.value)
        if prefix:
            return f"{prefix}.{node.attr}"
        return node.attr
    return ""


def _is_enum_class(node: ast.ClassDef) -> bool:
    return any(
        _base_name(base) in {"Enum", "IntEnum", "enum.Enum", "enum.IntEnum"}
        for base in node.bases
    )


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Attribute) and _base_name(target.value) == "self":
        return [target.attr]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return names
    return []


def _merge_caps_mapping(
    manifest: Manifest,
    *,
    kind: str,
    old: str,
    scope: str,
) -> None:
    if not _K_CAPS_RE.match(old):
        return
    new = to_caps_case_without_k_prefix(old)
    if new == old:
        return
    merge_mapping(
        manifest,
        Mapping(
            kind=kind,
            old=old,
            new=new,
            source="scan-caps-constants",
            scope=scope,
            reason="Pure-Python K_ prefix cleanup",
        ),
    )


def iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                p
                for p in path.rglob("*.py")
                if "__pycache__" not in p.parts and ".git" not in p.parts
            )
    return sorted(files)


def scan_python_file(path: Path, manifest: Manifest, scope: str) -> None:
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if not is_dunder(name) and not is_probably_type_name(name):
                new = to_snake_case(name, "method")
                if new != name:
                    merge_mapping(
                        manifest,
                        Mapping(
                            kind="method",
                            old=name,
                            new=new,
                            source="scan-py",
                            scope=scope,
                        ),
                    )
        elif isinstance(node, ast.arg):
            name = node.arg
            if not is_dunder(name) and not is_probably_type_name(name):
                new = to_snake_case(name, "parameter")
                if new != name:
                    merge_mapping(
                        manifest,
                        Mapping(
                            kind="parameter",
                            old=name,
                            new=new,
                            source="scan-py",
                            scope=scope,
                        ),
                    )


class _CapsConstantScanVisitor(ast.NodeVisitor):
    def __init__(self, manifest: Manifest, scope: str):
        self.manifest = manifest
        self.scope = scope
        self._enum_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        is_enum = _is_enum_class(node)
        if is_enum:
            self._enum_depth += 1
        self.generic_visit(node)
        if is_enum:
            self._enum_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        kind = "enum_value" if self._enum_depth else "attribute"
        for target in node.targets:
            for name in _target_names(target):
                _merge_caps_mapping(
                    self.manifest,
                    kind=kind,
                    old=name,
                    scope=self.scope,
                )
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        kind = "enum_value" if self._enum_depth else "attribute"
        for name in _target_names(node.target):
            _merge_caps_mapping(
                self.manifest,
                kind=kind,
                old=name,
                scope=self.scope,
            )
        if node.value is not None:
            self.visit(node.value)


def scan_caps_constants_file(
    path: Path,
    manifest: Manifest,
    scope: str = "global",
) -> None:
    tree = ast.parse(path.read_text(), filename=str(path))
    _CapsConstantScanVisitor(manifest, scope).visit(tree)
