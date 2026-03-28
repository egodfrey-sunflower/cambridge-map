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
