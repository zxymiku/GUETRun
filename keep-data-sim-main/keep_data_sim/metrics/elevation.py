"""Elevation profile generation."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import ElevationConfig


def generate_elevation_profile(
    n_points: int,
    config: ElevationConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate elevation values for each track point.

    Builds the profile from alternating climb/descent segments,
    guaranteeing total ascent ≈ total_gain_m.
    """
    if n_points == 0:
        return np.array([])

    if config.mode == "flat":
        return np.full(n_points, config.start_elevation_m)

    # Create control points: alternating climbs and descents
    # Each climb contributes equally to total gain
    n_hills = config.hill_count
    climb_per_hill = config.total_gain_m / n_hills

    # Control points as (fraction_of_route, elevation_offset)
    control_fracs = [0.0]
    control_elevs = [0.0]
    current_elev = 0.0

    for i in range(n_hills):
        # Climb phase
        climb_start = (2 * i + 0.5) / (2 * n_hills)
        climb_end = climb_start + 0.5 / (2 * n_hills)
        current_elev += climb_per_hill
        control_fracs.extend([climb_start, climb_end])
        control_elevs.extend([current_elev - climb_per_hill * 0.5, current_elev])

        # Descent phase
        descent_start = climb_end
        descent_end = descent_start + 0.5 / (2 * n_hills)
        current_elev -= climb_per_hill
        control_fracs.extend([descent_start + 0.5 / (4 * n_hills), descent_end])
        control_elevs.extend([current_elev + climb_per_hill * 0.5, current_elev])

    # End at 0
    control_fracs.append(1.0)
    control_elevs.append(0.0)

    # Sort by fraction and deduplicate
    pairs = sorted(zip(control_fracs, control_elevs))
    control_fracs = [p[0] for p in pairs]
    control_elevs = [p[1] for p in pairs]

    # Interpolate to n_points
    x = np.linspace(0, 1, n_points)
    elevation = np.interp(x, control_fracs, control_elevs)

    # Add small noise (keep it small to not significantly alter total ascent)
    elevation += rng.normal(0, 0.5, n_points)

    # Verify and rescale if needed
    diffs = np.diff(elevation)
    actual_ascent = float(np.sum(diffs[diffs > 0]))
    if actual_ascent > 0:
        scale = config.total_gain_m / actual_ascent
        # Only rescale the variation, not the base
        mean_elev = np.mean(elevation)
        elevation = mean_elev + (elevation - mean_elev) * scale

    # Shift to start at start_elevation_m
    elevation = elevation - elevation[0] + config.start_elevation_m

    return elevation
