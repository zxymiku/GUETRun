"""Circular/loop route generator."""

from __future__ import annotations

import math

import numpy as np

from keep_data_sim.config.schema import RouteConfig
from keep_data_sim.route.base import RouteGenerator
from keep_data_sim.route.noise import apply_gps_noise, smooth_coords
from keep_data_sim.utils.geo import destination, haversine


class CircularRouteGenerator(RouteGenerator):
    """Generate a loop route starting and ending near the center point."""

    def generate(
        self,
        config: RouteConfig,
        distance_m: float,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        center_lat = config.center_lat
        center_lon = config.center_lon
        radius_m = config.radius_m

        # Number of segments around the loop
        num_segments = max(12, int(distance_m / 50))
        angle_step = 360.0 / num_segments

        # Generate base circular route with radius variation
        coords: list[tuple[float, float]] = []
        for i in range(num_segments):
            angle = i * angle_step
            # Vary radius ±15% per segment
            r = radius_m * (1.0 + rng.uniform(-0.15, 0.15))
            # Add angular jitter ±3 degrees
            jittered_angle = angle + rng.uniform(-3, 3)
            lat, lon = destination(center_lat, center_lon, r, jittered_angle)
            coords.append((lat, lon))

        # Close the loop
        coords.append(coords[0])

        # Interpolate to achieve target point spacing
        coords = self._interpolate_spacing(coords, config.point_spacing_m)

        # Scale route to match target distance
        coords = self._scale_to_distance(coords, center_lat, center_lon, distance_m, rng)

        # Apply GPS noise
        coords = apply_gps_noise(coords, config, rng)
        coords = smooth_coords(coords)

        # Final distance adjustment after noise (trim or extend points)
        coords = self._trim_to_distance(coords, distance_m)

        return coords

    def _interpolate_spacing(
        self,
        coords: list[tuple[float, float]],
        spacing_m: float,
    ) -> list[tuple[float, float]]:
        """Insert intermediate points to achieve target spacing."""
        result: list[tuple[float, float]] = [coords[0]]

        for i in range(1, len(coords)):
            prev = result[-1]
            curr = coords[i]
            dist = haversine(prev[0], prev[1], curr[0], curr[1])

            if dist <= spacing_m:
                result.append(curr)
                continue

            n_points = max(2, int(dist / spacing_m))
            for j in range(1, n_points + 1):
                frac = j / n_points
                interp_lat = prev[0] + (curr[0] - prev[0]) * frac
                interp_lon = prev[1] + (curr[1] - prev[1]) * frac
                result.append((interp_lat, interp_lon))

        return result

    def _trim_to_distance(
        self,
        coords: list[tuple[float, float]],
        target_distance_m: float,
        tolerance: float = 0.03,
    ) -> list[tuple[float, float]]:
        """Trim route to match target distance within tolerance."""
        # Compute cumulative distances
        cum_dist = [0.0]
        for i in range(1, len(coords)):
            d = haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
            cum_dist.append(cum_dist[-1] + d)

        total = cum_dist[-1]
        if abs(total - target_distance_m) / target_distance_m < tolerance:
            return coords

        # Find the point where we reach target distance
        for i in range(1, len(cum_dist)):
            if cum_dist[i] >= target_distance_m:
                # Interpolate exact end point
                overshoot = cum_dist[i] - target_distance_m
                seg_len = cum_dist[i] - cum_dist[i - 1]
                if seg_len > 0:
                    frac = 1.0 - overshoot / seg_len
                    end_lat = coords[i - 1][0] + (coords[i][0] - coords[i - 1][0]) * frac
                    end_lon = coords[i - 1][1] + (coords[i][1] - coords[i - 1][1]) * frac
                    return coords[:i] + [(end_lat, end_lon)]

        return coords

    def _scale_to_distance(
        self,
        coords: list[tuple[float, float]],
        center_lat: float,
        center_lon: float,
        target_distance_m: float,
        rng: np.random.Generator,
        max_iterations: int = 10,
    ) -> list[tuple[float, float]]:
        """Scale route radius to match target distance within 5% tolerance."""
        for _ in range(max_iterations):
            total_dist = sum(
                haversine(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
                for i in range(len(coords) - 1)
            )

            if abs(total_dist - target_distance_m) / target_distance_m < 0.05:
                break

            # Scale all points relative to center
            scale = target_distance_m / total_dist
            scaled: list[tuple[float, float]] = []
            for lat, lon in coords:
                # Move point away/toward center by scale factor
                dlat = lat - center_lat
                dlon = lon - center_lon
                scaled.append((center_lat + dlat * scale, center_lon + dlon * scale))
            coords = scaled

        return coords
