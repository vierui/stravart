from __future__ import annotations

from pathlib import Path

import numpy as np

from stravart.export import route_to_gpx, route_to_map
from stravart.geo import GeoPoints, estimate_initial_scale, shape_to_geo
from stravart.router import (
    Route,
    apply_affinity_weights,
    compute_route,
    filter_graph_to_corridor,
    load_graph,
    prune_dead_ends,
    snap_to_graph,
)
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

    graph_radius = max(initial_scale * 4.0, 2500)
    print(f"Downloading walk network ({graph_radius:.0f}m radius)...")
    G = load_graph(center_lat, center_lon, graph_radius)
    print(f"Graph: {len(G.nodes)} nodes, {len(G.edges)} edges")

    if len(G.nodes) < 10:
        raise RuntimeError(
            f"Too few walkable roads near ({center_lat}, {center_lon}). "
            "Check that --lat and --lon are correct (lat first, lon second)."
        )

    scale = initial_scale
    best_route: Route | None = None
    best_geo: GeoPoints | None = None
    best_diff = float("inf")

    for iteration in range(5):
        geo = shape_to_geo(shape, center_lat, center_lon, scale, rotation_deg)

        route = None
        snap = None
        used_buffer = "full"

        for buffer_m in [300, 500, 800]:
            G_corridor = filter_graph_to_corridor(G, geo, buffer_m)
            G_corridor = prune_dead_ends(G_corridor)
            if len(G_corridor.nodes) == 0:
                continue
            apply_affinity_weights(G_corridor, geo)
            snap = snap_to_graph(G_corridor, geo)
            candidate = compute_route(G_corridor, snap.node_ids, weight="affinity")

            if candidate.skipped_segments == 0 and candidate.total_distance_m > 0:
                route = candidate
                used_buffer = f"{buffer_m}"
                break

        if route is None:
            G_pruned = prune_dead_ends(G)
            snap = snap_to_graph(G_pruned, geo)
            route = compute_route(G_pruned, snap.node_ids)

        unique = len(np.unique(snap.node_ids))
        ratio = route.total_distance_m / target_m if target_m > 0 else 1.0
        print(
            f"  iter {iteration + 1}: scale={scale:.0f}m  "
            f"corridor={used_buffer}m  "
            f"snap: mean={snap.distances_m.mean():.0f}m max={snap.distances_m.max():.0f}m  "
            f"unique={unique}/{num_points}  "
            f"route={route.total_distance_m:.0f}m  "
            f"target={target_m:.0f}m  "
            f"ratio={ratio:.2f}"
        )

        diff = abs(route.total_distance_m - target_m)

        if diff < best_diff:
            best_diff = diff
            best_route = route
            best_geo = geo

        if abs(ratio - 1.0) < 0.10:
            break

        if route.total_distance_m > 0:
            scale = scale * (target_m / route.total_distance_m)

    assert best_route is not None
    assert best_geo is not None

    output_dir.mkdir(parents=True, exist_ok=True)
    basename = f"{shape_name}_{target_distance_km}km_{center_lat}_{center_lon}"
    gpx_path = output_dir / f"{basename}.gpx"
    map_path = output_dir / f"{basename}.html"

    route_to_gpx(best_route, gpx_path)
    route_to_map(best_route, best_geo, map_path)

    actual_km = best_route.total_distance_m / 1000
    return {
        "gpx_path": gpx_path,
        "map_path": map_path,
        "actual_distance_km": actual_km,
        "num_waypoints": best_route.lat.shape[0],
    }
