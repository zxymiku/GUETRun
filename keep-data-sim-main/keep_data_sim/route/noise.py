"""GPS noise and drift simulation."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import RouteConfig
from keep_data_sim.utils.geo import meters_to_degrees_lat, meters_to_degrees_lon


def apply_gps_noise(
    coords: list[tuple[float, float]],
    config: RouteConfig,
    rng: np.random.Generator,
) -> list[tuple[float, float]]:
    """Add realistic GPS jitter, drift, and occasional spikes to coordinates."""
    n = len(coords)
    if n == 0:
        return coords

    sigma_deg_lat = meters_to_degrees_lat(config.gps_noise_sigma_m)
    drift_deg_lat = meters_to_degrees_lat(config.gps_drift_m)

    noisy: list[tuple[float, float]] = []

    # Cumulative drift as random walk
    drift_lat = 0.0
    drift_lon = 0.0

    for i, (lat, lon) in enumerate(coords):
        sigma_deg_lon = meters_to_degrees_lon(config.gps_noise_sigma_m, lat)
        drift_deg_lon = meters_to_degrees_lon(config.gps_drift_m, lat)

        # Update drift (random walk)
        drift_lat += rng.normal(0, drift_deg_lat)
        drift_lon += rng.normal(0, drift_deg_lon)

        # Jitter
        jitter_lat = rng.normal(0, sigma_deg_lat)
        jitter_lon = rng.normal(0, sigma_deg_lon)

        # Spike (1-2% of points)
        spike_lat, spike_lon = 0.0, 0.0
        if rng.random() < 0.015:
            spike_m = rng.uniform(10, 30)
            spike_lat = meters_to_degrees_lat(spike_m) * rng.choice([-1, 1])
            spike_lon = meters_to_degrees_lon(spike_m, lat) * rng.choice([-1, 1])

        noisy.append((
            lat + jitter_lat + drift_lat + spike_lat,
            lon + jitter_lon + drift_lon + spike_lon,
        ))

    return noisy


def smooth_coords(coords: list[tuple[float, float]], window: int = 5) -> list[tuple[float, float]]:
    """Light smoothing to prevent unrealistic jumps after noise addition."""
    if len(coords) <= window:
        return coords

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]

    kernel_size = window // 2
    smoothed = []
    for i in range(len(coords)):
        start = max(0, i - kernel_size)
        end = min(len(coords), i + kernel_size + 1)
        smoothed.append((
            sum(lats[start:end]) / (end - start),
            sum(lons[start:end]) / (end - start),
        ))

    return smoothed
