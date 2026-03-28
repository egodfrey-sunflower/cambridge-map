"""Phase 2: Merge per-walk coverage results into overall grid state."""

from __future__ import annotations

from dataclasses import dataclass, field

from .parse_gpx import WalkResult


@dataclass
class SquareState:
    quadrants_visited: set[int] = field(default_factory=set)
    walks: list[str] = field(default_factory=list)


@dataclass
class CombinedResult:
    grid: dict[tuple[int, int], SquareState]
    walks: list[WalkResult]


def combine(walk_results: list[WalkResult]) -> CombinedResult:
    """Merge all per-walk coverage into a single grid state."""
    grid: dict[tuple[int, int], SquareState] = {}

    for walk in walk_results:
        for (gx, gy), quads in walk.quadrant_coverage.items():
            key = (gx, gy)
            if key not in grid:
                grid[key] = SquareState()
            grid[key].quadrants_visited |= quads
            if walk.name not in grid[key].walks:
                grid[key].walks.append(walk.name)

    return CombinedResult(grid=grid, walks=walk_results)
