"""Shift every timestamp in an existing FIT activity."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from garmin_fit_sdk import Decoder, Encoder, Stream
from garmin_fit_sdk.profile import Profile
from garmin_fit_sdk.util import convert_datetime_to_timestamp

MESG_NUM_LAP = 19
MESG_NUM_RECORD = 20
MESG_NUM_SESSION = 18


@dataclass(frozen=True)
class FitShiftResult:
    """Details about a completed FIT timestamp shift."""

    input_path: Path
    output_path: Path
    old_start: datetime
    new_start: datetime
    delta: timedelta
    message_count: int
    skipped_message_count: int = 0


def parse_local_start_time(value: str, timezone_name: str = "Asia/Shanghai") -> datetime:
    """Parse a wall-clock start time and return an aware UTC datetime."""
    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc

    try:
        local_time = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(
            "Start time must use the format YYYY-MM-DD HH:MM:SS"
        ) from exc

    return local_time.replace(tzinfo=local_zone).astimezone(timezone.utc)


def shift_fit_start_time(
    input_path: str | Path,
    new_start: datetime,
    output_path: str | Path | None = None,
    timezone_name: str | None = None,
) -> FitShiftResult:
    """Shift an activity to ``new_start`` while preserving its elapsed times."""
    source = Path(input_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"FIT input file does not exist: {source}")
    if source.suffix.lower() != ".fit":
        raise ValueError(f"Input file must have a .fit extension: {source}")
    if new_start.tzinfo is None or new_start.utcoffset() is None:
        raise ValueError("New start time must include timezone information")

    destination = (
        Path(output_path).expanduser()
        if output_path is not None
        else source.with_name(f"{source.stem}_shifted.fit")
    )
    if destination.suffix.lower() != ".fit":
        raise ValueError(f"Output file must have a .fit extension: {destination}")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must be different")
    if destination.exists():
        raise FileExistsError(f"Output file already exists: {destination}")

    ordered_messages, field_descriptions = _decode_ordered(source)
    old_start = _find_activity_start(ordered_messages)
    normalized_new_start = new_start.astimezone(timezone.utc)
    delta = normalized_new_start - old_start
    local_delta = _calculate_local_delta(
        ordered_messages,
        normalized_new_start,
        delta,
        timezone_name,
    )

    encoder = Encoder(field_descriptions=field_descriptions)
    skipped_message_count = 0
    try:
        for mesg_num, mesg in ordered_messages:
            if mesg_num not in Profile["messages"]:
                skipped_message_count += 1
                continue
            encoder.on_mesg(
                mesg_num,
                _shift_message(mesg_num, mesg, delta, local_delta),
            )
        encoded = encoder.close()
    except Exception as exc:
        raise ValueError(f"Could not re-encode FIT messages: {exc}") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as output_file:
            output_file.write(encoded)
        _verify_fit(destination)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return FitShiftResult(
        input_path=source,
        output_path=destination,
        old_start=old_start,
        new_start=normalized_new_start,
        delta=delta,
        message_count=len(ordered_messages) - skipped_message_count,
        skipped_message_count=skipped_message_count,
    )


def _decode_ordered(path: Path) -> tuple[list[tuple[int, dict]], dict]:
    ordered_messages: list[tuple[int, dict]] = []
    field_descriptions: dict[Any, dict] = {}

    def collect_message(mesg_num: int, mesg: dict) -> None:
        ordered_messages.append((mesg_num, deepcopy(mesg)))

    def collect_field_description(
        key: Any,
        developer_data_id_mesg: dict,
        field_description_mesg: dict,
    ) -> None:
        field_descriptions[key] = {
            "developer_data_id_mesg": deepcopy(developer_data_id_mesg),
            "field_description_mesg": deepcopy(field_description_mesg),
        }

    stream = Stream.from_file(str(path))
    try:
        decoder = Decoder(stream)
        _, errors = decoder.read(
            enable_crc_check=True,
            expand_sub_fields=False,
            expand_components=False,
            merge_heart_rates=False,
            mesg_listener=collect_message,
            field_description_listener=collect_field_description,
        )
    finally:
        stream.close()
    if errors:
        raise ValueError(f"Could not decode FIT file: {errors[0]}")
    if not ordered_messages:
        raise ValueError("FIT file contains no messages")
    return ordered_messages, field_descriptions


def _find_activity_start(ordered_messages: list[tuple[int, dict]]) -> datetime:
    for mesg_num in (MESG_NUM_SESSION, MESG_NUM_LAP, MESG_NUM_RECORD):
        field_name = "start_time" if mesg_num != MESG_NUM_RECORD else "timestamp"
        for current_num, mesg in ordered_messages:
            value = mesg.get(field_name)
            if current_num == mesg_num and isinstance(value, datetime):
                return _as_utc(value)
    raise ValueError("Could not find an activity start time in the FIT file")



def _calculate_local_delta(
    ordered_messages: list[tuple[int, dict]],
    new_start: datetime,
    utc_delta: timedelta,
    timezone_name: str | None,
) -> timedelta:
    if timezone_name is None:
        return utc_delta

    try:
        target_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone_name}") from exc

    original_offset = _find_local_utc_offset(ordered_messages)
    if original_offset is None:
        return utc_delta

    target_offset = new_start.astimezone(target_zone).utcoffset()
    if target_offset is None:
        return utc_delta
    return utc_delta + target_offset - original_offset


def _find_local_utc_offset(
    ordered_messages: list[tuple[int, dict]],
) -> timedelta | None:
    for mesg_num, mesg in ordered_messages:
        if mesg_num != 34:
            continue
        timestamp = mesg.get("timestamp")
        local_timestamp = mesg.get("local_timestamp")
        if isinstance(timestamp, datetime) and isinstance(local_timestamp, (int, float)):
            utc_timestamp = convert_datetime_to_timestamp(_as_utc(timestamp))
            return timedelta(seconds=local_timestamp - utc_timestamp)
    return None


def _shift_message(
    mesg_num: int,
    mesg: dict,
    utc_delta: timedelta,
    local_delta: timedelta,
) -> dict:
    shifted = _shift_value(mesg, utc_delta)
    message_profile = Profile["messages"].get(mesg_num, {})
    for field_profile in message_profile.get("fields", {}).values():
        if field_profile.get("type") != "local_date_time":
            continue
        field_name = field_profile.get("name")
        if field_name in shifted:
            shifted[field_name] = _shift_numeric_time(
                shifted[field_name],
                round(local_delta.total_seconds()),
            )
    return shifted


def _shift_numeric_time(value: Any, delta_seconds: int) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value + delta_seconds
    if isinstance(value, list):
        return [_shift_numeric_time(item, delta_seconds) for item in value]
    if isinstance(value, tuple):
        return tuple(_shift_numeric_time(item, delta_seconds) for item in value)
    return value

def _shift_value(value: Any, delta: timedelta) -> Any:
    if isinstance(value, datetime):
        return value + delta
    if isinstance(value, dict):
        return {key: _shift_value(item, delta) for key, item in value.items()}
    if isinstance(value, list):
        return [_shift_value(item, delta) for item in value]
    if isinstance(value, tuple):
        return tuple(_shift_value(item, delta) for item in value)
    return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _verify_fit(path: Path) -> None:
    stream = Stream.from_file(str(path))
    try:
        decoder = Decoder(stream)
        messages, errors = decoder.read(enable_crc_check=True, merge_heart_rates=False)
    finally:
        stream.close()
    if errors:
        raise ValueError(f"Generated FIT file failed CRC validation: {errors[0]}")
    if not messages:
        raise ValueError("Generated FIT file contains no messages")
