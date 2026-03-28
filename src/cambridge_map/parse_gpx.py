"""Phase 1: Parse a GPX file and compute per-walk quadrant coverage."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import gpxpy

from .coords import latlon_to_osgb


@dataclass
class WalkResult:
    name: str
    date: str | None
    total_distance: float  # metres
    track_points: list[tuple[float, float]]  # (lat, lon) for map display
    quadrant_coverage: dict[tuple[int, int], set[int]]  # (gx, gy) -> set of quadrant indices 0-3


def parse_gpx(gpx_path: Path, config: dict) -> WalkResult:
    """Parse a GPX file and return per-walk coverage data."""
    grid = config["grid"]
    origin_e = grid["origin_easting"]
    origin_n = grid["origin_northing"]
    sq_size = grid["square_size"]
    half = sq_size / 2
    squares_x = grid["squares_x"]
    squares_y = grid["squares_y"]
    threshold = config["visit"]["quadrant_threshold"]

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

    # Accumulate distance per quadrant.
    # quadrant_dist[(gx, gy, q)] = total distance in metres
    quadrant_dist: dict[tuple[int, int, int], float] = {}
    total_distance = 0.0

    def _grid_quadrant(e: float, n: float) -> tuple[int, int, int] | None:
        """Return (grid_x, grid_y, quadrant) for an OSGB point, or None if outside grid."""
        gx = int((e - origin_e) / sq_size)
        gy = int((n - origin_n) / sq_size)
        if not (0 <= gx < squares_x and 0 <= gy < squares_y):
            return None
        # Quadrant within square: 0=SW, 1=SE, 2=NW, 3=NE
        local_e = e - (origin_e + gx * sq_size)
        local_n = n - (origin_n + gy * sq_size)
        q = (1 if local_e >= half else 0) + (2 if local_n >= half else 0)
        return gx, gy, q

    for i in range(1, len(osgb_points)):
        e1, n1 = osgb_points[i - 1]
        e2, n2 = osgb_points[i]
        dist = math.hypot(e2 - e1, n2 - n1)
        total_distance += dist

        gq1 = _grid_quadrant(e1, n1)
        gq2 = _grid_quadrant(e2, n2)

        if gq1 is not None and gq2 is not None:
            if gq1 == gq2:
                # Both points in same quadrant — full distance.
                key = gq1
                quadrant_dist[key] = quadrant_dist.get(key, 0.0) + dist
            else:
                # Different quadrants — split evenly.
                half_dist = dist / 2
                quadrant_dist[gq1] = quadrant_dist.get(gq1, 0.0) + half_dist
                quadrant_dist[gq2] = quadrant_dist.get(gq2, 0.0) + half_dist
        elif gq1 is not None:
            quadrant_dist[gq1] = quadrant_dist.get(gq1, 0.0) + dist
        elif gq2 is not None:
            quadrant_dist[gq2] = quadrant_dist.get(gq2, 0.0) + dist

    # Apply threshold to determine visited quadrants per square.
    quadrant_coverage: dict[tuple[int, int], set[int]] = {}
    for (gx, gy, q), d in quadrant_dist.items():
        if d >= threshold:
            key = (gx, gy)
            if key not in quadrant_coverage:
                quadrant_coverage[key] = set()
            quadrant_coverage[key].add(q)

    return WalkResult(
        name=name,
        date=date,
        total_distance=total_distance,
        track_points=latlon_points,
        quadrant_coverage=quadrant_coverage,
    )
