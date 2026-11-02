"""Cadence generation correlated with speed."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import CadenceConfig


def generate_cadence_curve(
    speed_curve: np.ndarray,
    sport: str,
    config: CadenceConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate cadence values correlated with speed."""
    if len(speed_curve) == 0:
        return np.array([], dtype=int)

    if sport == "running":
        avg = config.running_avg_spm
        span = config.running_range_spm
    else:
        avg = config.cycling_avg_rpm
        span = config.cycling_range_rpm

    # Normalize speed to [0, 1]
    min_speed = speed_curve.min()
    max_speed = speed_curve.max()
    if max_speed > min_speed:
        norm_speed = (speed_curve - min_speed) / (max_speed - min_speed)
    else:
        norm_speed = np.full_like(speed_curve, 0.5)

    # Cadence increases with speed, centered around avg
    cadence = avg - span / 2 + norm_speed * span

    # Add small random variation
    cadence += rng.normal(0, span * 0.1, len(cadence))

    # Clamp to physiological range
    if sport == "running":
        cadence = np.clip(cadence, 140, 200)
    else:
        cadence = np.clip(cadence, 50, 130)

    return np.round(cadence).astype(int)
