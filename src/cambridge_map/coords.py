"""Coordinate conversion helpers: WGS84 (lat/lon) <-> OS National Grid (EPSG:27700)."""

from pyproj import Transformer

# Lazily initialised transformers (thread-safe after creation).
_to_osgb: Transformer | None = None
_to_wgs84: Transformer | None = None


def _get_to_osgb() -> Transformer:
    global _to_osgb
    if _to_osgb is None:
        _to_osgb = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    return _to_osgb


def _get_to_wgs84() -> Transformer:
    global _to_wgs84
    if _to_wgs84 is None:
        _to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    return _to_wgs84


def latlon_to_osgb(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 lat/lon to OS National Grid easting/northing."""
    easting, northing = _get_to_osgb().transform(lon, lat)
    return easting, northing


def osgb_to_latlon(easting: float, northing: float) -> tuple[float, float]:
    """Convert OS National Grid easting/northing to WGS84 lat/lon."""
    lon, lat = _get_to_wgs84().transform(easting, northing)
    return lat, lon


# 500km grid letters indexed by (easting // 500_000, northing // 500_000).
_GRID_500 = {(0, 0): "S", (1, 0): "T", (0, 1): "N", (1, 1): "O", (0, 2): "H"}
# 100km sub-grid letters (A-Z, no I), top-left = A.
_GRID_100 = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def osgb_to_gridref(easting: float, northing: float) -> str:
    """Convert OS easting/northing to a 4-figure grid reference (e.g. 'TL3748')."""
    e500 = int(easting) // 500_000
    n500 = int(northing) // 500_000
    first = _GRID_500[(e500, n500)]

    e100 = (int(easting) % 500_000) // 100_000
    n100 = (int(northing) % 500_000) // 100_000
    second = _GRID_100[(4 - n100) * 5 + e100]

    e_km = (int(easting) % 100_000) // 1000
    n_km = (int(northing) % 100_000) // 1000
    return f"{first}{second}{e_km:02d}{n_km:02d}"
