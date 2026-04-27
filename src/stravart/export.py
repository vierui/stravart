from __future__ import annotations

from pathlib import Path

import folium
import gpxpy
import gpxpy.gpx

from stravart.geo import GeoPoints
from stravart.router import Route


def route_to_gpx(route: Route, output_path: Path) -> None:
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name="stravart route")
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for lat, lon in zip(route.lat, route.lon):
        segment.points.append(gpxpy.gpx.GPXTrackPoint(float(lat), float(lon)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(gpx.to_xml())


def route_to_map(
    route: Route,
    ideal_shape: GeoPoints,
    output_path: Path,
) -> None:
    center_lat = float(route.lat.mean())
    center_lon = float(route.lon.mean())
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Ideal shape outline
    ideal_coords = list(zip(ideal_shape.lat.tolist(), ideal_shape.lon.tolist()))
    ideal_coords.append(ideal_coords[0])  # close the loop
    folium.PolyLine(
        ideal_coords, color="blue", weight=2, opacity=0.5, dash_array="10"
    ).add_to(m)

    # Actual route
    route_coords = list(zip(route.lat.tolist(), route.lon.tolist()))
    folium.PolyLine(route_coords, color="red", weight=3, opacity=0.8).add_to(m)

    # Start / end markers
    folium.Marker(
        [float(route.lat[0]), float(route.lon[0])],
        icon=folium.Icon(color="green"),
        tooltip="Start",
    ).add_to(m)
    folium.Marker(
        [float(route.lat[-1]), float(route.lon[-1])],
        icon=folium.Icon(color="red"),
        tooltip="End",
    ).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
