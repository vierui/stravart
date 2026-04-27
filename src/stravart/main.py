from __future__ import annotations

from pathlib import Path

from stravart.export import route_to_gpx, route_to_map
from stravart.geo import GeoPoints, estimate_initial_scale, shape_to_geo
from stravart.router import Route, compute_route, load_graph, snap_to_graph
from stravart.shapes import generate_shape


def generate_route(
    center_lat: float,
    center_lon: float,
    shape_name: str,
    target_distance_km: float,
    rotation_deg: float = 0.0,
    num_points: int = 50,
    output_dir: Path = Path("output"),
) -> dict:
    target_m = target_distance_km * 1000

    shape = generate_shape(shape_name, num_points)
    initial_scale = estimate_initial_scale(shape, target_m)

    # Load graph once with generous radius
    graph_radius = initial_scale * 2.5
    print(f"Downloading walk network ({graph_radius:.0f}m radius)...")
    G = load_graph(center_lat, center_lon, graph_radius)
    print(f"Graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

    # Iterative calibration
    scale = initial_scale
    best_route: Route | None = None
    best_geo: GeoPoints | None = None
    best_diff = float("inf")

    for iteration in range(5):
        geo = shape_to_geo(shape, center_lat, center_lon, scale, rotation_deg)
        nodes = snap_to_graph(G, geo)
        route = compute_route(G, nodes)

        diff = abs(route.total_distance_m - target_m)
        ratio = route.total_distance_m / target_m if target_m > 0 else 1.0
        print(
            f"  iter {iteration + 1}: scale={scale:.0f}m  "
            f"route={route.total_distance_m:.0f}m  "
            f"target={target_m:.0f}m  "
            f"ratio={ratio:.2f}"
        )

        if diff < best_diff:
            best_diff = diff
            best_route = route
            best_geo = geo

        if abs(ratio - 1.0) < 0.10:
            break

        # Adjust scale proportionally
        if route.total_distance_m > 0:
            scale = scale * (target_m / route.total_distance_m)

    assert best_route is not None
    assert best_geo is not None

    # Export
    output_dir.mkdir(parents=True, exist_ok=True)
    gpx_path = output_dir / f"{shape_name}_route.gpx"
    map_path = output_dir / f"{shape_name}_route.html"

    route_to_gpx(best_route, gpx_path)
    route_to_map(best_route, best_geo, map_path)

    actual_km = best_route.total_distance_m / 1000
    return {
        "gpx_path": gpx_path,
        "map_path": map_path,
        "actual_distance_km": actual_km,
        "num_waypoints": best_route.lat.shape[0],
    }
