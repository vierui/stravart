from __future__ import annotations

import warnings
from dataclasses import dataclass

import networkx as nx
import numpy as np
import osmnx as ox
from numpy.typing import NDArray

from stravart.geo import GeoPoints


@dataclass
class Route:
    lat: NDArray[np.float64]
    lon: NDArray[np.float64]
    total_distance_m: float


def load_graph(
    center_lat: float, center_lon: float, radius_m: float
) -> nx.MultiDiGraph:
    G = ox.graph_from_point(
        (center_lat, center_lon),
        dist=radius_m,
        network_type="walk",
    )
    # Project to UTM so nearest_nodes works without scikit-learn
    return ox.project_graph(G)


def snap_to_graph(
    G: nx.MultiDiGraph, geo_points: GeoPoints
) -> NDArray[np.int64]:
    # Project lat/lon to the graph's CRS (UTM) for snapping
    xs, ys = _project_coords(G, geo_points.lon, geo_points.lat)
    node_ids = ox.distance.nearest_nodes(G, X=xs, Y=ys)
    return np.array(node_ids, dtype=np.int64)


def _project_coords(
    G: nx.MultiDiGraph, lons: NDArray, lats: NDArray
) -> tuple[NDArray, NDArray]:
    """Project WGS84 lon/lat arrays to the graph's projected CRS."""
    import pyproj
    crs = G.graph["crs"]
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = transformer.transform(lons, lats)
    return np.array(xs), np.array(ys)


def compute_route(
    G: nx.MultiDiGraph, snapped_nodes: NDArray[np.int64], close_loop: bool = True
) -> Route:
    nodes_seq = _deduplicate_consecutive(snapped_nodes)
    if close_loop and len(nodes_seq) > 1 and nodes_seq[0] != nodes_seq[-1]:
        nodes_seq = np.append(nodes_seq, nodes_seq[0])

    all_lats: list[float] = []
    all_lons: list[float] = []
    total_dist = 0.0

    for i in range(len(nodes_seq) - 1):
        orig, dest = int(nodes_seq[i]), int(nodes_seq[i + 1])
        if orig == dest:
            continue
        try:
            path = nx.shortest_path(G, orig, dest, weight="length")
        except nx.NetworkXNoPath:
            warnings.warn(f"No path between nodes {orig} -> {dest}, skipping segment")
            continue

        lats, lons = _path_to_coords(G, path)
        dist = _path_distance(G, path)

        # Avoid duplicating the junction node
        if all_lats and lats:
            lats = lats[1:]
            lons = lons[1:]

        all_lats.extend(lats)
        all_lons.extend(lons)
        total_dist += dist

    return Route(
        lat=np.array(all_lats),
        lon=np.array(all_lons),
        total_distance_m=total_dist,
    )


def _deduplicate_consecutive(nodes: NDArray[np.int64]) -> NDArray[np.int64]:
    if len(nodes) == 0:
        return nodes
    mask = np.concatenate([[True], nodes[1:] != nodes[:-1]])
    return nodes[mask]


def _path_to_coords(
    G: nx.MultiDiGraph, path_nodes: list[int]
) -> tuple[list[float], list[float]]:
    import pyproj
    crs = G.graph["crs"]
    transformer = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xs = [G.nodes[n]["x"] for n in path_nodes]
    ys = [G.nodes[n]["y"] for n in path_nodes]
    lons, lats = transformer.transform(xs, ys)
    return list(lats), list(lons)


def _path_distance(G: nx.MultiDiGraph, path_nodes: list[int]) -> float:
    dist = 0.0
    for u, v in zip(path_nodes[:-1], path_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            dist += min(d.get("length", 0) for d in edge_data.values())
    return dist
