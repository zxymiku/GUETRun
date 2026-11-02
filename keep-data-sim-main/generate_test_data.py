"""Generate test data for Keep data simulator.

Produces 12 test scenarios covering running/cycling, various pace strategies,
route types, distances, and locations. Outputs GPX + FIT to test_data/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from keep_data_sim.config.schema import (
    CadenceConfig,
    ElevationConfig,
    HeartRateConfig,
    PaceConfig,
    RouteConfig,
    SimConfig,
)
from keep_data_sim.core.simulator import Simulator


@dataclass
class Scenario:
    name: str
    config: SimConfig
    description: str


def make_scenarios() -> list[Scenario]:
    """Define all test scenarios."""
    scenarios: list[Scenario] = []

    # Running scenarios

    scenarios.append(Scenario(
        name="run_5k_constant",
        description="5km constant pace, circular, Beijing",
        config=SimConfig(
            sport="running",
            distance_m=5000.0,
            start_time=datetime(2025, 6, 15, 7, 0, 0, tzinfo=timezone.utc),
            title="Morning 5K Run",
            seed=42,
            route=RouteConfig(
                type="circular",
                center_lat=39.9042,
                center_lon=116.4074,
                radius_m=800.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(strategy="constant", avg_pace_min_per_km=5.5),
            heart_rate=HeartRateConfig(avg_hr=145, resting_hr=60, max_hr=190),
            elevation=ElevationConfig(total_gain_m=30.0, hill_count=2),
            cadence=CadenceConfig(running_avg_spm=170),
        ),
    ))

    scenarios.append(Scenario(
        name="run_10k_negative_split",
        description="10km negative split, circular, Beijing",
        config=SimConfig(
            sport="running",
            distance_m=10000.0,
            start_time=datetime(2025, 6, 15, 6, 30, 0, tzinfo=timezone.utc),
            title="10K Negative Split",
            seed=123,
            route=RouteConfig(
                type="circular",
                center_lat=39.9042,
                center_lon=116.4074,
                radius_m=1600.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(
                strategy="negative_split",
                avg_pace_min_per_km=5.3,
                negative_split_ratio=0.92,
            ),
            heart_rate=HeartRateConfig(avg_hr=155, resting_hr=60, max_hr=190),
            elevation=ElevationConfig(total_gain_m=50.0, hill_count=3),
            cadence=CadenceConfig(running_avg_spm=175),
        ),
    ))

    scenarios.append(Scenario(
        name="run_half_marathon",
        description="21.1km constant pace, out-and-back, Shanghai",
        config=SimConfig(
            sport="running",
            distance_m=21100.0,
            start_time=datetime(2025, 6, 15, 5, 0, 0, tzinfo=timezone.utc),
            title="Half Marathon Training",
            seed=256,
            route=RouteConfig(
                type="out_and_back",
                center_lat=31.2304,
                center_lon=121.4737,
                out_distance_m=10550.0,
                bearing_deg=45.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(strategy="constant", avg_pace_min_per_km=5.0),
            heart_rate=HeartRateConfig(avg_hr=160, resting_hr=58, max_hr=192),
            elevation=ElevationConfig(total_gain_m=80.0, hill_count=5),
            cadence=CadenceConfig(running_avg_spm=178),
        ),
    ))

    scenarios.append(Scenario(
        name="run_interval_8k",
        description="8km interval training, circular, Guangzhou",
        config=SimConfig(
            sport="running",
            distance_m=8000.0,
            start_time=datetime(2025, 6, 15, 18, 0, 0, tzinfo=timezone.utc),
            title="Interval Training 8K",
            seed=789,
            route=RouteConfig(
                type="circular",
                center_lat=23.1291,
                center_lon=113.2644,
                radius_m=1300.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(
                strategy="interval",
                avg_pace_min_per_km=5.5,
                interval_fast_min_per_km=4.3,
                interval_slow_min_per_km=6.5,
                interval_fast_duration_s=240.0,
                interval_slow_duration_s=120.0,
                warmup_duration_s=300.0,
                warmup_speed_factor=0.8,
            ),
            heart_rate=HeartRateConfig(avg_hr=155, resting_hr=60, max_hr=190),
            elevation=ElevationConfig(total_gain_m=40.0, hill_count=3),
            cadence=CadenceConfig(running_avg_spm=175),
        ),
    ))

    scenarios.append(Scenario(
        name="run_easy_3k",
        description="3km easy pace, circular, Shenzhen",
        config=SimConfig(
            sport="running",
            distance_m=3000.0,
            start_time=datetime(2025, 6, 15, 19, 30, 0, tzinfo=timezone.utc),
            title="Easy Recovery Run",
            seed=321,
            route=RouteConfig(
                type="circular",
                center_lat=22.5431,
                center_lon=114.0579,
                radius_m=500.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(strategy="constant", avg_pace_min_per_km=6.5),
            heart_rate=HeartRateConfig(avg_hr=130, resting_hr=60, max_hr=190),
            elevation=ElevationConfig(total_gain_m=15.0, hill_count=1),
            cadence=CadenceConfig(running_avg_spm=165),
        ),
    ))

    scenarios.append(Scenario(
        name="run_positive_split_15k",
        description="15km positive split, out-and-back, Chengdu",
        config=SimConfig(
            sport="running",
            distance_m=15000.0,
            start_time=datetime(2025, 6, 15, 6, 0, 0, tzinfo=timezone.utc),
            title="15K Long Run",
            seed=654,
            route=RouteConfig(
                type="out_and_back",
                center_lat=30.5728,
                center_lon=104.0668,
                out_distance_m=7500.0,
                bearing_deg=90.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=3.0,
            ),
            pace=PaceConfig(
                strategy="positive_split",
                avg_pace_min_per_km=5.5,
                positive_split_ratio=1.08,
            ),
            heart_rate=HeartRateConfig(avg_hr=155, resting_hr=60, max_hr=190),
            elevation=ElevationConfig(total_gain_m=60.0, hill_count=4),
            cadence=CadenceConfig(running_avg_spm=172),
        ),
    ))

    # Cycling scenarios

    scenarios.append(Scenario(
        name="ride_20k_constant",
        description="20km constant speed, circular, Beijing",
        config=SimConfig(
            sport="cycling",
            distance_m=20000.0,
            start_time=datetime(2025, 6, 15, 8, 0, 0, tzinfo=timezone.utc),
            title="Morning Ride",
            seed=100,
            route=RouteConfig(
                type="circular",
                center_lat=39.9042,
                center_lon=116.4074,
                radius_m=3200.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(strategy="constant", avg_speed_kmh=25.0),
            heart_rate=HeartRateConfig(avg_hr=135, resting_hr=60, max_hr=185),
            elevation=ElevationConfig(total_gain_m=60.0, hill_count=4),
            cadence=CadenceConfig(cycling_avg_rpm=85),
        ),
    ))

    scenarios.append(Scenario(
        name="ride_40k_negative_split",
        description="40km negative split, out-and-back, Hangzhou",
        config=SimConfig(
            sport="cycling",
            distance_m=40000.0,
            start_time=datetime(2025, 6, 15, 6, 0, 0, tzinfo=timezone.utc),
            title="40K Training Ride",
            seed=200,
            route=RouteConfig(
                type="out_and_back",
                center_lat=30.2741,
                center_lon=120.1551,
                out_distance_m=20000.0,
                bearing_deg=0.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(
                strategy="negative_split",
                avg_speed_kmh=25.0,
                negative_split_ratio=0.93,
            ),
            heart_rate=HeartRateConfig(avg_hr=145, resting_hr=60, max_hr=185),
            elevation=ElevationConfig(total_gain_m=120.0, hill_count=6),
            cadence=CadenceConfig(cycling_avg_rpm=88),
        ),
    ))

    scenarios.append(Scenario(
        name="ride_interval_30k",
        description="30km interval training, circular, Nanjing",
        config=SimConfig(
            sport="cycling",
            distance_m=30000.0,
            start_time=datetime(2025, 6, 15, 17, 0, 0, tzinfo=timezone.utc),
            title="Evening Interval Ride",
            seed=300,
            route=RouteConfig(
                type="circular",
                center_lat=32.0603,
                center_lon=118.7969,
                radius_m=4800.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(
                strategy="interval",
                avg_speed_kmh=25.0,
                interval_fast_speed_kmh=32.0,
                interval_slow_speed_kmh=18.0,
                interval_fast_duration_s=300.0,
                interval_slow_duration_s=150.0,
                warmup_duration_s=600.0,
                warmup_speed_factor=0.7,
            ),
            heart_rate=HeartRateConfig(avg_hr=148, resting_hr=60, max_hr=185),
            elevation=ElevationConfig(total_gain_m=100.0, hill_count=5),
            cadence=CadenceConfig(cycling_avg_rpm=88),
        ),
    ))

    scenarios.append(Scenario(
        name="ride_easy_15k",
        description="15km easy ride, circular, Wuhan",
        config=SimConfig(
            sport="cycling",
            distance_m=15000.0,
            start_time=datetime(2025, 6, 15, 9, 0, 0, tzinfo=timezone.utc),
            title="Easy Spin",
            seed=400,
            route=RouteConfig(
                type="circular",
                center_lat=30.5928,
                center_lon=114.3055,
                radius_m=2400.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(strategy="constant", avg_speed_kmh=18.0),
            heart_rate=HeartRateConfig(avg_hr=120, resting_hr=60, max_hr=185),
            elevation=ElevationConfig(total_gain_m=30.0, hill_count=2),
            cadence=CadenceConfig(cycling_avg_rpm=78),
        ),
    ))

    scenarios.append(Scenario(
        name="ride_hilly_25k",
        description="25km hilly ride, circular, Chongqing",
        config=SimConfig(
            sport="cycling",
            distance_m=25000.0,
            start_time=datetime(2025, 6, 15, 7, 30, 0, tzinfo=timezone.utc),
            title="Chongqing Hill Climb",
            seed=500,
            route=RouteConfig(
                type="circular",
                center_lat=29.4316,
                center_lon=106.9123,
                radius_m=4000.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(strategy="constant", avg_speed_kmh=20.0),
            heart_rate=HeartRateConfig(avg_hr=155, resting_hr=60, max_hr=188),
            elevation=ElevationConfig(total_gain_m=250.0, hill_count=8),
            cadence=CadenceConfig(cycling_avg_rpm=80),
        ),
    ))

    scenarios.append(Scenario(
        name="ride_morning_50k",
        description="50km early morning ride, out-and-back",
        config=SimConfig(
            sport="cycling",
            distance_m=50000.0,
            start_time=datetime(2025, 6, 15, 5, 30, 0, tzinfo=timezone.utc),
            title="Dawn 50K Ride",
            seed=600,
            route=RouteConfig(
                type="out_and_back",
                center_lat=39.9042,
                center_lon=116.4074,
                out_distance_m=25000.0,
                bearing_deg=180.0,
                point_spacing_m=10.0,
                gps_noise_sigma_m=5.0,
            ),
            pace=PaceConfig(strategy="constant", avg_speed_kmh=28.0),
            heart_rate=HeartRateConfig(avg_hr=140, resting_hr=58, max_hr=185),
            elevation=ElevationConfig(total_gain_m=150.0, hill_count=6),
            cadence=CadenceConfig(cycling_avg_rpm=90),
        ),
    ))

    return scenarios


def generate_all(output_dir: str = "test_data") -> None:
    """Generate all test scenarios and print summary."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scenarios = make_scenarios()
    print(f"Generating {len(scenarios)} test scenarios to {out}/\n")

    # Table header
    print(f"{'#':<3} {'Name':<28} {'Sport':<9} {'Dist':>8} {'Strategy':<16} {'Route':<14} {'Points':>7}")
    print("-" * 95)

    for idx, sc in enumerate(scenarios, 1):
        cfg = sc.config
        # Set output dir and formats per scenario
        cfg = SimConfig(
            sport=cfg.sport,
            distance_m=cfg.distance_m,
            start_time=cfg.start_time,
            route=cfg.route,
            pace=cfg.pace,
            heart_rate=cfg.heart_rate,
            elevation=cfg.elevation,
            cadence=cfg.cadence,
            output_dir=str(out),
            output_formats=("gpx", "fit"),
            title=cfg.title,
            seed=cfg.seed,
        )

        sim = Simulator(cfg)
        summary = sim.dry_run()

        # Actually write the files
        paths = sim.run()

        dist_str = f"{summary['distance_m'] / 1000:.1f}km"
        print(
            f"{idx:<3} {sc.name:<28} {cfg.sport:<9} {dist_str:>8} "
            f"{cfg.pace.strategy:<16} {cfg.route.type:<14} {summary['num_points']:>7}"
        )

    print("-" * 95)
    print(f"\n[OK] Generated {len(scenarios) * 2} files (GPX + FIT) in {out}/\n")

    # List generated files
    files = sorted(out.glob("*"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<50} {size_kb:>7.1f} KB")


if __name__ == "__main__":
    generate_all()

