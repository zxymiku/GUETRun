"""Geographic utility functions."""

from __future__ import annotations

import math


EARTH_RADIUS_M = 6_371_000.0
SEMICIRCLE_MAX = 2**31


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two WGS84 points."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return initial bearing in degrees from point 1 to point 2."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination(lat: float, lon: float, dist_m: float, brng_deg: float) -> tuple[float, float]:
    """Return (lat, lon) of a point at `dist_m` meters along `brng_deg` bearing."""
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    brng_r = math.radians(brng_deg)
    dist_ratio = dist_m / EARTH_RADIUS_M
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(dist_ratio)
        + math.cos(lat_r) * math.sin(dist_ratio) * math.cos(brng_r)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng_r) * math.sin(dist_ratio) * math.cos(lat_r),
        math.cos(dist_ratio) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def interpolate_point(
    lat1: float, lon1: float, lat2: float, lon2: float, fraction: float
) -> tuple[float, float]:
    """Linearly interpolate between two coordinates by fraction [0, 1]."""
    return lat1 + (lat2 - lat1) * fraction, lon1 + (lon2 - lon1) * fraction


def meters_to_degrees_lat(meters: float) -> float:
    """Convert meters to degrees of latitude (approximate)."""
    return meters / (EARTH_RADIUS_M * math.pi / 180)


def meters_to_degrees_lon(meters: float, lat: float) -> float:
    """Convert meters to degrees of longitude at given latitude (approximate)."""
    return meters / (EARTH_RADIUS_M * math.pi / 180 * math.cos(math.radians(lat)))


def degrees_to_semicircles(degrees: float) -> int:
    """Convert WGS84 degrees to Garmin semicircles."""
    return int(round(degrees * SEMICIRCLE_MAX / 180))


def semicircles_to_degrees(semicircles: int) -> float:
    """Convert Garmin semicircles to WGS84 degrees."""
    return semicircles * 180 / SEMICIRCLE_MAX
