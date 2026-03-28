"""Typed configuration loaded from YAML via Pydantic."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, PositiveFloat, PositiveInt


class GridConfig(BaseModel):
    origin_easting: int
    origin_northing: int
    squares_x: PositiveInt
    squares_y: PositiveInt
    square_size: PositiveInt


class VisitConfig(BaseModel):
    min_contiguous_distance_in_square_per_walk: PositiveFloat
    min_contiguous_distance_in_quadrant_per_walk: PositiveFloat


class Config(BaseModel):
    grid: GridConfig
    visit: VisitConfig


def load_config(config_path: Path) -> Config:
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    return Config.model_validate(raw)
