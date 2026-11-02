"""Coordinate file route generator — read route from JSON or CSV files."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from keep_data_sim.config.schema import RouteConfig
from keep_data_sim.route.base import RouteGenerator
from keep_data_sim.route.noise import apply_gps_noise, smooth_coords
from keep_data_sim.utils.geo import haversine


class CoordFileRouteGenerator(RouteGenerator):
    """Generate a route by reading coordinates from a JSON or CSV file.

    JSON format:
        [{"lat": 39.9, "lon": 116.4}, ...]
        or
        [[39.9, 116.4], ...]

    CSV format (with or without header):
        lat,lon
        39.9,116.4
        ...
    """

    def generate(
        self,
        config: RouteConfig,
        distance_m: float,
        rng: np.random.Generator,
    ) -> list[tuple[float, float]]:
        if not config.import_file:
            raise ValueError("coord_file route requires --import-file")

        path = Path(config.import_file)
        suffix = path.suffix.lower()

        if suffix == ".json":
            coords = self._read_json(path)
        elif suffix == ".csv":
            coords = self._read_csv(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix} (use .json or .csv)")

        if len(coords) < 2:
            raise ValueError(f"File contains fewer than 2 coordinate points: {config.import_file}")

        coords = self._interpolate(coords, config.point_spacing_m)
        coords = self._scale_to_distance(coords, distance_m)
        coords = apply_gps_noise(coords, config, rng)
        coords = smooth_coords(coords)
        coords = self._trim_to_distance(coords, distance_m)
        return coords

    def _read_json(self, path: Path) -> list[tuple[float, float]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        coords: list[tuple[float, float]] = []
        for item in data:
            if isinstance(item, dict):
                lat = float(item.get("lat") or item.get("latitude", 0))
                lon = float(item.get("lon") or item.get("lng") or item.get("longitude", 0))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                lat, lon = float(item[0]), float(item[1])
            else:
                continue
            coords.append((lat, lon))
        return coords

    def _read_csv(self, path: Path) -> list[tuple[float, float]]:
        coords: list[tuple[float, float]] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            if first_row is None:
                return coords

            has_header = first_row and any(
                h.strip().lower() in ("lat", "latitude", "lon", "lng", "longitude")
                for h in first_row
            )

            if not has_header and first_row:
                try:
                    coords.append((float(first_row[0]), float(first_row[1])))
                except (ValueError, IndexError):
                    pass

            for row in reader:
                try:
                    coords.append((float(row[0]), float(row[1])))
                except (ValueError, IndexError):
                    continue
        return coords

    def _interpolate(
        self,
        coords: list[tuple[float, float]],
        spacing_m: float,
    ) -> list[tuple[float, float]]:
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
                result.append((
                    prev[0] + (curr[0] - prev[0]) * frac,
                    prev[1] + (curr[1] - prev[1]) * frac,
                ))
        return result

    def _scale_to_distance(
        self,
        coords: list[tuple[float, float]],
        target_distance_m: float,
    ) -> list[tuple[float, float]]:
        total = sum(
            haversine(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
            for i in range(len(coords) - 1)
        )
        if total == 0:
            return coords

        scale = target_distance_m / total
        center_lat = sum(c[0] for c in coords) / len(coords)
        center_lon = sum(c[1] for c in coords) / len(coords)

        return [
            (center_lat + (lat - center_lat) * scale, center_lon + (lon - center_lon) * scale)
            for lat, lon in coords
        ]

    def _trim_to_distance(
        self,
        coords: list[tuple[float, float]],
        target_distance_m: float,
        tolerance: float = 0.03,
    ) -> list[tuple[float, float]]:
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
