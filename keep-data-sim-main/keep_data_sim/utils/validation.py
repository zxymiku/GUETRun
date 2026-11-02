"""Configuration validation helpers."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from keep_data_sim.config.schema import SimConfig


def validate_config(config: SimConfig) -> None:
    """Raise ValueError if config contains impossible combinations."""
    if config.distance_m <= 0:
        raise ValueError(f"Distance must be positive, got {config.distance_m}")

    if config.sport not in ("running", "cycling"):
        raise ValueError(f"Unknown sport: {config.sport}")
    if config.treadmill and config.sport != "running":
        raise ValueError("Treadmill mode is only available for running")
    if config.treadmill and config.output_formats != ("fit",):
        raise ValueError("Treadmill mode supports FIT output only")
    try:
        ZoneInfo(config.timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {config.timezone_name}") from exc

    if config.route.type == "waypoint" and len(config.route.waypoints) < 2:
        raise ValueError("Waypoint route requires at least 2 waypoints")

    for route_type in ("gpx_import", "coord_file", "hand_drawn"):
        if config.route.type == route_type and not config.route.import_file:
            raise ValueError(f"{route_type} route requires --import-file")

    if config.route.type in ("gpx_import", "coord_file", "hand_drawn") and config.route.import_file:
        import os
        if not os.path.isfile(config.route.import_file):
            raise ValueError(f"Import file not found: {config.route.import_file}")

    if config.pace.strategy not in ("constant", "negative_split", "positive_split", "interval"):
        raise ValueError(f"Unknown pace strategy: {config.pace.strategy}")

    if config.pace.negative_split_ratio <= 0:
        raise ValueError("Negative split ratio must be positive")

    if config.pace.positive_split_ratio <= 0:
        raise ValueError("Positive split ratio must be positive")

    if config.pace.warmup_speed_factor <= 0:
        raise ValueError("Warmup speed factor must be positive")

    if config.route.point_spacing_m <= 0:
        raise ValueError("Point spacing must be positive")

    if config.route.gps_noise_sigma_m < 0:
        raise ValueError("GPS noise sigma must not be negative")

    if config.sport == "running":
        if not (2.0 < config.pace.avg_pace_min_per_km < 12.0):
            raise ValueError(f"Running pace out of range: {config.pace.avg_pace_min_per_km} min/km")
    else:
        if not (5.0 < config.pace.avg_speed_kmh < 60.0):
            raise ValueError(f"Cycling speed out of range: {config.pace.avg_speed_kmh} km/h")

    if config.heart_rate.resting_hr >= config.heart_rate.max_hr:
        raise ValueError("Resting HR must be less than max HR")

    if config.heart_rate.avg_hr < config.heart_rate.resting_hr or config.heart_rate.avg_hr > config.heart_rate.max_hr:
        raise ValueError("Avg HR must be between resting and max HR")

    for fmt in config.output_formats:
        if fmt not in ("gpx", "fit"):
            raise ValueError(f"Unknown output format: {fmt}")

    if config.route.type == "circular" and config.route.radius_m <= 0:
        raise ValueError("Circular route radius must be positive")

    if config.route.type == "out_and_back" and config.route.out_distance_m <= 0:
        raise ValueError("Out-and-back distance must be positive")
