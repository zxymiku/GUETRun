"""Time-based treadmill activity simulation without a geographic route."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.types import TrackPoint
from keep_data_sim.metrics.pace_strategy import create_pace_strategy
from keep_data_sim.metrics.treadmill import (
    generate_treadmill_cadence_curve,
    generate_treadmill_heart_rate_curve,
    generate_treadmill_speed_curve,
    integrate_treadmill_distance,
)

SAMPLE_INTERVAL_SECONDS = 1.0


def generate_treadmill_points(
    config: SimConfig,
    rng: np.random.Generator,
) -> list[TrackPoint]:
    """Generate a one-second treadmill timeline that ends at the exact distance."""
    pace_strategy = create_pace_strategy(config.pace, config.sport)
    distances = [0.0]
    elapsed_times = [0.0]
    speeds: list[float] = []

    distance = 0.0
    elapsed = 0.0
    while distance < config.distance_m:
        speed = pace_strategy.speed_at(distance, config.distance_m, elapsed)
        if speed <= 0:
            raise ValueError("Treadmill speed must be positive")

        speeds.append(speed)
        remaining_time = (config.distance_m - distance) / speed
        if remaining_time <= SAMPLE_INTERVAL_SECONDS + 1e-9:
            interval = remaining_time
            distance = config.distance_m
        else:
            interval = SAMPLE_INTERVAL_SECONDS
            distance += speed * interval
        elapsed += interval
        distances.append(distance)
        elapsed_times.append(elapsed)

    speeds.append(
        pace_strategy.speed_at(config.distance_m, config.distance_m, elapsed)
    )

    elapsed_curve = np.asarray(elapsed_times, dtype=float)
    base_speed_curve = np.asarray(speeds, dtype=float)
    speed_curve = generate_treadmill_speed_curve(
        base_speed_curve,
        elapsed_curve,
        config.distance_m,
        rng,
    )
    distance_curve = integrate_treadmill_distance(
        speed_curve,
        elapsed_curve,
        config.distance_m,
    )
    unix_timestamps = config.start_time.timestamp() + elapsed_curve
    heart_rates = generate_treadmill_heart_rate_curve(
        elapsed_curve,
        config.heart_rate,
        rng,
    )
    cadences = generate_treadmill_cadence_curve(
        speed_curve,
        config.cadence,
        rng,
    )

    return [
        TrackPoint(
            latitude=config.route.center_lat,
            longitude=config.route.center_lon,
            elevation=config.elevation.start_elevation_m,
            timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
            speed=float(speed),
            heart_rate=int(heart_rate),
            cadence=int(cadence),
            distance=float(point_distance),
        )
        for point_distance, timestamp, speed, heart_rate, cadence in zip(
            distance_curve,
            unix_timestamps,
            speed_curve,
            heart_rates,
            cadences,
        )
    ]
