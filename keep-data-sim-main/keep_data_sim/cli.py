"""Command line interface for Keep Data Simulator."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from keep_data_sim.config.schema import (
    CadenceConfig,
    ElevationConfig,
    HeartRateConfig,
    PaceConfig,
    RouteConfig,
    SimConfig,
)
from keep_data_sim.core.simulator import Simulator
from keep_data_sim.fit_binary_shift import shift_fit_binary_start_time
from keep_data_sim.fit_shift import parse_local_start_time, shift_fit_start_time

ROUTE_TYPES = ("circular", "out_and_back", "waypoint", "gpx_import", "coord_file", "hand_drawn")
PACE_STRATEGIES = ("constant", "negative_split", "positive_split", "interval")
OUTPUT_FORMATS = ("gpx", "fit")


def parse_pace(pace_str: str) -> float:
    """Parse a pace string like ``5:30`` into minutes per kilometer."""
    parts = pace_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) + int(parts[1]) / 60
    return float(pace_str)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="keep-data-sim",
        description="Generate realistic GPX/FIT workout files for running and cycling simulations",
    )

    basic = parser.add_argument_group("Basic")
    basic.add_argument("--sport", choices=["running", "cycling"], default="running")
    basic.add_argument("--distance", type=float, default=5000.0, help="Distance in meters")
    basic.add_argument("--pace", type=str, default="5:30", help="Pace as M:SS per km (running)")
    basic.add_argument("--speed", type=float, default=None, help="Speed in km/h (cycling)")
    basic.add_argument("--start-time", type=str, default=None, help="Start time in UTC (YYYY-MM-DD HH:MM:SS)")
    basic.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="IANA timezone used for FIT local time (default: Asia/Shanghai)",
    )
    basic.add_argument(
        "--treadmill",
        action="store_true",
        help="Generate a GPS-free Garmin treadmill running FIT file",
    )
    basic.add_argument("--start-lat", type=float, default=39.9042, help="Start latitude")
    basic.add_argument("--start-lon", type=float, default=116.4074, help="Start longitude")
    basic.add_argument("--title", type=str, default="", help="Activity title")
    basic.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")

    route = parser.add_argument_group("Route")
    route.add_argument("--route-type", choices=ROUTE_TYPES, default="circular")
    route.add_argument("--route-radius", type=float, default=2000.0, help="Circular route radius (m)")
    route.add_argument("--out-distance", type=float, default=5000.0, help="Out-and-back one-way distance (m)")
    route.add_argument("--bearing", type=float, default=None, help="Bearing for out-and-back (degrees)")
    route.add_argument("--waypoints", type=str, default=None, help="Waypoints as 'lat1,lon1;lat2,lon2;...'")
    route.add_argument("--point-spacing", type=float, default=10.0, help="GPS point spacing (m)")
    route.add_argument("--gps-noise", type=float, default=3.0, help="GPS noise sigma (m)")
    route.add_argument(
        "--import-file",
        type=str,
        default=None,
        help="Path to import file (GPX/JSON/CSV) for gpx_import, coord_file, or hand_drawn routes",
    )

    pace_group = parser.add_argument_group("Pace Strategy")
    pace_group.add_argument("--pace-strategy", choices=PACE_STRATEGIES, default="constant")
    pace_group.add_argument("--split-ratio", type=float, default=0.95, help="Split ratio for split strategies")
    pace_group.add_argument("--interval-fast", type=str, default="4:30", help="Fast interval pace (M:SS)")
    pace_group.add_argument("--interval-slow", type=str, default="6:30", help="Slow interval pace (M:SS)")
    pace_group.add_argument("--interval-fast-speed", type=float, default=30.0, help="Fast cycling speed (km/h)")
    pace_group.add_argument("--interval-slow-speed", type=float, default=18.0, help="Slow cycling speed (km/h)")
    pace_group.add_argument("--interval-fast-dur", type=float, default=240.0, help="Fast interval duration (s)")
    pace_group.add_argument("--interval-slow-dur", type=float, default=120.0, help="Slow interval duration (s)")
    pace_group.add_argument("--warmup-dur", type=float, default=300.0, help="Warmup duration (s)")
    pace_group.add_argument("--warmup-factor", type=float, default=0.8, help="Warmup speed factor (0-1)")

    heart_rate = parser.add_argument_group("Heart Rate")
    heart_rate.add_argument("--hr-resting", type=int, default=60)
    heart_rate.add_argument("--hr-avg", type=int, default=145)
    heart_rate.add_argument("--hr-max", type=int, default=190)
    heart_rate.add_argument("--hr-lag", type=float, default=30.0, help="HR response lag (seconds)")
    heart_rate.add_argument("--hr-noise", type=float, default=3.0, help="HR noise std (bpm)")

    elevation = parser.add_argument_group("Elevation")
    elevation.add_argument("--elevation-mode", choices=["synthetic", "flat"], default="synthetic")
    elevation.add_argument("--elevation-gain", type=float, default=50.0, help="Total elevation gain (m)")
    elevation.add_argument("--hill-count", type=int, default=3, help="Number of hills")
    elevation.add_argument("--start-elevation", type=float, default=50.0, help="Start elevation (m)")

    cadence = parser.add_argument_group("Cadence")
    cadence.add_argument("--cadence-avg", type=int, default=None, help="Average cadence (spm or rpm)")

    output = parser.add_argument_group("Output")
    output.add_argument("--output-dir", type=str, default=".", help="Output directory")
    output.add_argument("--format", nargs="+", choices=OUTPUT_FORMATS, default=None)
    output.add_argument("--dry-run", action="store_true", help="Print summary without writing files")

    return parser


def build_shift_fit_parser() -> argparse.ArgumentParser:
    """Build the parser for modifying an existing FIT activity start time."""
    parser = argparse.ArgumentParser(
        prog="keep-data-sim shift-fit",
        description="Change an existing FIT activity start time and rebuild its CRC",
    )
    parser.add_argument("input", help="Existing .fit activity file")
    parser.add_argument(
        "--start-time",
        required=True,
        help="New local start time (YYYY-MM-DD HH:MM:SS)",
    )
    parser.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="IANA timezone for --start-time (default: Asia/Shanghai)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .fit path (default: <input>_shifted.fit)",
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Patch timestamps in place and preserve all original FIT messages",
    )
    return parser


def build_config(args: argparse.Namespace) -> SimConfig:
    """Construct a simulation config from parsed CLI arguments."""
    if args.start_time:
        start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    else:
        start_time = datetime.now(timezone.utc)

    waypoints: tuple[tuple[float, float], ...] = ()
    if args.waypoints:
        parsed_waypoints = []
        for pair in args.waypoints.split(";"):
            lat_str, lon_str = pair.split(",")
            parsed_waypoints.append((float(lat_str), float(lon_str)))
        waypoints = tuple(parsed_waypoints)

    cadence_avg = args.cadence_avg
    if cadence_avg is None:
        cadence_avg = 170 if args.sport == "running" else 85

    if args.format is None:
        output_formats = ("fit",) if args.treadmill else OUTPUT_FORMATS
    else:
        output_formats = tuple(args.format)

    return SimConfig(
        sport=args.sport,
        distance_m=args.distance,
        start_time=start_time,
        timezone_name=args.timezone,
        treadmill=args.treadmill,
        route=RouteConfig(
            type=args.route_type,
            center_lat=args.start_lat,
            center_lon=args.start_lon,
            waypoints=waypoints,
            radius_m=args.route_radius,
            out_distance_m=args.out_distance,
            bearing_deg=args.bearing,
            point_spacing_m=args.point_spacing,
            gps_noise_sigma_m=args.gps_noise,
            import_file=args.import_file,
        ),
        pace=PaceConfig(
            strategy=args.pace_strategy,
            avg_pace_min_per_km=parse_pace(args.pace),
            avg_speed_kmh=args.speed if args.speed else 25.0,
            negative_split_ratio=args.split_ratio,
            positive_split_ratio=1.0 / args.split_ratio if args.split_ratio > 0 else 1.05,
            interval_fast_min_per_km=parse_pace(args.interval_fast),
            interval_slow_min_per_km=parse_pace(args.interval_slow),
            interval_fast_speed_kmh=args.interval_fast_speed,
            interval_slow_speed_kmh=args.interval_slow_speed,
            interval_fast_duration_s=args.interval_fast_dur,
            interval_slow_duration_s=args.interval_slow_dur,
            warmup_duration_s=args.warmup_dur,
            warmup_speed_factor=args.warmup_factor,
        ),
        heart_rate=HeartRateConfig(
            resting_hr=args.hr_resting,
            max_hr=args.hr_max,
            avg_hr=args.hr_avg,
            lag_seconds=args.hr_lag,
            noise_std=args.hr_noise,
        ),
        elevation=ElevationConfig(
            total_gain_m=args.elevation_gain,
            mode=args.elevation_mode,
            hill_count=args.hill_count,
            start_elevation_m=args.start_elevation,
        ),
        cadence=CadenceConfig(
            running_avg_spm=cadence_avg if args.sport == "running" else 170,
            cycling_avg_rpm=cadence_avg if args.sport == "cycling" else 85,
        ),
        output_dir=args.output_dir,
        output_formats=output_formats,
        title=args.title,
        seed=args.seed,
    )


def print_summary(summary: dict) -> None:
    """Print a human-readable workout summary."""
    print("\n=== Workout Summary ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print()


def main(argv: list[str] | None = None) -> None:
    """Run the command line interface."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments and arguments[0] == "shift-fit":
        parser = build_shift_fit_parser()
        args = parser.parse_args(arguments[1:])
        try:
            new_start = parse_local_start_time(args.start_time, args.timezone)
            if args.preserve_structure:
                result = shift_fit_binary_start_time(
                    args.input,
                    new_start,
                    args.output,
                    timezone_name=args.timezone,
                )
            else:
                result = shift_fit_start_time(
                    args.input,
                    new_start,
                    args.output,
                    timezone_name=args.timezone,
                )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))

        print()
        print("=== FIT Date Shifted ===")
        print(f"  output: {result.output_path}")
        print(f"  old_start_utc: {result.old_start.isoformat()}")
        print(f"  new_start_utc: {result.new_start.isoformat()}")
        print(f"  shifted_messages: {result.message_count}")
        print(f"  skipped_private_messages: {result.skipped_message_count}")
        if hasattr(result, "patched_field_count"):
            print(f"  patched_timestamp_fields: {result.patched_field_count}")
        print()
        return

    parser = build_parser()
    args = parser.parse_args(arguments)
    config = build_config(args)
    sim = Simulator(config)

    if args.dry_run:
        print_summary(sim.dry_run())
        return

    paths, summary = sim.run_with_summary()
    print("\n=== Generated Files ===")
    for path in paths:
        print(f"  {path}")

    print_summary(summary)


if __name__ == "__main__":
    main()
