from __future__ import annotations

import re
from pathlib import Path

from .manifest import Manifest
from .scope import scoped_mappings

TEXT_SUFFIXES = {".md", ".rst", ".py", ".toml", ".yml", ".yaml"}


def iter_text_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            files.extend(
                p
                for p in path.rglob("*")
                if p.is_file()
                and p.suffix in TEXT_SUFFIXES
                and "__pycache__" not in p.parts
                and ".git" not in p.parts
            )
    return sorted(files)


def rewrite_text_source(
    source: str,
    manifest: Manifest,
    path: str | Path | None = None,
    root_path: str | Path | None = None,
) -> str:
    replacements = {
        mapping.old: mapping.new
        for mapping in sorted(
            scoped_mappings(manifest, path, root_path),
            key=lambda m: len(m.old),
            reverse=True,
        )
    }
    if not replacements:
        return source

    pattern = re.compile(
        rf"(?<![A-Za-z0-9_])({'|'.join(re.escape(old) for old in replacements)})(?![A-Za-z0-9_])"
    )
    return pattern.sub(lambda match: replacements[match.group(0)], source)
