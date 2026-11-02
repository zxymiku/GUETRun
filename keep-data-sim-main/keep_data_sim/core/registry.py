"""Factory registry for route generators and exporters."""

from __future__ import annotations

from typing import TypeVar

from keep_data_sim.route.base import RouteGenerator
from keep_data_sim.route.circular import CircularRouteGenerator
from keep_data_sim.route.coord_file import CoordFileRouteGenerator
from keep_data_sim.route.gpx_import import GpxImportRouteGenerator
from keep_data_sim.route.hand_drawn import HandDrawnRouteGenerator
from keep_data_sim.route.out_and_back import OutAndBackRouteGenerator
from keep_data_sim.route.waypoint import WaypointRouteGenerator

T = TypeVar("T")

# Route generator registry
_ROUTE_GENERATORS: dict[str, type[RouteGenerator]] = {
    "circular": CircularRouteGenerator,
    "out_and_back": OutAndBackRouteGenerator,
    "waypoint": WaypointRouteGenerator,
    "gpx_import": GpxImportRouteGenerator,
    "coord_file": CoordFileRouteGenerator,
    "hand_drawn": HandDrawnRouteGenerator,
}


def get_route_generator(route_type: str) -> type[RouteGenerator]:
    """Return the route generator class for the given type name."""
    cls = _ROUTE_GENERATORS.get(route_type)
    if cls is None:
        raise ValueError(f"Unknown route type: {route_type}. Available: {list(_ROUTE_GENERATORS)}")
    return cls


# Exporter registry — populated when exporter modules are imported
_EXPORTERS: dict[str, type] = {}


def register_exporter(name: str, cls: type) -> None:
    """Register an exporter class under a format name."""
    _EXPORTERS[name] = cls


def get_exporter(format_name: str) -> type:
    """Return the exporter class for the given format name."""
    cls = _EXPORTERS.get(format_name)
    if cls is None:
        raise ValueError(f"Unknown export format: {format_name}. Available: {list(_EXPORTERS)}")
    return cls


def available_route_types() -> list[str]:
    return list(_ROUTE_GENERATORS.keys())


def available_export_formats() -> list[str]:
    return list(_EXPORTERS.keys())
