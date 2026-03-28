"""Orchestrator: runs Phase 1 + Phase 2, renders the site."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .ascii_grid import render_ascii
from .combine import combine
from .config import load_config
from .coords import osgb_to_latlon
from .parse_gpx import parse_gpx

PROJECT_ROOT = Path.cwd()


def build(config_path: Path | None = None) -> None:
    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    config = load_config(config_path)
    grid = config.grid

    # Phase 1: parse all GPX files.
    gpx_dir = PROJECT_ROOT / "gpx"
    gpx_files = sorted(gpx_dir.glob("*.gpx"))

    walk_results = []
    for gpx_path in gpx_files:
        print(f"  Parsing {gpx_path.name}...")
        walk_results.append(parse_gpx(gpx_path, config))

    # Phase 2: combine.
    combined = combine(walk_results)

    # ASCII output for quick check.
    print()
    print(render_ascii(combined, grid.squares_x, grid.squares_y))
    print()

    # Build JSON data for the frontend.
    origin_e = grid.origin_easting
    origin_n = grid.origin_northing
    sq_size = grid.square_size
    squares_x = grid.squares_x
    squares_y = grid.squares_y

    # Grid squares with lat/lon corners.
    grid_squares = []
    for gy in range(squares_y):
        for gx in range(squares_x):
            e0 = origin_e + gx * sq_size
            e1 = origin_e + (gx + 1) * sq_size
            n0 = origin_n + gy * sq_size
            n1 = origin_n + (gy + 1) * sq_size
            # Convert all 4 corners independently so the polygon
            # faithfully represents the OS grid square on a Mercator map.
            sw_lat, sw_lon = osgb_to_latlon(e0, n0)
            se_lat, se_lon = osgb_to_latlon(e1, n0)
            ne_lat, ne_lon = osgb_to_latlon(e1, n1)
            nw_lat, nw_lon = osgb_to_latlon(e0, n1)
            state = combined.grid.get((gx, gy))
            grid_squares.append(
                {
                    "gx": gx,
                    "gy": gy,
                    "corners": [
                        [sw_lat, sw_lon],
                        [se_lat, se_lon],
                        [ne_lat, ne_lon],
                        [nw_lat, nw_lon],
                    ],
                    "quadrants_visited": len(state.quadrants_visited) if state else 0,
                    "walks": state.walks if state else [],
                }
            )

    # Grid overall bounds.
    sw_lat, sw_lon = osgb_to_latlon(origin_e, origin_n)
    ne_lat, ne_lon = osgb_to_latlon(
        origin_e + squares_x * sq_size, origin_n + squares_y * sq_size
    )

    # Walk data for frontend.
    walks_json = []
    for w in sorted(walk_results, key=lambda w: w.date or "", reverse=True):
        walks_json.append(
            {
                "name": w.name,
                "date": w.date,
                "distance": round(w.total_distance, 1),
                "track_points": w.track_points,
            }
        )

    data = {
        "grid_squares": grid_squares,
        "grid_bounds": {
            "sw_lat": sw_lat,
            "sw_lon": sw_lon,
            "ne_lat": ne_lat,
            "ne_lon": ne_lon,
        },
        "walks": walks_json,
    }

    data_json = json.dumps(data)

    # Render HTML.
    env = Environment(loader=FileSystemLoader(str(PROJECT_ROOT / "templates")))
    template = env.get_template("index.html")
    html = template.render(data_json=data_json)

    # Write output.
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "index.html").write_text(html)

    # Copy static assets.
    static_dir = PROJECT_ROOT / "static"
    for f in static_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, output_dir / f.name)

    print(f"Site built in {output_dir}/")


def main() -> None:
    build()
