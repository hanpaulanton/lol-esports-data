"""Balanced wikitext template parser (standard library only).

Parses MediaWiki templates without regex-only splitting, so nested
``{{...}}`` templates, ``[[link|text]]`` pipes, and ``<!-- comments -->``
are handled correctly.

Public API:
- find_templates(text) -> list[Template] of TOP-LEVEL templates in document order
- parse_template_args(raw_args) -> TemplateArgs(positional, named)

A Template has: name, args (TemplateArgs), raw text, and source offsets.
Nested templates remain available as raw arg strings and can be re-parsed
recursively.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TemplateArgs:
    positional: list[str] = field(default_factory=list)
    named: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.named.get(key, default)


@dataclass
class Template:
    name: str
    args: TemplateArgs
    raw: str  # verbatim source text including the outer {{ }}
    start: int
    end: int  # index just past the closing }}


def _find_balanced_close(text: str, open_idx: int) -> int:
    """Return the index just past the ``}}`` that closes the ``{{`` at open_idx.

    Tracks nested ``{{ }}``, ``[[ ]]`` (pipes inside links must not be treated
    as argument separators at the outer level) and ``<!-- -->`` comments.
    Raises ValueError on unbalanced input.
    """
    i = open_idx + 2
    depth = 1
    link_depth = 0
    n = len(text)
    while i < n:
        two = text[i : i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return i
            continue
        ch = text[i]
        if ch == "[" and text[i + 1 : i + 2] == "[":
            link_depth += 1
            i += 2
            continue
        if ch == "]" and text[i + 1 : i + 2] == "]":
            if link_depth > 0:
                link_depth -= 1
            i += 2
            continue
        if text[i : i + 4] == "<!--":
            end = text.find("-->", i + 4)
            i = n if end == -1 else end + 3
            continue
        i += 1
    raise ValueError(f"unbalanced template starting at index {open_idx}")


def _split_top_level_args(arg_text: str) -> list[str]:
    """Split template arguments on top-level ``|`` only."""
    parts: list[str] = []
    buf: list[str] = []
    link_depth = 0
    template_depth = 0
    i = 0
    n = len(arg_text)
    while i < n:
        two = arg_text[i : i + 2]
        if two == "{{":
            template_depth += 1
            buf.append(two)
            i += 2
            continue
        if two == "}}" and template_depth > 0:
            template_depth -= 1
            buf.append(two)
            i += 2
            continue
        ch = arg_text[i]
        if ch == "[" and arg_text[i + 1 : i + 2] == "[":
            link_depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == "]" and link_depth > 0:
            link_depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == "|" and link_depth == 0 and template_depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _strip_comments(value: str) -> str:
    """Remove HTML comments; they occur as positional notes in the fixture."""
    out = value
    while True:
        start = out.find("<!--")
        if start == -1:
            return out
        end = out.find("-->", start + 4)
        if end == -1:
            return out[:start]
        out = out[:start] + out[end + 3 :]


def parse_template_args(raw_args: str) -> TemplateArgs:
    """Split raw argument text into positional/named arguments.

    Keys are normalized (trimmed). Values are trimmed only — inner formatting
    (spaces inside links etc.) is preserved so raw data is not distorted.
    Positional arguments (including comment-only positions, which are dropped)
    are preserved in order.
    """
    args = TemplateArgs()
    for index, part in enumerate(_split_top_level_args(raw_args)):
        stripped = part.strip()
        if stripped == "" and index == 0:
            continue  # empty segment right after the template name
        comment_free = _strip_comments(stripped).strip()
        if comment_free == "":
            continue  # comment-only positional argument
        # split at the first top-level '=' (top-level: not inside [[ ]])
        link_depth = 0
        eq_idx = -1
        for i, ch in enumerate(comment_free):
            if ch == "[" and comment_free[i + 1 : i + 2] == "[":
                link_depth += 1
            elif ch == "]" and link_depth > 0:
                link_depth -= 1
            elif ch == "=" and link_depth == 0:
                eq_idx = i
                break
        if eq_idx <= 0:
            args.positional.append(comment_free)
        else:
            key = comment_free[:eq_idx].strip()
            value = comment_free[eq_idx + 1 :].strip()
            args.named[key] = value
    return args


def find_templates(text: str) -> list[Template]:
    """Return all TOP-LEVEL templates in the document, in order.

    Templates nested inside other templates are not returned here; they stay
    verbatim inside their parent's argument values and can be parsed by
    calling find_templates() on those values.
    """
    templates: list[Template] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i : i + 2] == "{{":
            end = _find_balanced_close(text, i)
            raw = text[i:end]
            inner = raw[2:-2]
            # template name = text up to the first top-level '|'
            parts = _split_top_level_args(inner)
            name = _strip_comments(parts[0]).strip() if parts else ""
            args = parse_template_args("|".join(parts[1:]) if len(parts) > 1 else "")
            templates.append(
                Template(name=name, args=args, raw=raw, start=i, end=end)
            )
            i = end
            continue
        i += 1
    return templates


def find_templates_by_name(text: str, name: str) -> list[Template]:
    """Find top-level templates with an exact name (case-sensitive, trimmed)."""
    return [t for t in find_templates(text) if t.name == name]


def find_nested_by_name(value: str, name: str) -> list[Template]:
    """Find templates with the given name among top-level templates of an
    argument VALUE (e.g. game templates nested in a series argument)."""
    return [t for t in find_templates(value) if t.name == name]
