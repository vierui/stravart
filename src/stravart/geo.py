from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stravart.shapes import ShapePoints

METERS_PER_DEG_LAT = 111_111.0


@dataclass
class GeoPoints:
    lat: NDArray[np.float64]
    lon: NDArray[np.float64]


def meters_per_degree_lon(lat_deg: float) -> float:
    return METERS_PER_DEG_LAT * math.cos(math.radians(lat_deg))


def shape_to_geo(
    shape: ShapePoints,
    center_lat: float,
    center_lon: float,
    scale_meters: float,
    rotation_deg: float = 0.0,
) -> GeoPoints:
    x, y = shape.x.copy(), shape.y.copy()

    if rotation_deg != 0.0:
        x, y = _rotate(x, y, rotation_deg)

    # Scale from [-1, 1] to meters
    x_m = x * scale_meters
    y_m = y * scale_meters

    # Convert meters to degree offsets
    lat = center_lat + y_m / METERS_PER_DEG_LAT
    lon = center_lon + x_m / meters_per_degree_lon(center_lat)

    return GeoPoints(lat=lat, lon=lon)


def estimate_initial_scale(
    shape: ShapePoints, target_distance_m: float, overhead_factor: float = 2.0
) -> float:
    perimeter = shape.perimeter
    if perimeter == 0:
        return 500.0
    return target_distance_m / (perimeter * overhead_factor)


def _rotate(
    x: NDArray, y: NDArray, angle_deg: float
) -> tuple[NDArray, NDArray]:
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    x_r = x * cos_a - y * sin_a
    y_r = x * sin_a + y * cos_a
    return x_r, y_r
