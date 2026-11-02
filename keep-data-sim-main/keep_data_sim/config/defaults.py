"""Default configurations per sport type."""

from __future__ import annotations

from keep_data_sim.config.schema import (
    CadenceConfig,
    ElevationConfig,
    HeartRateConfig,
    PaceConfig,
    RouteConfig,
    SimConfig,
)


def running_config(**overrides) -> SimConfig:
    """Default running simulation config."""
    defaults = dict(
        sport="running",
        distance_m=5000.0,
        pace=PaceConfig(
            strategy="constant",
            avg_pace_min_per_km=5.5,
        ),
        heart_rate=HeartRateConfig(
            avg_hr=145,
            resting_hr=60,
            max_hr=190,
        ),
        cadence=CadenceConfig(
            running_avg_spm=170,
            running_range_spm=10,
        ),
        elevation=ElevationConfig(
            total_gain_m=50.0,
            hill_count=3,
        ),
    )
    defaults.update(overrides)
    return SimConfig(**defaults)


def cycling_config(**overrides) -> SimConfig:
    """Default cycling simulation config."""
    defaults = dict(
        sport="cycling",
        distance_m=20000.0,
        pace=PaceConfig(
            strategy="constant",
            avg_speed_kmh=25.0,
        ),
        heart_rate=HeartRateConfig(
            avg_hr=135,
            resting_hr=60,
            max_hr=185,
        ),
        cadence=CadenceConfig(
            cycling_avg_rpm=85,
            cycling_range_rpm=15,
        ),
        elevation=ElevationConfig(
            total_gain_m=100.0,
            hill_count=5,
        ),
    )
    defaults.update(overrides)
    return SimConfig(**defaults)
