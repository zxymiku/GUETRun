"""FIT file exporter using garmin-fit-sdk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_fit_sdk import Encoder

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.registry import register_exporter
from keep_data_sim.core.types import TrackPoint
from keep_data_sim.export.base import Exporter
from keep_data_sim.utils.geo import degrees_to_semicircles

# FIT message numbers
MESG_NUM_FILE_ID = 0
MESG_NUM_DEVICE_INFO = 23
MESG_NUM_SPORT = 12
MESG_NUM_EVENT = 21
MESG_NUM_RECORD = 20
MESG_NUM_LAP = 19
MESG_NUM_SESSION = 18
MESG_NUM_ACTIVITY = 34

# Sport type enum values
SPORT_RUNNING = 1
SPORT_CYCLING = 2
SUB_SPORT_GENERIC = 0
SUB_SPORT_TREADMILL = 1

# Event and event type enum values
EVENT_TIMER = 0
EVENT_ACTIVITY_END = 26
EVENT_TYPE_START = 0
EVENT_TYPE_STOP = 1
EVENT_TYPE_STOP_ALL = 4

# File type
FILE_TYPE_ACTIVITY = 4

# Creator identity. 255 is the FIT development manufacturer ID.
MANUFACTURER_DEVELOPMENT = 255
PRODUCT_KEEP_DATA_SIM = 1
SERIAL_NUMBER_KEEP_DATA_SIM = 0x4B445349
PRODUCT_NAME = "Keep Data Simulator"
SOFTWARE_VERSION = 0.1
DEVICE_INDEX_CREATOR = 0


class FitExporter(Exporter):
    """Export track points as a Garmin-compatible FIT activity file."""

    def export(
        self,
        points: list[TrackPoint],
        config: SimConfig,
        output_dir: Path,
        title: str,
    ) -> Path:
        if not points:
            raise ValueError("No track points to export")

        output_path = output_dir / f"{self._safe_filename(title)}.fit"
        stats = self._compute_stats(points, config.sport)
        stats["sub_sport"] = (
            SUB_SPORT_TREADMILL if config.treadmill else SUB_SPORT_GENERIC
        )

        encoder = Encoder()
        with open(output_path, "wb") as output_file:
            encoder.on_mesg(MESG_NUM_FILE_ID, self._build_file_id(points[0].timestamp))
            encoder.on_mesg(
                MESG_NUM_DEVICE_INFO,
                self._build_device_info(points[0].timestamp),
            )
            encoder.on_mesg(MESG_NUM_SPORT, self._build_sport(config.sport, config.treadmill))
            encoder.on_mesg(
                MESG_NUM_EVENT,
                self._build_timer_event(points[0].timestamp, EVENT_TYPE_START),
            )

            for point in points:
                encoder.on_mesg(
                    MESG_NUM_RECORD,
                    self._build_record(point, config.sport, config.treadmill),
                )

            encoder.on_mesg(
                MESG_NUM_EVENT,
                self._build_timer_event(points[-1].timestamp, EVENT_TYPE_STOP_ALL),
            )
            encoder.on_mesg(MESG_NUM_LAP, self._build_lap(points, stats))
            encoder.on_mesg(MESG_NUM_SESSION, self._build_session(points, stats))
            encoder.on_mesg(
                MESG_NUM_ACTIVITY,
                self._build_activity(points, config.timezone_name),
            )

            output_file.write(encoder.close())

        return output_path

    def _build_file_id(self, start_time: datetime) -> dict:
        return {
            "type": FILE_TYPE_ACTIVITY,
            "manufacturer": MANUFACTURER_DEVELOPMENT,
            "product": PRODUCT_KEEP_DATA_SIM,
            "product_name": PRODUCT_NAME,
            "time_created": start_time,
            "serial_number": SERIAL_NUMBER_KEEP_DATA_SIM,
        }

    def _build_device_info(self, start_time: datetime) -> dict:
        return {
            "timestamp": start_time,
            "device_index": DEVICE_INDEX_CREATOR,
            "manufacturer": MANUFACTURER_DEVELOPMENT,
            "product": PRODUCT_KEEP_DATA_SIM,
            "product_name": PRODUCT_NAME,
            "serial_number": SERIAL_NUMBER_KEEP_DATA_SIM,
            "software_version": SOFTWARE_VERSION,
        }

    def _build_sport(self, sport: str, treadmill: bool) -> dict:
        sport_value = SPORT_RUNNING if sport == "running" else SPORT_CYCLING
        sub_sport = SUB_SPORT_TREADMILL if treadmill else SUB_SPORT_GENERIC
        return {"sport": sport_value, "sub_sport": sub_sport}

    def _build_timer_event(self, timestamp: datetime, event_type: int) -> dict:
        return {
            "timestamp": timestamp,
            "event": EVENT_TIMER,
            "event_type": event_type,
        }

    def _build_record(
        self,
        point: TrackPoint,
        sport: str,
        treadmill: bool,
    ) -> dict:
        fit_cadence = self._fit_cadence(point.cadence, sport)
        cadence_base, cadence_fraction = self._split_fraction(fit_cadence)
        message = {
            "timestamp": point.timestamp,
            "heart_rate": point.heart_rate,
            "cadence": cadence_base,
            "distance": point.distance,
            "speed": point.speed,
        }
        if not treadmill:
            message.update(
                {
                    "position_lat": degrees_to_semicircles(point.latitude),
                    "position_long": degrees_to_semicircles(point.longitude),
                    "altitude": point.elevation,
                }
            )
        if sport == "running":
            message["fractional_cadence"] = cadence_fraction
            if point.cadence > 0:
                message["step_length"] = point.speed * 60_000 / point.cadence
        return message

    def _build_lap(self, points: list[TrackPoint], stats: dict) -> dict:
        message = {
            "message_index": 0,
            "timestamp": points[-1].timestamp,
            "start_time": points[0].timestamp,
            "total_elapsed_time": stats["duration_s"],
            "total_timer_time": stats["duration_s"],
            "total_distance": stats["distance_m"],
            "total_cycles": stats["total_cycles"],
            "avg_heart_rate": stats["avg_hr"],
            "max_heart_rate": stats["max_hr"],
            "avg_speed": stats["avg_speed"],
            "max_speed": stats["max_speed"],
            "avg_cadence": stats["avg_cadence_base"],
            "max_cadence": stats["max_cadence_base"],
            "avg_fractional_cadence": stats["avg_cadence_fraction"],
            "max_fractional_cadence": stats["max_cadence_fraction"],
            "sport": stats["sport_enum"],
            "sub_sport": stats["sub_sport"],
        }
        if stats["avg_step_length_mm"] is not None:
            message["avg_step_length"] = stats["avg_step_length_mm"]
        return message

    def _build_session(self, points: list[TrackPoint], stats: dict) -> dict:
        message = self._build_lap(points, stats)
        message["total_ascent"] = int(round(stats["elevation_gain"]))
        message["total_descent"] = int(round(stats["elevation_loss"]))
        message["first_lap_index"] = 0
        message["num_laps"] = 1
        return message

    def _build_activity(
        self,
        points: list[TrackPoint],
        timezone_name: str,
    ) -> dict:
        duration = (points[-1].timestamp - points[0].timestamp).total_seconds()
        local_time = points[-1].timestamp.astimezone(ZoneInfo(timezone_name))
        fit_local_time = local_time.replace(tzinfo=timezone.utc)
        return {
            "timestamp": points[-1].timestamp,
            "local_timestamp": fit_local_time,
            "total_timer_time": duration,
            "num_sessions": 1,
            "event": EVENT_ACTIVITY_END,
            "event_type": EVENT_TYPE_STOP,
        }

    def _compute_stats(self, points: list[TrackPoint], sport: str) -> dict:
        total_distance = points[-1].distance
        duration_s = (points[-1].timestamp - points[0].timestamp).total_seconds()
        avg_speed = total_distance / duration_s if duration_s > 0 else 0

        speeds = [point.speed for point in points]
        heart_rates = [point.heart_rate for point in points]
        fit_cadences = [self._fit_cadence(point.cadence, sport) for point in points]
        total_cycles_float = self._integrate_cycles(points, fit_cadences)
        total_cycles = int(round(total_cycles_float))
        if duration_s > 0 and total_cycles_float > 0:
            avg_fit_cadence = total_cycles_float * 60 / duration_s
        else:
            avg_fit_cadence = sum(fit_cadences) / len(fit_cadences)
        max_fit_cadence = max(fit_cadences)
        avg_cadence_base, avg_cadence_fraction = self._split_fraction(avg_fit_cadence)
        max_cadence_base, max_cadence_fraction = self._split_fraction(max_fit_cadence)

        elevation_gain = 0.0
        elevation_loss = 0.0
        for index in range(1, len(points)):
            difference = points[index].elevation - points[index - 1].elevation
            if difference > 0:
                elevation_gain += difference
            else:
                elevation_loss += abs(difference)

        avg_step_length_mm = None
        if sport == "running" and total_cycles_float > 0:
            total_steps = total_cycles_float * 2
            avg_step_length_mm = total_distance * 1000 / total_steps

        return {
            "distance_m": total_distance,
            "duration_s": duration_s,
            "avg_speed": avg_speed,
            "max_speed": max(speeds),
            "avg_hr": int(round(sum(heart_rates) / len(heart_rates))),
            "max_hr": max(heart_rates),
            "total_cycles": total_cycles,
            "avg_cadence_base": avg_cadence_base,
            "avg_cadence_fraction": avg_cadence_fraction,
            "max_cadence_base": max_cadence_base,
            "max_cadence_fraction": max_cadence_fraction,
            "avg_step_length_mm": avg_step_length_mm,
            "elevation_gain": elevation_gain,
            "elevation_loss": elevation_loss,
            "sport_enum": SPORT_RUNNING if sport == "running" else SPORT_CYCLING,
        }

    @staticmethod
    def _fit_cadence(cadence: int | float, sport: str) -> float:
        return cadence / 2 if sport == "running" else float(cadence)

    @staticmethod
    def _split_fraction(value: float) -> tuple[int, float]:
        quantized = round(value * 128) / 128
        base = int(quantized)
        return base, quantized - base

    @staticmethod
    def _integrate_cycles(
        points: list[TrackPoint],
        fit_cadences: list[float],
    ) -> float:
        total_cycles = 0.0
        for index in range(1, len(points)):
            elapsed_seconds = (
                points[index].timestamp - points[index - 1].timestamp
            ).total_seconds()
            interval_cadence = (
                fit_cadences[index - 1] + fit_cadences[index]
            ) / 2
            total_cycles += interval_cadence * elapsed_seconds / 60
        return total_cycles

    @staticmethod
    def _safe_filename(title: str) -> str:
        return "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in title
        )


# Auto-register
register_exporter("fit", FitExporter)
