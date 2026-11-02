"""Shift FIT timestamps without re-encoding the original message stream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_fit_sdk import CrcCalculator
from garmin_fit_sdk.fit import BASE_TYPE
from garmin_fit_sdk.profile import Profile
from garmin_fit_sdk.util import convert_datetime_to_timestamp

from keep_data_sim.fit_shift import (
    _calculate_local_delta,
    _decode_ordered,
    _find_activity_start,
    _verify_fit,
)

_DEFINITION_MASK = 0x40
_DEVELOPER_DATA_MASK = 0x20
_COMPRESSED_TIMESTAMP_MASK = 0x80
_LOCAL_MESG_NUM_MASK = 0x0F
_UINT32_BASE_TYPES = {BASE_TYPE["UINT32"], BASE_TYPE["UINT32Z"]}
_TIMESTAMP_FIELD_NUM = 253
_TIMESTAMP_HEURISTIC_RANGE = timedelta(days=370)


@dataclass(frozen=True)
class BinaryFitShiftResult:
    """Details about a structure-preserving FIT timestamp shift."""

    input_path: Path
    output_path: Path
    old_start: datetime
    new_start: datetime
    delta: timedelta
    message_count: int
    patched_field_count: int
    skipped_message_count: int = 0


@dataclass(frozen=True)
class _FieldDefinition:
    number: int
    size: int
    base_type: int
    offset: int


@dataclass(frozen=True)
class _MessageDefinition:
    global_number: int
    byte_order: str
    fields: tuple[_FieldDefinition, ...]
    payload_size: int


def shift_fit_binary_start_time(
    input_path: str | Path,
    new_start: datetime,
    output_path: str | Path | None = None,
    timezone_name: str | None = "Asia/Shanghai",
) -> BinaryFitShiftResult:
    """Shift timestamp bytes while preserving all FIT records and definitions."""
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
        else source.with_name(f"{source.stem}_preserved.fit")
    )
    if destination.suffix.lower() != ".fit":
        raise ValueError(f"Output file must have a .fit extension: {destination}")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must be different")
    if destination.exists():
        raise FileExistsError(f"Output file already exists: {destination}")

    ordered_messages, _ = _decode_ordered(source)
    old_start = _find_activity_start(ordered_messages)
    normalized_new_start = new_start.astimezone(timezone.utc)
    utc_delta = normalized_new_start - old_start
    local_delta = _calculate_local_delta(
        ordered_messages,
        normalized_new_start,
        utc_delta,
        timezone_name,
    )

    data = bytearray(source.read_bytes())
    original_size = len(data)
    patched_fields, message_count = _patch_fit_chain(
        data,
        round(utc_delta.total_seconds()),
        round(local_delta.total_seconds()),
        old_start,
    )
    if len(data) != original_size:
        raise ValueError("Structure-preserving shift unexpectedly changed file size")

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as output_file:
            output_file.write(data)
        _verify_fit(destination)
        output_messages, _ = _decode_ordered(destination)
        output_start = _find_activity_start(output_messages)
        if output_start != normalized_new_start:
            raise ValueError(
                f"Generated FIT start time is {output_start.isoformat()}, "
                f"expected {normalized_new_start.isoformat()}"
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return BinaryFitShiftResult(
        input_path=source,
        output_path=destination,
        old_start=old_start,
        new_start=normalized_new_start,
        delta=utc_delta,
        message_count=message_count,
        patched_field_count=patched_fields,
    )


def _patch_fit_chain(
    data: bytearray,
    utc_delta_seconds: int,
    local_delta_seconds: int,
    old_start: datetime,
) -> tuple[int, int]:
    file_start = 0
    patched_fields = 0
    message_count = 0
    old_start_value = convert_datetime_to_timestamp(old_start)
    heuristic_radius = round(_TIMESTAMP_HEURISTIC_RANGE.total_seconds())
    heuristic_min = old_start_value - heuristic_radius
    heuristic_max = old_start_value + heuristic_radius

    while file_start < len(data):
        if file_start + 14 > len(data):
            raise ValueError("Truncated FIT file header")
        header_size = data[file_start]
        if header_size < 12 or file_start + header_size > len(data):
            raise ValueError("Invalid FIT header size")
        if bytes(data[file_start + 8 : file_start + 12]) != b".FIT":
            raise ValueError("Invalid FIT signature")

        data_size = int.from_bytes(
            data[file_start + 4 : file_start + 8],
            "little",
        )
        records_start = file_start + header_size
        records_end = records_start + data_size
        crc_end = records_end + 2
        if crc_end > len(data):
            raise ValueError("FIT data size extends past the end of the file")

        changed, messages = _patch_records(
            data,
            records_start,
            records_end,
            utc_delta_seconds,
            local_delta_seconds,
            heuristic_min,
            heuristic_max,
        )
        patched_fields += changed
        message_count += messages

        crc = CrcCalculator.calculate_crc(data, file_start, records_end)
        data[records_end:crc_end] = crc.to_bytes(2, "little")
        file_start = crc_end

    return patched_fields, message_count


def _patch_records(
    data: bytearray,
    start: int,
    end: int,
    utc_delta_seconds: int,
    local_delta_seconds: int,
    heuristic_min: int,
    heuristic_max: int,
) -> tuple[int, int]:
    definitions: dict[int, _MessageDefinition] = {}
    position = start
    patched_fields = 0
    message_count = 0

    while position < end:
        record_header = data[position]
        if record_header & _COMPRESSED_TIMESTAMP_MASK:
            local_number = (record_header >> 5) & 0x03
            definition = _require_definition(definitions, local_number)
            position += 1 + definition.payload_size
            message_count += 1
            continue

        local_number = record_header & _LOCAL_MESG_NUM_MASK
        if record_header & _DEFINITION_MASK:
            definition, position = _read_definition(
                data,
                position,
                end,
                bool(record_header & _DEVELOPER_DATA_MASK),
            )
            definitions[local_number] = definition
            continue

        definition = _require_definition(definitions, local_number)
        payload_start = position + 1
        payload_end = payload_start + definition.payload_size
        if payload_end > end:
            raise ValueError("FIT data message extends past the data section")
        patched_fields += _patch_message_fields(
            data,
            payload_start,
            definition,
            utc_delta_seconds,
            local_delta_seconds,
            heuristic_min,
            heuristic_max,
        )
        position = payload_end
        message_count += 1

    if position != end:
        raise ValueError("FIT record parsing did not end at the data boundary")
    return patched_fields, message_count


def _read_definition(
    data: bytearray,
    position: int,
    end: int,
    has_developer_fields: bool,
) -> tuple[_MessageDefinition, int]:
    if position + 6 > end:
        raise ValueError("Truncated FIT definition message")
    architecture = data[position + 2]
    if architecture not in (0, 1):
        raise ValueError(f"Unsupported FIT architecture: {architecture}")
    byte_order = "little" if architecture == 0 else "big"
    global_number = int.from_bytes(
        data[position + 3 : position + 5],
        byte_order,
    )
    field_count = data[position + 5]
    cursor = position + 6
    fields: list[_FieldDefinition] = []
    payload_size = 0

    for _ in range(field_count):
        if cursor + 3 > end:
            raise ValueError("Truncated FIT field definition")
        number, size, base_type = data[cursor : cursor + 3]
        fields.append(
            _FieldDefinition(
                number=number,
                size=size,
                base_type=base_type & 0x1F,
                offset=payload_size,
            )
        )
        payload_size += size
        cursor += 3

    if has_developer_fields:
        if cursor >= end:
            raise ValueError("Missing FIT developer field count")
        developer_field_count = data[cursor]
        cursor += 1
        developer_bytes = developer_field_count * 3
        if cursor + developer_bytes > end:
            raise ValueError("Truncated FIT developer field definitions")
        for index in range(developer_field_count):
            payload_size += data[cursor + index * 3 + 1]
        cursor += developer_bytes

    return (
        _MessageDefinition(
            global_number=global_number,
            byte_order=byte_order,
            fields=tuple(fields),
            payload_size=payload_size,
        ),
        cursor,
    )


def _patch_message_fields(
    data: bytearray,
    payload_start: int,
    definition: _MessageDefinition,
    utc_delta_seconds: int,
    local_delta_seconds: int,
    heuristic_min: int,
    heuristic_max: int,
) -> int:
    patched = 0
    message_profile = Profile["messages"].get(definition.global_number)
    profile_fields = message_profile.get("fields", {}) if message_profile else {}

    for field in definition.fields:
        field_profile = profile_fields.get(field.number)
        field_type = field_profile.get("type") if field_profile else None
        if field.number == _TIMESTAMP_FIELD_NUM:
            field_type = "date_time"

        if field_type == "local_date_time":
            patched += _shift_uint32_values(
                data,
                payload_start + field.offset,
                field,
                definition.byte_order,
                local_delta_seconds,
            )
        elif field_type == "date_time":
            patched += _shift_uint32_values(
                data,
                payload_start + field.offset,
                field,
                definition.byte_order,
                utc_delta_seconds,
            )
        elif field_profile is None and field.base_type in _UINT32_BASE_TYPES:
            patched += _shift_timestamp_like_values(
                data,
                payload_start + field.offset,
                field,
                definition.byte_order,
                utc_delta_seconds,
                heuristic_min,
                heuristic_max,
            )

    return patched


def _shift_uint32_values(
    data: bytearray,
    start: int,
    field: _FieldDefinition,
    byte_order: str,
    delta_seconds: int,
) -> int:
    if field.base_type not in _UINT32_BASE_TYPES or field.size % 4:
        return 0
    patched = 0
    for offset in range(0, field.size, 4):
        position = start + offset
        value = int.from_bytes(data[position : position + 4], byte_order)
        if value in (0, 0xFFFFFFFF):
            continue
        shifted = value + delta_seconds
        if not 0 < shifted < 0xFFFFFFFF:
            raise ValueError("Shifted FIT timestamp is outside the uint32 range")
        data[position : position + 4] = shifted.to_bytes(4, byte_order)
        patched += 1
    return patched


def _shift_timestamp_like_values(
    data: bytearray,
    start: int,
    field: _FieldDefinition,
    byte_order: str,
    delta_seconds: int,
    heuristic_min: int,
    heuristic_max: int,
) -> int:
    if field.size % 4:
        return 0
    patched = 0
    for offset in range(0, field.size, 4):
        position = start + offset
        value = int.from_bytes(data[position : position + 4], byte_order)
        if not heuristic_min <= value <= heuristic_max:
            continue
        shifted = value + delta_seconds
        if not 0 < shifted < 0xFFFFFFFF:
            raise ValueError("Shifted private FIT timestamp is outside the uint32 range")
        data[position : position + 4] = shifted.to_bytes(4, byte_order)
        patched += 1
    return patched


def _require_definition(
    definitions: dict[int, _MessageDefinition],
    local_number: int,
) -> _MessageDefinition:
    try:
        return definitions[local_number]
    except KeyError as exc:
        raise ValueError(
            f"FIT data message uses undefined local message {local_number}"
        ) from exc
