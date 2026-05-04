from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

AVAILABLE_SHAPES = [
    "heart",
    "circle",
    "square",
    "lightning",
    "star",
    "triangle",
    "infinity",
    "spiral",
    "cross",
]


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
        "star": _star,
        "triangle": _triangle,
        "infinity": _infinity,
        "spiral": _spiral,
        "cross": _cross,
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
    x, y = _curvature_adaptive_resample(x_dense, y_dense, num_points)
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


def _star(num_points: int) -> ShapePoints:
    # 5-pointed star alternating between outer and inner radius
    n_tips = 5
    angles = np.linspace(0, 2 * np.pi, 2 * n_tips, endpoint=False)
    # Start from top (rotate by -pi/2)
    angles = angles - np.pi / 2
    radii = np.where(np.arange(2 * n_tips) % 2 == 0, 1.0, 0.4)
    wx = radii * np.cos(angles)
    wy = radii * np.sin(angles)
    # Close the loop
    wx = np.append(wx, wx[0])
    wy = np.append(wy, wy[0])
    x, y = _interpolate_polyline(wx, wy, num_points)
    return ShapePoints(x=x, y=y)


def _triangle(num_points: int) -> ShapePoints:
    # Equilateral triangle pointing up
    angles = np.array([np.pi / 2, np.pi / 2 + 2 * np.pi / 3, np.pi / 2 + 4 * np.pi / 3])
    wx = np.cos(angles)
    wy = np.sin(angles)
    wx = np.append(wx, wx[0])
    wy = np.append(wy, wy[0])
    x, y = _interpolate_polyline(wx, wy, num_points)
    return ShapePoints(x=x, y=y)


def _infinity(num_points: int) -> ShapePoints:
    # Lemniscate of Bernoulli (figure-8)
    t_dense = np.linspace(0, 2 * np.pi, 1000, endpoint=False)
    denom = 1 + np.sin(t_dense) ** 2
    x_dense = np.cos(t_dense) / denom
    y_dense = np.sin(t_dense) * np.cos(t_dense) / denom
    x, y = _arc_length_resample(x_dense, y_dense, num_points)
    return ShapePoints(x=x, y=y)


def _spiral(num_points: int) -> ShapePoints:
    # Spiral outward for 2.5 turns then straight back to center
    turns = 2.5
    n_spiral = int(num_points * 0.85)
    n_return = num_points - n_spiral
    t = np.linspace(0, turns * 2 * np.pi, n_spiral)
    r = t / (turns * 2 * np.pi)
    x_spiral = r * np.cos(t)
    y_spiral = r * np.sin(t)
    # Straight return from outer end back to center
    x_ret = np.linspace(x_spiral[-1], 0, n_return + 1)[1:]
    y_ret = np.linspace(y_spiral[-1], 0, n_return + 1)[1:]
    x = np.concatenate([x_spiral, x_ret])
    y = np.concatenate([y_spiral, y_ret])
    return ShapePoints(x=x, y=y)


def _cross(num_points: int) -> ShapePoints:
    # Plus/cross shape
    w = 0.3  # arm width (half)
    wx = np.array([w, w, 1, 1, w, w, -w, -w, -1, -1, -w, -w, w])
    wy = np.array([1, w, w, -w, -w, -1, -1, -w, -w, w, w, 1, 1])
    x, y = _interpolate_polyline(wx, wy, num_points)
    return ShapePoints(x=x, y=y)


def _curvature_adaptive_resample(
    x_dense: NDArray, y_dense: NDArray, num_points: int, kappa_min: float = 0.05
) -> tuple[NDArray, NDArray]:
    """Place more points where curvature is high (cusps, lobes)."""
    dx = np.gradient(x_dense)
    dy = np.gradient(y_dense)
    ddx = np.gradient(dx)
    ddy = np.gradient(dy)
    denom = (dx**2 + dy**2) ** 1.5
    kappa = np.abs(dx * ddy - dy * ddx) / np.where(denom > 1e-10, denom, 1e-10)
    kappa = np.nan_to_num(kappa, nan=0.0)
    density = kappa + kappa_min

    seg_lengths = np.sqrt(np.diff(x_dense) ** 2 + np.diff(y_dense) ** 2)
    weighted = seg_lengths * 0.5 * (density[:-1] + density[1:])
    cum_weighted = np.concatenate([[0], np.cumsum(weighted)])
    cum_arc = np.concatenate([[0], np.cumsum(seg_lengths)])

    targets = np.linspace(0, cum_weighted[-1], num_points, endpoint=False)
    # Map weighted targets back to arc-length positions, then to x/y
    arc_at_targets = np.interp(targets, cum_weighted, cum_arc)
    x_out = np.interp(arc_at_targets, cum_arc, x_dense)
    y_out = np.interp(arc_at_targets, cum_arc, y_dense)
    return x_out, y_out


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
