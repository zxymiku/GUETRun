"""GPX file exporter using gpxpy."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import gpxpy
import gpxpy.gpx

from keep_data_sim.config.schema import SimConfig
from keep_data_sim.core.registry import register_exporter
from keep_data_sim.core.types import TrackPoint
from keep_data_sim.export.base import Exporter

GPX_NS = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
GPX_NS_PREFIX = "ns3"
GPXX_NS = "http://www.garmin.com/xmlschemas/GpxExtensions/v3"


class GpxExporter(Exporter):
    """Export track points as a GPX 1.1 file with Garmin extensions."""

    def export(
        self,
        points: list[TrackPoint],
        config: SimConfig,
        output_dir: Path,
        title: str,
    ) -> Path:
        gpx = gpxpy.gpx.GPX()
        gpx.version = "1.1"
        gpx.creator = "Keep Data Simulator"

        # Add namespace for Garmin TrackPointExtension
        gpx.nsmap[GPX_NS_PREFIX] = GPX_NS

        # Track
        track = gpxpy.gpx.GPXTrack()
        track.name = title
        track.type = config.sport

        # Segment
        segment = gpxpy.gpx.GPXTrackSegment()

        for pt in points:
            gpx_pt = gpxpy.gpx.GPXTrackPoint(
                latitude=pt.latitude,
                longitude=pt.longitude,
                elevation=pt.elevation,
                time=pt.timestamp,
                speed=pt.speed,
            )

            # Add Garmin TrackPointExtension for HR and cadence
            if pt.heart_rate > 0 or pt.cadence > 0:
                ext = ET.Element(f"{{{GPX_NS}}}TrackPointExtension")
                if pt.heart_rate > 0:
                    hr_el = ET.SubElement(ext, f"{{{GPX_NS}}}hr")
                    hr_el.text = str(pt.heart_rate)
                if pt.cadence > 0:
                    cad_el = ET.SubElement(ext, f"{{{GPX_NS}}}cad")
                    cad_el.text = str(pt.cadence)
                gpx_pt.extensions.append(ext)

            segment.points.append(gpx_pt)

        track.segments.append(segment)
        gpx.tracks.append(track)

        # Write file
        output_path = output_dir / f"{self._safe_filename(title)}.gpx"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(gpx.to_xml())

        return output_path

    @staticmethod
    def _safe_filename(title: str) -> str:
        """Convert title to a safe filename."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in title)


# Auto-register
register_exporter("gpx", GpxExporter)
