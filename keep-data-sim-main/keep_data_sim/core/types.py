"""Core type definitions for the data simulator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TrackPoint:
    """Single point in a workout track."""

    latitude: float
    longitude: float
    elevation: float
    timestamp: datetime
    speed: float
    heart_rate: int
    cadence: int
    distance: float
    temperature: float | None = None
