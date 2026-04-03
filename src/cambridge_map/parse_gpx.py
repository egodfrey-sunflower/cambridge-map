"""Phase 1: Parse a GPX file and compute per-walk quadrant coverage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import gpxpy

from .config import Config
from .coords import latlon_to_osgb


@dataclass
class WalkResult:
    name: str
    date: str | None
    total_distance: float  # metres
    track_points: list[tuple[float, float]]  # (lat, lon) for map display
    quadrant_coverage: dict[
        tuple[int, int], set[int]
    ]  # (gx, gy) -> set of quadrant indices 0-3


def parse_gpx(gpx_path: Path, config: Config) -> WalkResult:
    """Parse a GPX file and return per-walk coverage data."""
    grid = config.grid
    origin_e = grid.origin_easting
    origin_n = grid.origin_northing
    sq_size = grid.square_size
    half = sq_size / 2
    squares_x = grid.squares_x
    squares_y = grid.squares_y
    threshold = config.visit.min_contiguous_distance_in_quadrant_per_walk

    with open(gpx_path) as f:
        gpx = gpxpy.parse(f)

    # Extract walk name from filename (without extension).
    name = gpx_path.stem

    # Extract date from the first track's first segment's first point.
    date = None
    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:
                if pt.time is not None:
                    date = pt.time.strftime("%Y-%m-%d")
                    break
            if date:
                break
        if date:
            break

    # Collect all track points and convert to OSGB.
    latlon_points: list[tuple[float, float]] = []
    osgb_points: list[tuple[float, float]] = []

    for track in gpx.tracks:
        for seg in track.segments:
            for pt in seg.points:
                latlon_points.append((pt.latitude, pt.longitude))
                osgb_points.append(latlon_to_osgb(pt.latitude, pt.longitude))

    min_square_dist = config.visit.min_contiguous_distance_in_square_per_walk
    total_distance = 0.0

    def _grid_square(e: float, n: float) -> tuple[int, int] | None:
        """Return (grid_x, grid_y) or None if outside grid."""
        gx = math.floor((e - origin_e) / sq_size)
        gy = math.floor((n - origin_n) / sq_size)
        if 0 <= gx < squares_x and 0 <= gy < squares_y:
            return gx, gy
        return None

    def _quadrant(e: float, n: float, gx: int, gy: int) -> int:
        """Return quadrant index 0-3 within a grid square."""
        local_e = e - (origin_e + gx * sq_size)
        local_n = n - (origin_n + gy * sq_size)
        return (1 if local_e >= half else 0) + (2 if local_n >= half else 0)

    # Walk through points, tracking contiguous stretches within each square.
    # A "stretch" is a run of consecutive points in the same grid square.
    # We accumulate distance and quadrant distances per stretch, then only
    # commit them if the stretch distance meets min_square_dist.

    # Quadrants that met the contiguous distance threshold within a stretch.
    quadrant_coverage: dict[tuple[int, int], set[int]] = {}

    # Current stretch state.
    stretch_dist = 0.0
    stretch_quad_dist: dict[tuple[int, int, int], float] = {}

    def _commit_stretch() -> None:
        """Commit the current stretch if it meets the minimum distance."""
        if stretch_dist >= min_square_dist:
            for (gx, gy, q), d in stretch_quad_dist.items():
                if d >= threshold:
                    quadrant_coverage.setdefault((gx, gy), set()).add(q)

    for i, (e, n) in enumerate(osgb_points):
        sq = _grid_square(e, n)

        if i > 0:
            e_prev, n_prev = osgb_points[i - 1]
            seg_dist = math.hypot(e - e_prev, n - n_prev)
            total_distance += seg_dist

            prev_sq = _grid_square(e_prev, n_prev)

            if sq == prev_sq and sq is not None:
                # Same square — accumulate into current stretch.
                gx, gy = sq
                q = _quadrant(e, n, gx, gy)
                q_prev = _quadrant(e_prev, n_prev, gx, gy)
                if q == q_prev:
                    key = (gx, gy, q)
                    stretch_quad_dist[key] = stretch_quad_dist.get(key, 0.0) + seg_dist
                else:
                    half_dist = seg_dist / 2
                    k1 = (gx, gy, q_prev)
                    k2 = (gx, gy, q)
                    stretch_quad_dist[k1] = stretch_quad_dist.get(k1, 0.0) + half_dist
                    stretch_quad_dist[k2] = stretch_quad_dist.get(k2, 0.0) + half_dist
                stretch_dist += seg_dist
                continue

            # Square changed — commit previous stretch and start new one.
            if prev_sq is not None and sq != prev_sq:
                # Add half the crossing segment to the old stretch.
                gx_p, gy_p = prev_sq
                q_prev = _quadrant(e_prev, n_prev, gx_p, gy_p)
                k_prev = (gx_p, gy_p, q_prev)
                stretch_quad_dist[k_prev] = (
                    stretch_quad_dist.get(k_prev, 0.0) + seg_dist / 2
                )
                stretch_dist += seg_dist / 2
                _commit_stretch()

            # Start new stretch for the new square.
            if sq is not None:
                gx, gy = sq
                q = _quadrant(e, n, gx, gy)
                stretch_dist = seg_dist / 2 if prev_sq is not None else 0.0
                k_new = (gx, gy, q)
                stretch_quad_dist = {k_new: stretch_dist}
            else:
                _commit_stretch()
                stretch_dist = 0.0
                stretch_quad_dist = {}
        else:
            # First point — start a stretch if it's in the grid.
            stretch_dist = 0.0
            stretch_quad_dist = {}

    # Commit final stretch.
    _commit_stretch()

    return WalkResult(
        name=name,
        date=date,
        total_distance=total_distance,
        track_points=latlon_points,
        quadrant_coverage=quadrant_coverage,
    )
