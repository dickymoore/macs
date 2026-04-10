#!/usr/bin/env python3
"""Small helpers for human-readable CLI rendering."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


NARROW_WIDTH = 100


@dataclass(frozen=True)
class TerminalRenderContext:
    width: int
    narrow: bool
    color_enabled: bool


def terminal_render_context() -> TerminalRenderContext:
    columns = _terminal_columns()
    return TerminalRenderContext(
        width=columns,
        narrow=columns < NARROW_WIDTH,
        color_enabled=not bool(os.environ.get("NO_COLOR")),
    )


def key_value_lines(
    label: str,
    value: object,
    context: TerminalRenderContext,
) -> list[str]:
    rendered_value = str(value)
    if context.narrow:
        return [f"{label}:", f"  {rendered_value}"]
    return [f"{label}: {rendered_value}"]


def _terminal_columns() -> int:
    columns = os.environ.get("COLUMNS")
    if columns:
        try:
            parsed = int(columns)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
    return shutil.get_terminal_size(fallback=(120, 24)).columns
