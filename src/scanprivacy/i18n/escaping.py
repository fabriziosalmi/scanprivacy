"""Values that came from the scanned site, made safe to print inside a Markdown report.

A report is built from two kinds of text. The catalogue (rule texts, labels) is ours and may carry
Markdown on purpose. Everything else (cookie and storage key names, hosts, URLs, document titles,
the domain of an unknown vendor) was chosen by the site being scanned, who is not a friend: a
localStorage key can be any string, and one that closes a code span and opens a link turns a report
that a team reads and shares into a place the site can write to.

So a value is untrusted unless it is marked `Trusted`, and an untrusted value is escaped where it
meets the catalogue text, never earlier: the JSON keeps what was observed, byte for byte.
"""

from __future__ import annotations

import re
from typing import Any


class Trusted(str):
    """Text that came from our own catalogues. Passed through untouched."""


_CONTROL = re.compile(r"[\x00-\x1f\x7f  ]+")
_STRUCTURAL = re.compile(r"[\\`*\[\]<>|~&]")
_UNDERSCORE = re.compile(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])")


def md_escape(value: Any) -> Any:
    """Make `value` plain text wherever it lands in Markdown, a table cell included.

    Only strings that are not `Trusted` change; numbers and the rest pass through. Line breaks and
    control characters become one space, so a value cannot start a heading, a list or a fence.
    Characters that open emphasis, code, links, HTML, entities or table cells are backslash-escaped.
    An underscore is escaped only where it could open or close emphasis (not inside a word), which
    keeps `utm_source` readable. `://` is split so a renderer does not turn the text into a link.
    """
    if not isinstance(value, str) or isinstance(value, Trusted):
        return value
    text = _CONTROL.sub(" ", value)
    text = _STRUCTURAL.sub(lambda m: "\\" + m.group(0), text)
    text = _UNDERSCORE.sub(lambda m: "\\_", text)
    text = text.replace("://", ":\\/\\/")
    return text


def md_code(value: Any) -> str:
    """`value` as an inline code span that nothing inside it can close.

    The fence is one backtick longer than the longest run of backticks in the value (a single one
    after the substitution below, so never more than two), and the value is padded with a space when
    it begins or ends with one, as CommonMark requires.
    """
    text = _CONTROL.sub(" ", str(value))
    # A run of two or more backticks would make the fence three or more, which some parsers read as
    # the start of a fenced block when it begins a line. Such a name is shown with reversed primes.
    text = re.sub(r"`{2,}", lambda m: "\u2035" * len(m.group()), text)
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"
