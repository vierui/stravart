from __future__ import annotations

import warnings
from dataclasses import dataclass

import networkx as nx
import numpy as np
import osmnx as ox
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from stravart.geo import GeoPoints


@dataclass
class Route:
    lat: NDArray[np.float64]
    lon: NDArray[np.float64]
    total_distance_m: float
    skipped_segments: int = 0


@dataclass
class SnapResult:
    node_ids: NDArray[np.int64]
    distances_m: NDArray[np.float64]


def load_graph(
    center_lat: float, center_lon: float, radius_m: float
) -> nx.MultiDiGraph:
    G = ox.graph_from_point(
        (center_lat, center_lon),
        dist=radius_m,
        network_type="walk",
    )
    return ox.project_graph(G)


def prune_dead_ends(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Iteratively remove dead-end nodes (undirected degree <= 1)."""
    G = G.copy()
    while True:
        G_undir = G.to_undirected()
        dead = [n for n in G_undir.nodes() if G_undir.degree(n) <= 1]
        if not dead:
            break
        G.remove_nodes_from(dead)
    return G


def snap_to_graph(
    G: nx.MultiDiGraph, geo_points: GeoPoints, prefer_intersections: bool = True
) -> SnapResult:
    xs, ys = _project_coords(G, geo_points.lon, geo_points.lat)
    node_ids_list = list(G.nodes())
    node_xs = np.array([G.nodes[n]["x"] for n in node_ids_list])
    node_ys = np.array([G.nodes[n]["y"] for n in node_ids_list])
    tree = cKDTree(np.column_stack([node_xs, node_ys]))
    query_pts = np.column_stack([xs, ys])

    if prefer_intersections and len(node_ids_list) > 1:
        G_undir = G.to_undirected()
        degrees = np.array([G_undir.degree(n) for n in node_ids_list])
        k = min(10, len(node_ids_list))
        dists_k, idxs_k = tree.query(query_pts, k=k)
        if k == 1:
            dists_k = dists_k.reshape(-1, 1)
            idxs_k = idxs_k.reshape(-1, 1)

        chosen_ids = np.empty(len(xs), dtype=np.int64)
        chosen_dists = np.empty(len(xs))
        for i in range(len(xs)):
            nearest_dist = dists_k[i, 0]
            best_idx = idxs_k[i, 0]
            # Pick closest intersection (degree >= 3) within 2x nearest distance
            for j in range(k):
                idx = idxs_k[i, j]
                if dists_k[i, j] > nearest_dist * 2.0:
                    break
                if degrees[idx] >= 3:
                    best_idx = idx
                    break
            chosen_ids[i] = node_ids_list[best_idx]
            chosen_dists[i] = dists_k[i, list(idxs_k[i]).index(best_idx)]
    else:
        dists_q, idxs_q = tree.query(query_pts)
        chosen_ids = np.array([node_ids_list[i] for i in idxs_q], dtype=np.int64)
        chosen_dists = dists_q

    return SnapResult(node_ids=chosen_ids, distances_m=chosen_dists)


def filter_graph_to_corridor(
    G: nx.MultiDiGraph, geo_points: GeoPoints, buffer_m: float
) -> nx.MultiDiGraph:
    from shapely.geometry import LineString

    shape_xs, shape_ys = _project_coords(G, geo_points.lon, geo_points.lat)
    coords = list(zip(shape_xs.tolist(), shape_ys.tolist()))
    coords.append(coords[0])
    ideal_line = LineString(coords)
    corridor = ideal_line.buffer(buffer_m)

    keep_edges = []
    for u, v, k, data in G.edges(keys=True, data=True):
        geom = data.get("geometry")
        if geom is None:
            p1 = (G.nodes[u]["x"], G.nodes[u]["y"])
            p2 = (G.nodes[v]["x"], G.nodes[v]["y"])
            geom = LineString([p1, p2])
        if geom.intersects(corridor):
            keep_edges.append((u, v, k))

    return G.edge_subgraph(keep_edges).copy()


def apply_affinity_weights(
    G: nx.MultiDiGraph, geo_points: GeoPoints, alpha: float = 5.0
) -> None:
    """Add 'affinity' weight to edges: penalizes edges far from the ideal shape outline."""
    from shapely.geometry import LineString, Point

    shape_xs, shape_ys = _project_coords(G, geo_points.lon, geo_points.lat)
    coords = list(zip(shape_xs.tolist(), shape_ys.tolist()))
    coords.append(coords[0])
    ideal_line = LineString(coords)
    ref_dist = ideal_line.length / 20.0

    for u, v, k, data in G.edges(keys=True, data=True):
        length = data.get("length", 1.0)
        geom = data.get("geometry")
        if geom is not None:
            midpoint = geom.interpolate(0.5, normalized=True)
        else:
            mid_x = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2
            mid_y = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2
            midpoint = Point(mid_x, mid_y)
        dist_to_shape = ideal_line.distance(midpoint)
        data["affinity"] = length * (1.0 + alpha * dist_to_shape / ref_dist)


def compute_route(
    G: nx.MultiDiGraph,
    snapped_nodes: NDArray[np.int64],
    close_loop: bool = True,
    weight: str = "length",
) -> Route:
    nodes_seq = _deduplicate_consecutive(snapped_nodes)
    if close_loop and len(nodes_seq) > 1 and nodes_seq[0] != nodes_seq[-1]:
        nodes_seq = np.append(nodes_seq, nodes_seq[0])

    all_path_nodes: list[int] = []
    total_dist = 0.0
    skipped = 0

    for i in range(len(nodes_seq) - 1):
        orig, dest = int(nodes_seq[i]), int(nodes_seq[i + 1])
        if orig == dest:
            continue
        try:
            path = nx.shortest_path(G, orig, dest, weight=weight)
        except nx.NetworkXNoPath:
            warnings.warn(f"No path between nodes {orig} -> {dest}, skipping segment")
            skipped += 1
            continue

        dist = _path_distance(G, path)

        if all_path_nodes and path:
            path = path[1:]

        all_path_nodes.extend(path)
        total_dist += dist

    # Remove out-and-back spurs: shortcut when a node is revisited within a window
    all_path_nodes = _remove_spurs(all_path_nodes)
    total_dist = _path_distance(G, all_path_nodes)

    all_lats: list[float] = []
    all_lons: list[float] = []
    if all_path_nodes:
        all_lats, all_lons = _path_to_coords(G, all_path_nodes)

    return Route(
        lat=np.array(all_lats),
        lon=np.array(all_lons),
        total_distance_m=total_dist,
        skipped_segments=skipped,
    )


def _remove_spurs(path_nodes: list[int], max_spur_nodes: int = 40) -> list[int]:
    """Remove out-and-back spurs by shortcutting revisited nodes.

    When a node appears twice within a window of max_spur_nodes,
    the segment between is an out-and-back spur — remove it.
    """
    result = list(path_nodes)
    changed = True
    while changed:
        changed = False
        seen: dict[int, int] = {}
        for i, node in enumerate(result):
            if node in seen:
                prev_i = seen[node]
                gap = i - prev_i
                if 0 < gap <= max_spur_nodes:
                    result = result[:prev_i] + result[i:]
                    changed = True
                    break
            seen[node] = i
    return result


def _project_coords(
    G: nx.MultiDiGraph, lons: NDArray, lats: NDArray
) -> tuple[NDArray, NDArray]:
    """Project WGS84 lon/lat arrays to the graph's projected CRS."""
    import pyproj

    crs = G.graph["crs"]
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    xs, ys = transformer.transform(lons, lats)
    return np.array(xs), np.array(ys)


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

    if len(path_nodes) < 2:
        if path_nodes:
            x, y = G.nodes[path_nodes[0]]["x"], G.nodes[path_nodes[0]]["y"]
            lon, lat = transformer.transform(x, y)
            return [float(lat)], [float(lon)]
        return [], []

    all_xs: list[float] = []
    all_ys: list[float] = []

    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edge_data = G.get_edge_data(u, v)

        if edge_data:
            best_key = min(
                edge_data, key=lambda k: edge_data[k].get("length", float("inf"))
            )
            geom = edge_data[best_key].get("geometry")

            if geom is not None:
                coords = list(geom.coords)
                u_pos = (G.nodes[u]["x"], G.nodes[u]["y"])
                d_first = (coords[0][0] - u_pos[0]) ** 2 + (
                    coords[0][1] - u_pos[1]
                ) ** 2
                d_last = (coords[-1][0] - u_pos[0]) ** 2 + (
                    coords[-1][1] - u_pos[1]
                ) ** 2
                if d_last < d_first:
                    coords = coords[::-1]
                xs = [c[0] for c in coords]
                ys = [c[1] for c in coords]
            else:
                xs = [G.nodes[u]["x"], G.nodes[v]["x"]]
                ys = [G.nodes[u]["y"], G.nodes[v]["y"]]
        else:
            xs = [G.nodes[u]["x"], G.nodes[v]["x"]]
            ys = [G.nodes[u]["y"], G.nodes[v]["y"]]

        if all_xs:
            xs = xs[1:]
            ys = ys[1:]

        all_xs.extend(xs)
        all_ys.extend(ys)

    lons, lats = transformer.transform(all_xs, all_ys)
    return list(lats), list(lons)


def _path_distance(G: nx.MultiDiGraph, path_nodes: list[int]) -> float:
    dist = 0.0
    for u, v in zip(path_nodes[:-1], path_nodes[1:]):
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            dist += min(d.get("length", 0) for d in edge_data.values())
    return dist
