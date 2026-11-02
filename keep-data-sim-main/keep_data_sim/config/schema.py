"""Configuration schema — frozen dataclasses for all simulation parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RouteConfig:
    type: str = "circular"
    center_lat: float = 39.9042
    center_lon: float = 116.4074
    waypoints: tuple[tuple[float, float], ...] = ()
    radius_m: float = 2000.0
    out_distance_m: float = 5000.0
    bearing_deg: float | None = None
    point_spacing_m: float = 10.0
    gps_noise_sigma_m: float = 3.0
    gps_drift_m: float = 1.0
    import_file: str | None = None


@dataclass(frozen=True)
class PaceConfig:
    strategy: str = "constant"
    avg_pace_min_per_km: float = 5.5
    avg_speed_kmh: float = 25.0
    negative_split_ratio: float = 0.95
    positive_split_ratio: float = 1.05
    interval_fast_min_per_km: float = 4.5
    interval_slow_min_per_km: float = 6.5
    interval_fast_speed_kmh: float = 30.0
    interval_slow_speed_kmh: float = 18.0
    interval_fast_duration_s: float = 240.0
    interval_slow_duration_s: float = 120.0
    warmup_duration_s: float = 300.0
    warmup_speed_factor: float = 0.8


@dataclass(frozen=True)
class HeartRateConfig:
    resting_hr: int = 60
    max_hr: int = 190
    avg_hr: int = 145
    lag_seconds: float = 30.0
    noise_std: float = 3.0


@dataclass(frozen=True)
class ElevationConfig:
    total_gain_m: float = 50.0
    mode: str = "synthetic"
    hill_count: int = 3
    start_elevation_m: float = 50.0


@dataclass(frozen=True)
class CadenceConfig:
    running_avg_spm: int = 170
    running_range_spm: int = 10
    cycling_avg_rpm: int = 85
    cycling_range_rpm: int = 15


@dataclass(frozen=True)
class SimConfig:
    sport: str = "running"
    distance_m: float = 5000.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timezone_name: str = "Asia/Shanghai"
    treadmill: bool = False
    route: RouteConfig = field(default_factory=RouteConfig)
    pace: PaceConfig = field(default_factory=PaceConfig)
    heart_rate: HeartRateConfig = field(default_factory=HeartRateConfig)
    elevation: ElevationConfig = field(default_factory=ElevationConfig)
    cadence: CadenceConfig = field(default_factory=CadenceConfig)
    output_dir: str = "."
    output_formats: tuple[str, ...] = ("gpx", "fit")
    title: str = ""
    seed: int | None = None
