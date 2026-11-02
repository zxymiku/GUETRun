"""Waypoint-based route generator."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import RouteConfig
from keep_data_sim.route.base import RouteGenerator
from keep_data_sim.route.noise import apply_gps_noise, smooth_coords
from keep_data_sim.utils.geo import haversine


class WaypointRouteGenerator(RouteGenerator):
    """Generate a route passing through specified waypoints."""

    def generate(
        self,
        config: RouteConfig,
        distance_m: float,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        waypoints = list(config.waypoints)
        if len(waypoints) < 2:
            raise ValueError("Waypoint route requires at least 2 waypoints")

        # Interpolate between consecutive waypoints
        coords: list[tuple[float, float]] = [waypoints[0]]

        for i in range(len(waypoints) - 1):
            seg_start = waypoints[i]
            seg_end = waypoints[i + 1]
            seg_coords = self._interpolate_segment(
                seg_start, seg_end, config.point_spacing_m, rng
            )
            # Skip first point (duplicate of previous segment end)
            coords.extend(seg_coords[1:])

        # Optionally close the loop back to start
        first_to_last = haversine(coords[-1][0], coords[-1][1], coords[0][0], coords[0][1])
        if first_to_last > 50:  # More than 50m gap, close it
            close_coords = self._interpolate_segment(
                (coords[-1][0], coords[-1][1]),
                (coords[0][0], coords[0][1]),
                config.point_spacing_m,
                rng,
            )
            coords.extend(close_coords[1:])

        # Apply GPS noise
        coords = apply_gps_noise(coords, config, rng)
        coords = smooth_coords(coords)

        # Trim to target distance
        coords = self._trim_to_distance(coords, distance_m)

        return coords

    def _trim_to_distance(
        self,
        coords: list[tuple[float, float]],
        target_distance_m: float,
        tolerance: float = 0.05,
    ) -> list[tuple[float, float]]:
        """Trim route to match target distance within tolerance."""
        cum_dist = [0.0]
        for i in range(1, len(coords)):
            d = haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
            cum_dist.append(cum_dist[-1] + d)

        total = cum_dist[-1]
        if abs(total - target_distance_m) / target_distance_m < tolerance:
            return coords

        for i in range(1, len(cum_dist)):
            if cum_dist[i] >= target_distance_m:
                overshoot = cum_dist[i] - target_distance_m
                seg_len = cum_dist[i] - cum_dist[i - 1]
                if seg_len > 0:
                    frac = 1.0 - overshoot / seg_len
                    end_lat = coords[i - 1][0] + (coords[i][0] - coords[i - 1][0]) * frac
                    end_lon = coords[i - 1][1] + (coords[i][1] - coords[i - 1][1]) * frac
                    return coords[:i] + [(end_lat, end_lon)]

        return coords

    def _interpolate_segment(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        spacing_m: float,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        """Interpolate points between two waypoints with slight curvature."""
        dist = haversine(start[0], start[1], end[0], end[1])
        n_points = max(2, int(dist / spacing_m))

        coords: list[tuple[float, float]] = []
        # Perpendicular offset for curvature
        offset = rng.uniform(-0.0002, 0.0002)

        for i in range(n_points + 1):
            t = i / n_points
            # Bezier-like curve with control point offset
            lat = start[0] + (end[0] - start[0]) * t + offset * 4 * t * (1 - t)
            lon = start[1] + (end[1] - start[1]) * t + offset * 4 * t * (1 - t)
            coords.append((lat, lon))

        return coords
