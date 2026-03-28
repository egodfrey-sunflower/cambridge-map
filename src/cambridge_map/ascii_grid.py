"""ASCII renderer for the combined grid state."""

from __future__ import annotations

from .combine import CombinedResult

CHARS = {0: "·", 1: "░", 2: "▒", 3: "▓", 4: "█"}


def render_ascii(result: CombinedResult, squares_x: int, squares_y: int) -> str:
    """Render a text grid with north at the top."""
    lines: list[str] = []
    visited_count = 0

    for gy in range(squares_y - 1, -1, -1):
        row = []
        for gx in range(squares_x):
            state = result.grid.get((gx, gy))
            n = len(state.quadrants_visited) if state else 0
            if n > 0:
                visited_count += 1
            row.append(CHARS[n])
        lines.append(" ".join(row))

    total = squares_x * squares_y
    lines.append(
        f"\n{visited_count}/{total} squares visited, {len(result.walks)} walks"
    )
    return "\n".join(lines)
