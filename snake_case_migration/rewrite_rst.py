from __future__ import annotations

import re
from pathlib import Path

from .manifest import Manifest
from .names import is_dunder, is_probably_type_name
from .rewrite_text import rewrite_text_source
from .scope import scoped_ignored_names, scoped_mapping_name_map

_RST_SUFFIXES = {".rst"}
_FENCE_RE = re.compile(r"^(?P<indent>\s*)```(?P<lang>[A-Za-z0-9_+-]*)\s*$")
_CODE_DIRECTIVE_RE = re.compile(
    r"^(?P<indent>\s*)\.\.\s+(?:code-block|sourcecode)::\s*(?P<lang>\S*)\s*$"
)
_TAB_ITEM_RE = re.compile(r"^(?P<indent>\s*)\.\.\s+tab-item::\s*(?P<title>.*?)\s*$")
_REMOTE_LITERAL_INCLUDE_RE = re.compile(
    r"^\s*\.\.\s+(?:remoteliteralinclude|rli)::\s*.*$", re.IGNORECASE
)
_SYNC_RE = re.compile(r"^\s*:sync:\s*python\s*$", re.IGNORECASE)
_PY_ROLE_RE = re.compile(
    r"(?P<prefix>:(?:external:)?py:[A-Za-z0-9_]+:`)(?P<body>[^`]+)(?P<suffix>`)"
)
_REMOTE_LITERAL_RE = re.compile(
    r"^(?P<indent>\s*)\.\.\s+(?:remoteliteralinclude|rli)::\s*(?P<url>\S+)\s*$",
    re.IGNORECASE,
)
_LANGUAGE_PYTHON_RE = re.compile(r"^\s*:language:\s*python\s*$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL_RE = re.compile(r"[a-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*")


def iter_rst_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix in _RST_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            files.extend(
                p
                for p in path.rglob("*")
                if p.is_file()
                and p.suffix in _RST_SUFFIXES
                and "__pycache__" not in p.parts
                and ".git" not in p.parts
            )
    return sorted(files)


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _is_python_language(language: str) -> bool:
    return language.lower() in {"python", "py"}


def _directive_body_end(lines: list[str], start: int, directive_indent: int) -> int:
    end = start
    while end < len(lines):
        line = lines[end]
        if not _is_blank(line) and _indent_width(line) <= directive_indent:
            break
        end += 1
    return end


def _tab_item_is_python(lines: list[str], index: int, title: str, directive_indent: int) -> bool:
    if title.strip().lower() == "python":
        return True

    body_end = _directive_body_end(lines, index + 1, directive_indent)
    for option_line in lines[index + 1 : body_end]:
        if _is_blank(option_line):
            continue
        if _indent_width(option_line) <= directive_indent:
            break
        if _SYNC_RE.match(option_line):
            return True
        stripped = option_line.strip()
        if not stripped.startswith(":"):
            break
    return False


def _directive_content_start(
    lines: list[str], start: int, end: int, directive_indent: int
) -> int:
    if start >= end:
        return start

    first_line = lines[start]
    if (
        _is_blank(first_line)
        or _indent_width(first_line) <= directive_indent
        or not first_line.lstrip().startswith(":")
    ):
        return start

    idx = start + 1
    while idx < end:
        line = lines[idx]
        if _is_blank(line):
            idx += 1
            while idx < end and _is_blank(lines[idx]):
                idx += 1
            return idx
        if _indent_width(line) <= directive_indent:
            return idx
        idx += 1
    return idx


def _introduces_plain_literal_block(line: str) -> bool:
    stripped = line.strip()
    return stripped.endswith("::") and not stripped.startswith(".. ")


def _plain_literal_block_end(lines: list[str], start: int, block_indent: int) -> int:
    first_content = start
    while first_content < len(lines) and _is_blank(lines[first_content]):
        first_content += 1
    if first_content >= len(lines) or _indent_width(lines[first_content]) <= block_indent:
        return start

    content_indent = _indent_width(lines[first_content])
    idx = first_content + 1
    while idx < len(lines):
        if not _is_blank(lines[idx]) and _indent_width(lines[idx]) < content_indent:
            break
        idx += 1
    return idx


def _rewrite_line(
    line: str,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> str:
    return _rewrite_text_preserving_python_role_display(line, manifest, path, root_path)


def _rewrite_lines(
    lines: list[str],
    start: int,
    end: int,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> None:
    for idx in range(start, end):
        lines[idx] = _rewrite_line(lines[idx], manifest, path, root_path)


def _rewrite_role_body(
    body: str,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> str:
    if "<" in body and body.endswith(">"):
        display, target = body.rsplit("<", 1)
        rewritten_target = rewrite_text_source(
            target[:-1], manifest, path=path, root_path=root_path
        )
        return f"{display}<{rewritten_target}>"
    return rewrite_text_source(body, manifest, path=path, root_path=root_path)


def _rewrite_python_role_match(
    match: re.Match[str],
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> str:
    return "".join(
        [
            match.group("prefix"),
            _rewrite_role_body(match.group("body"), manifest, path, root_path),
            match.group("suffix"),
        ]
    )


def _inline_literal_spans(line: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    search_start = 0
    while True:
        start = line.find("``", search_start)
        if start == -1:
            return spans
        end = line.find("``", start + 2)
        if end == -1:
            return spans
        spans.append((start, end + 2))
        search_start = end + 2


def _position_in_spans(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _has_odd_preceding_backslashes(line: str, position: int) -> bool:
    count = 0
    idx = position - 1
    while idx >= 0 and line[idx] == "\\":
        count += 1
        idx -= 1
    return count % 2 == 1


def _python_role_tokens(
    line: str,
) -> list[tuple[str, int, int, re.Match[str] | None]]:
    inline_spans = [
        (start, end)
        for start, end in _inline_literal_spans(line)
        if _PY_ROLE_RE.search(line[start:end])
    ]
    tokens: list[tuple[str, int, int, re.Match[str] | None]] = [
        ("protected", start, end, None) for start, end in inline_spans
    ]

    for match in _PY_ROLE_RE.finditer(line):
        if _position_in_spans(match.start(), inline_spans):
            continue
        if _has_odd_preceding_backslashes(line, match.start()):
            tokens.append(("protected", match.start(), match.end(), None))
            continue
        tokens.append(("role", match.start(), match.end(), match))

    return sorted(tokens, key=lambda token: token[1])


def _rewrite_line_with_python_role_tokens(
    line: str,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
    *,
    rewrite_non_role_text: bool,
) -> str:
    rewritten_parts: list[str] = []
    last_end = 0
    for token_kind, start, end, match in _python_role_tokens(line):
        segment = line[last_end:start]
        if rewrite_non_role_text:
            segment = rewrite_text_source(
                segment,
                manifest,
                path=path,
                root_path=root_path,
            )
        rewritten_parts.append(segment)

        if token_kind == "role":
            assert match is not None
            rewritten_parts.append(
                _rewrite_python_role_match(match, manifest, path, root_path)
            )
        else:
            rewritten_parts.append(line[start:end])
        last_end = end

    segment = line[last_end:]
    if rewrite_non_role_text:
        segment = rewrite_text_source(segment, manifest, path=path, root_path=root_path)
    rewritten_parts.append(segment)
    return "".join(rewritten_parts)


def _rewrite_python_roles(
    line: str,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> str:
    return _rewrite_line_with_python_role_tokens(
        line,
        manifest,
        path,
        root_path,
        rewrite_non_role_text=False,
    )


def _rewrite_text_preserving_python_role_display(
    line: str,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> str:
    return _rewrite_line_with_python_role_tokens(
        line,
        manifest,
        path,
        root_path,
        rewrite_non_role_text=True,
    )


def _is_probably_type_like_public_name(name: str) -> bool:
    stripped = name.lstrip("_")
    return bool(stripped) and is_probably_type_name(stripped)


def _audit_text(
    text: str,
    lineno: int,
    context: str,
    allowed: set[str],
    mapped_old_names: dict[str, str],
    messages: list[str],
) -> None:
    seen_on_line: set[str] = set()
    for match in _TOKEN_RE.finditer(text):
        name = match.group(0)
        if name in seen_on_line:
            continue
        seen_on_line.add(name)
        if name in allowed or is_dunder(name):
            continue
        if name in mapped_old_names:
            messages.append(
                f"line {lineno} {context}: mapped old name {name!r} remains; "
                f"expected {mapped_old_names[name]!r}"
            )
            continue
        if _is_probably_type_like_public_name(name):
            continue
        if _CAMEL_RE.search(name):
            messages.append(
                f"line {lineno} {context}: unmapped camelCase candidate {name!r}"
            )


def _python_role_target(match: re.Match[str]) -> str:
    body = match.group("body")
    if "<" in body and body.endswith(">"):
        return body.rsplit("<", 1)[1][:-1]
    return body


def _audit_line_with_python_role_tokens(
    line: str,
    lineno: int,
    allowed: set[str],
    mapped_old_names: dict[str, str],
    messages: list[str],
    *,
    audit_non_role_text: bool,
) -> None:
    last_end = 0
    for token_kind, start, end, match in _python_role_tokens(line):
        if audit_non_role_text:
            _audit_text(
                line[last_end:start],
                lineno,
                "python",
                allowed,
                mapped_old_names,
                messages,
            )

        if token_kind == "role":
            assert match is not None
            _audit_text(
                _python_role_target(match),
                lineno,
                "python-role",
                allowed,
                mapped_old_names,
                messages,
            )
        last_end = end

    if audit_non_role_text:
        _audit_text(
            line[last_end:],
            lineno,
            "python",
            allowed,
            mapped_old_names,
            messages,
        )


def _remote_include_is_python(lines: list[str], index: int, directive_indent: int) -> bool:
    body_end = _directive_body_end(lines, index + 1, directive_indent)
    return any(_LANGUAGE_PYTHON_RE.match(line) for line in lines[index + 1 : body_end])


def _rewrite_python_roles_in_prose_lines(
    lines: list[str],
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
) -> None:
    idx = 0
    while idx < len(lines):
        if _REMOTE_LITERAL_INCLUDE_RE.match(lines[idx]):
            directive_indent = _indent_width(lines[idx])
            idx = _directive_body_end(lines, idx + 1, directive_indent)
            continue

        fence_match = _FENCE_RE.match(lines[idx])
        if fence_match is not None:
            fence_end = idx + 1
            while fence_end < len(lines) and not lines[fence_end].lstrip().startswith(
                "```"
            ):
                fence_end += 1
            idx = min(fence_end + 1, len(lines))
            continue

        code_match = _CODE_DIRECTIVE_RE.match(lines[idx])
        if code_match is not None:
            directive_indent = len(code_match.group("indent"))
            idx = _directive_body_end(lines, idx + 1, directive_indent)
            continue

        if _introduces_plain_literal_block(lines[idx]):
            block_indent = _indent_width(lines[idx])
            lines[idx] = _rewrite_python_roles(lines[idx], manifest, path, root_path)
            idx = _plain_literal_block_end(lines, idx + 1, block_indent)
            continue

        lines[idx] = _rewrite_python_roles(lines[idx], manifest, path, root_path)
        idx += 1


def _rewrite_rst_range(
    lines: list[str],
    start: int,
    end: int,
    manifest: Manifest,
    path: str | Path | None,
    root_path: str | Path | None,
    *,
    rewrite_default: bool,
) -> None:
    idx = start
    while idx < end:
        if _REMOTE_LITERAL_INCLUDE_RE.match(lines[idx]):
            directive_indent = _indent_width(lines[idx])
            idx = _directive_body_end(lines, idx + 1, directive_indent)
            continue

        fence_match = _FENCE_RE.match(lines[idx])
        if fence_match is not None:
            lang = fence_match.group("lang")
            fence_end = idx + 1
            while fence_end < end and not lines[fence_end].lstrip().startswith("```"):
                fence_end += 1
            if _is_python_language(lang):
                _rewrite_lines(lines, idx + 1, fence_end, manifest, path, root_path)
            idx = min(fence_end + 1, end)
            continue

        code_match = _CODE_DIRECTIVE_RE.match(lines[idx])
        if code_match is not None:
            directive_indent = len(code_match.group("indent"))
            body_end = _directive_body_end(lines, idx + 1, directive_indent)
            if _is_python_language(code_match.group("lang")):
                content_start = _directive_content_start(
                    lines, idx + 1, body_end, directive_indent
                )
                _rewrite_lines(lines, content_start, body_end, manifest, path, root_path)
            idx = body_end
            continue

        if _introduces_plain_literal_block(lines[idx]):
            block_indent = _indent_width(lines[idx])
            if rewrite_default:
                lines[idx] = _rewrite_line(lines[idx], manifest, path, root_path)
            idx = min(_plain_literal_block_end(lines, idx + 1, block_indent), end)
            continue

        tab_match = _TAB_ITEM_RE.match(lines[idx])
        if tab_match is not None:
            directive_indent = len(tab_match.group("indent"))
            body_end = _directive_body_end(lines, idx + 1, directive_indent)
            body_start = _directive_content_start(lines, idx + 1, body_end, directive_indent)
            _rewrite_rst_range(
                lines,
                body_start,
                body_end,
                manifest,
                path,
                root_path,
                rewrite_default=_tab_item_is_python(
                    lines, idx, tab_match.group("title"), directive_indent
                ),
            )
            idx = body_end
            continue

        if rewrite_default:
            lines[idx] = _rewrite_line(lines[idx], manifest, path, root_path)
        idx += 1


def rewrite_rst_python_source(
    source: str,
    manifest: Manifest,
    path: str | Path | None = None,
    root_path: str | Path | None = None,
) -> str:
    keepends = source.splitlines(keepends=True)
    had_trailing_newline = source.endswith(("\n", "\r"))
    lines = [line[:-1] if line.endswith("\n") else line for line in keepends]
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    if not keepends and source == "":
        return source

    _rewrite_rst_range(
        lines,
        0,
        len(lines),
        manifest,
        path,
        root_path,
        rewrite_default=False,
    )

    _rewrite_python_roles_in_prose_lines(lines, manifest, path, root_path)

    output = "\n".join(lines)
    if had_trailing_newline:
        output += "\n"
    return output


def _audit_rst_range(
    lines: list[str],
    start: int,
    end: int,
    allowed: set[str],
    mapped_old_names: dict[str, str],
    messages: list[str],
    *,
    audit_default: bool,
) -> None:
    idx = start
    while idx < end:
        remote_match = _REMOTE_LITERAL_RE.match(lines[idx])
        if remote_match is not None:
            directive_indent = len(remote_match.group("indent"))
            if _remote_include_is_python(lines, idx, directive_indent):
                messages.append(
                    f"line {idx + 1} remote-python-include: "
                    f"{remote_match.group('url')} is not rewritten"
                )
            idx = min(_directive_body_end(lines, idx + 1, directive_indent), end)
            continue

        fence_match = _FENCE_RE.match(lines[idx])
        if fence_match is not None:
            lang = fence_match.group("lang")
            fence_end = idx + 1
            while fence_end < end and not lines[fence_end].lstrip().startswith("```"):
                fence_end += 1
            if _is_python_language(lang):
                for line_idx in range(idx + 1, fence_end):
                    _audit_text(
                        lines[line_idx],
                        line_idx + 1,
                        "python",
                        allowed,
                        mapped_old_names,
                        messages,
                    )
            idx = min(fence_end + 1, end)
            continue

        code_match = _CODE_DIRECTIVE_RE.match(lines[idx])
        if code_match is not None:
            directive_indent = len(code_match.group("indent"))
            body_end = _directive_body_end(lines, idx + 1, directive_indent)
            if _is_python_language(code_match.group("lang")):
                content_start = _directive_content_start(
                    lines, idx + 1, body_end, directive_indent
                )
                for line_idx in range(content_start, body_end):
                    _audit_text(
                        lines[line_idx],
                        line_idx + 1,
                        "python",
                        allowed,
                        mapped_old_names,
                        messages,
                    )
            idx = min(body_end, end)
            continue

        if _introduces_plain_literal_block(lines[idx]):
            block_indent = _indent_width(lines[idx])
            _audit_line_with_python_role_tokens(
                lines[idx],
                idx + 1,
                allowed,
                mapped_old_names,
                messages,
                audit_non_role_text=audit_default,
            )
            idx = min(_plain_literal_block_end(lines, idx + 1, block_indent), end)
            continue

        tab_match = _TAB_ITEM_RE.match(lines[idx])
        if tab_match is not None:
            directive_indent = len(tab_match.group("indent"))
            body_end = _directive_body_end(lines, idx + 1, directive_indent)
            body_start = _directive_content_start(
                lines, idx + 1, body_end, directive_indent
            )
            _audit_rst_range(
                lines,
                body_start,
                body_end,
                allowed,
                mapped_old_names,
                messages,
                audit_default=_tab_item_is_python(
                    lines, idx, tab_match.group("title"), directive_indent
                ),
            )
            idx = min(body_end, end)
            continue

        _audit_line_with_python_role_tokens(
            lines[idx],
            idx + 1,
            allowed,
            mapped_old_names,
            messages,
            audit_non_role_text=audit_default,
        )
        idx += 1


def audit_rst_python_source(
    source: str,
    manifest: Manifest,
    path: str | Path | None = None,
    root_path: str | Path | None = None,
) -> list[str]:
    keepends = source.splitlines(keepends=True)
    lines = [line[:-1] if line.endswith("\n") else line for line in keepends]
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    allowed = scoped_ignored_names(manifest, path, root_path)
    mapped_old_names = scoped_mapping_name_map(manifest, path, root_path)
    messages: list[str] = []

    _audit_rst_range(
        lines,
        0,
        len(lines),
        allowed,
        mapped_old_names,
        messages,
        audit_default=False,
    )

    return messages
