from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

AVAILABLE_SHAPES = ["heart", "circle", "square", "lightning"]


@dataclass
class ShapePoints:
    x: NDArray[np.float64]
    y: NDArray[np.float64]

    @property
    def num_points(self) -> int:
        return len(self.x)

    @property
    def perimeter(self) -> float:
        dx = np.diff(np.append(self.x, self.x[0]))
        dy = np.diff(np.append(self.y, self.y[0]))
        return float(np.sum(np.sqrt(dx**2 + dy**2)))


def generate_shape(name: str, num_points: int = 50) -> ShapePoints:
    generators = {
        "heart": _heart,
        "circle": _circle,
        "square": _square,
        "lightning": _lightning,
    }
    if name not in generators:
        raise ValueError(f"Unknown shape '{name}'. Choose from: {AVAILABLE_SHAPES}")
    return _normalize(generators[name](num_points))


def _heart(num_points: int) -> ShapePoints:
    t_dense = np.linspace(0, 2 * np.pi, 1000, endpoint=False)
    x_dense = 16 * np.sin(t_dense) ** 3
    y_dense = (
        13 * np.cos(t_dense)
        - 5 * np.cos(2 * t_dense)
        - 2 * np.cos(3 * t_dense)
        - np.cos(4 * t_dense)
    )
    x, y = _arc_length_resample(x_dense, y_dense, num_points)
    return ShapePoints(x=x, y=y)


def _circle(num_points: int) -> ShapePoints:
    t = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    return ShapePoints(x=np.cos(t), y=np.sin(t))


def _square(num_points: int) -> ShapePoints:
    # Distribute points evenly along the 4 edges
    per_side = max(num_points // 4, 2)
    segments: list[tuple[NDArray, NDArray]] = []
    corners = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        t = np.linspace(0, 1, per_side, endpoint=False)
        segments.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
    x = np.concatenate([s[0] for s in segments])
    y = np.concatenate([s[1] for s in segments])
    return ShapePoints(x=x, y=y)


def _lightning(num_points: int) -> ShapePoints:
    # Lightning bolt polyline (closed loop)
    waypoints_x = [0.0, 0.4, 0.0, 0.6, 0.2, 0.6, 0.0]
    waypoints_y = [1.0, 0.3, 0.2, -1.0, -0.1, 0.0, 1.0]
    wx = np.array(waypoints_x)
    wy = np.array(waypoints_y)
    x, y = _interpolate_polyline(wx, wy, num_points)
    return ShapePoints(x=x, y=y)


def _arc_length_resample(
    x_dense: NDArray, y_dense: NDArray, num_points: int
) -> tuple[NDArray, NDArray]:
    dx = np.diff(x_dense)
    dy = np.diff(y_dense)
    seg_lengths = np.sqrt(dx**2 + dy**2)
    cum_length = np.concatenate([[0], np.cumsum(seg_lengths)])
    total = cum_length[-1]
    targets = np.linspace(0, total, num_points, endpoint=False)
    x_out = np.interp(targets, cum_length, x_dense)
    y_out = np.interp(targets, cum_length, y_dense)
    return x_out, y_out


def _interpolate_polyline(
    wx: NDArray, wy: NDArray, num_points: int
) -> tuple[NDArray, NDArray]:
    dx = np.diff(wx)
    dy = np.diff(wy)
    seg_lengths = np.sqrt(dx**2 + dy**2)
    cum_length = np.concatenate([[0], np.cumsum(seg_lengths)])
    total = cum_length[-1]
    targets = np.linspace(0, total, num_points, endpoint=False)
    x_out = np.interp(targets, cum_length, wx)
    y_out = np.interp(targets, cum_length, wy)
    return x_out, y_out


def _normalize(points: ShapePoints) -> ShapePoints:
    x = points.x - (points.x.max() + points.x.min()) / 2
    y = points.y - (points.y.max() + points.y.min()) / 2
    extent = max(x.max() - x.min(), y.max() - y.min())
    if extent > 0:
        x = x / (extent / 2)
        y = y / (extent / 2)
    return ShapePoints(x=x, y=y)
