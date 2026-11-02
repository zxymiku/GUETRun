"""Out-and-back route generator."""

from __future__ import annotations

import numpy as np

from keep_data_sim.config.schema import RouteConfig
from keep_data_sim.route.base import RouteGenerator
from keep_data_sim.route.noise import apply_gps_noise, smooth_coords
from keep_data_sim.utils.geo import destination, haversine


class OutAndBackRouteGenerator(RouteGenerator):
    """Generate an out-and-back route from the start point."""

    def generate(
        self,
        config: RouteConfig,
        distance_m: float,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        start_lat = config.center_lat
        start_lon = config.center_lon
        half_dist = distance_m / 2

        # Choose bearing
        brng = config.bearing_deg if config.bearing_deg is not None else rng.uniform(0, 360)

        # Generate outbound path
        outbound = self._generate_leg(start_lat, start_lon, half_dist, brng, config, rng)

        # Generate return path (reverse bearing with slight offset)
        return_brng = (brng + 180 + rng.uniform(-5, 5)) % 360
        end_lat, end_lon = outbound[-1]
        return_leg = self._generate_leg(end_lat, end_lon, half_dist, return_brng, config, rng)

        # Combine: outbound + return (skip first point of return to avoid duplicate)
        coords = outbound + return_leg[1:]

        # Apply GPS noise
        coords = apply_gps_noise(coords, config, rng)
        coords = smooth_coords(coords)

        # Trim to exact target distance
        coords = self._trim_to_distance(coords, distance_m)

        return coords

    def _generate_leg(
        self,
        start_lat: float,
        start_lon: float,
        distance_m: float,
        brng_deg: float,
        config: RouteConfig,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        """Generate one leg of an out-and-back route."""
        spacing = config.point_spacing_m
        n_points = max(2, int(distance_m / spacing))

        coords: list[tuple[float, float]] = [(start_lat, start_lon)]

        for i in range(1, n_points + 1):
            dist_so_far = i * spacing
            lateral_offset = rng.normal(0, 2)
            current_brng = brng_deg + lateral_offset

            lat, lon = destination(start_lat, start_lon, dist_so_far, current_brng)
            coords.append((lat, lon))

        return coords

    def _trim_to_distance(
        self,
        coords: list[tuple[float, float]],
        target_distance_m: float,
        tolerance: float = 0.03,
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
