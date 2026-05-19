"""Tekstnormalisatie voor parser-output.

Direct port van de ``TextNormalizer`` trait — strips controltekens, normaliseert
unicode-spaties, harmoniseert line-endings en trimt regels.
"""

from __future__ import annotations

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_UNICODE_SPACE = re.compile(
    "[  -​  　]"
)
_ZERO_WIDTH = re.compile("[‌‍﻿]")
_TRIPLE_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE_TAB = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = _CONTROL_CHARS.sub("", text)
    text = _UNICODE_SPACE.sub(" ", text)
    text = _ZERO_WIDTH.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRIPLE_NEWLINE.sub("\n\n", text)
    text = _MULTI_SPACE_TAB.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()
