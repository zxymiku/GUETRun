"""Main simulator orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.registry import get_exporter, get_route_generator
from keep_data_sim.core.treadmill import generate_treadmill_points
from keep_data_sim.core.types import TrackPoint
from keep_data_sim.metrics.cadence import generate_cadence_curve
from keep_data_sim.metrics.elevation import generate_elevation_profile
from keep_data_sim.metrics.heart_rate import generate_heart_rate_curve
from keep_data_sim.metrics.pace_strategy import create_pace_strategy
from keep_data_sim.utils.geo import haversine
from keep_data_sim.utils.validation import validate_config

logger = logging.getLogger(__name__)


class Simulator:
    """Orchestrate the full simulation pipeline: config -> track data -> files."""

    def __init__(self, config: SimConfig) -> None:
        validate_config(config)
        self._config = config
        self._rng = np.random.default_rng(config.seed)

    def run(self) -> list[Path]:
        """Execute simulation and return paths to generated files."""
        points = self.simulate()
        return self._export(points)

    def run_with_summary(self) -> tuple[list[Path], dict]:
        """Execute simulation and return generated paths plus a matching summary."""
        points = self.simulate()
        return self._export(points), self._summarize(points)

    def simulate(self) -> list[TrackPoint]:
        """Generate track points without exporting them."""
        if self._config.treadmill:
            return generate_treadmill_points(self._config, self._rng)

        coords = self._generate_route()
        return self._apply_metrics(coords)

    def dry_run(self) -> dict:
        """Run simulation without writing files. Return summary dict."""
        return self._summarize(self.simulate())

    def _generate_route(self) -> list[tuple[float, float]]:
        """Generate the route coordinates."""
        gen_cls = get_route_generator(self._config.route.type)
        generator = gen_cls()
        coords = generator.generate(
            self._config.route,
            self._config.distance_m,
            self._rng,
        )
        logger.info("Generated route with %d points", len(coords))
        return coords

    def _apply_metrics(self, coords: list[tuple[float, float]]) -> list[TrackPoint]:
        """Apply pace, HR, elevation, and cadence to route coordinates."""
        if not coords:
            return []

        config = self._config
        pace_strategy = create_pace_strategy(config.pace, config.sport)

        # Compute cumulative distances
        distances = [0.0]
        for i in range(1, len(coords)):
            d = haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
            distances.append(distances[-1] + d)

        total_distance = distances[-1]

        # Compute speeds and timestamps
        speeds = np.zeros(len(coords))
        timestamps = np.zeros(len(coords))
        start_time = config.start_time.timestamp()
        timestamps[0] = start_time
        elapsed = 0.0

        for i in range(1, len(coords)):
            seg_dist = distances[i] - distances[i - 1]
            speed = pace_strategy.speed_at(distances[i], total_distance, elapsed)
            speeds[i] = speed
            if speed > 0:
                seg_time = seg_dist / speed
            else:
                seg_time = 1.0
            elapsed += seg_time
            timestamps[i] = start_time + elapsed

        # Set first point speed to second point's speed
        if len(speeds) > 1:
            speeds[0] = speeds[1]

        # Generate elevation
        elevations = generate_elevation_profile(len(coords), config.elevation, self._rng)

        # Generate heart rate
        hr_values = generate_heart_rate_curve(speeds, timestamps, config.heart_rate, self._rng)

        # Generate cadence
        cadence_values = generate_cadence_curve(speeds, config.sport, config.cadence, self._rng)

        # Assemble TrackPoints
        points: list[TrackPoint] = []
        for i in range(len(coords)):
            points.append(TrackPoint(
                latitude=coords[i][0],
                longitude=coords[i][1],
                elevation=float(elevations[i]),
                timestamp=datetime.fromtimestamp(timestamps[i], tz=timezone.utc),
                speed=float(speeds[i]),
                heart_rate=int(hr_values[i]),
                cadence=int(cadence_values[i]),
                distance=distances[i],
            ))

        logger.info("Applied metrics to %d track points", len(points))
        return points

    def _export(self, points: list[TrackPoint]) -> list[Path]:
        """Export track points to all requested formats."""
        # Lazy import exporters to register them
        import keep_data_sim.export.gpx_exporter  # noqa: F401
        import keep_data_sim.export.fit_exporter  # noqa: F401

        output_dir = Path(self._config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        title = self._config.title or self._default_title()
        paths: list[Path] = []

        for fmt in self._config.output_formats:
            exporter_cls = get_exporter(fmt)
            exporter = exporter_cls()
            path = exporter.export(points, self._config, output_dir, title)
            paths.append(path)
            logger.info("Exported %s: %s", fmt.upper(), path)

        return paths

    def _summarize(self, points: list[TrackPoint]) -> dict:
        """Return a summary dict of the simulated workout."""
        if not points:
            return {"error": "No points generated"}

        total_dist = points[-1].distance
        duration_s = (points[-1].timestamp - points[0].timestamp).total_seconds()
        avg_speed = total_dist / duration_s if duration_s > 0 else 0
        avg_hr = sum(p.heart_rate for p in points) / len(points)
        avg_cadence = sum(p.cadence for p in points) / len(points)

        # Elevation gain
        elevation_gain = 0.0
        for i in range(1, len(points)):
            diff = points[i].elevation - points[i - 1].elevation
            if diff > 0:
                elevation_gain += diff

        if self._config.sport == "running":
            avg_pace = (duration_s / 60) / (total_dist / 1000) if total_dist > 0 else 0
            pace_seconds = int(round(avg_pace * 60))
            pace_minutes, remaining_seconds = divmod(pace_seconds, 60)
            pace_str = f"{pace_minutes}:{remaining_seconds:02d} /km"
        else:
            avg_kmh = avg_speed * 3.6
            pace_str = f"{avg_kmh:.1f} km/h"

        return {
            "sport": self._config.sport,
            "mode": "treadmill" if self._config.treadmill else "outdoor",
            "distance_m": round(total_dist, 1),
            "duration_s": round(duration_s, 1),
            "pace": pace_str,
            "avg_hr": round(avg_hr),
            "avg_cadence": round(avg_cadence),
            "elevation_gain_m": round(elevation_gain, 1),
            "num_points": len(points),
            "start_time": points[0].timestamp.isoformat(),
        }

    def _default_title(self) -> str:
        """Generate a default activity title."""
        sport_name = "Run" if self._config.sport == "running" else "Ride"
        date_str = self._config.start_time.strftime("%Y-%m-%d")
        return f"{sport_name} {date_str}"
