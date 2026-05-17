# AGENTS.md

## Repository Layout

```
src/stravart/
  cli.py       command-line interface (argparse, entry point)
  main.py      route generation pipeline (orchestrates all modules)
  shapes.py    parametric shape definitions, normalized to [-1, 1]
  geo.py       convert normalized shapes to lat/lon coordinates
  router.py    OSMnx graph loading, corridor filtering, snapping, path computation
  export.py    GPX and Folium HTML map export
```

Entry point: `stravart = "stravart.cli:main"` (see `pyproject.toml`).

## Dependencies

Python >=3.10. Managed with `uv`.

- `osmnx` — download and project OpenStreetMap walking networks
- `networkx` — graph operations and shortest paths
- `folium` — interactive HTML map rendering
- `gpxpy` — GPX file generation
- `numpy` — coordinate arrays and math
- `scipy` — spatial indexing (cKDTree for snapping)
- `shapely` — corridor geometry (used inside `router.py`)
- `pyproj` — CRS projection (used inside `router.py`)

## Pipeline

`main.generate_route` runs these steps:

1. `shapes.generate_shape` — produce a `ShapePoints(x, y)` normalized to [-1, 1].
2. `geo.estimate_initial_scale` — guess a starting scale from shape perimeter and target distance.
3. `router.load_graph` — download walking network via `osmnx`, project to local CRS.
4. `geo.shape_to_geo` — scale, rotate, and convert shape to `GeoPoints(lat, lon)`.
5. `router.filter_graph_to_corridor` — keep only edges within a buffer around the ideal outline.
6. `router.prune_dead_ends` — iteratively remove degree-1 nodes.
7. `router.apply_affinity_weights` — penalize edges far from the ideal shape.
8. `router.snap_to_graph` — snap shape sample points to nearby graph nodes (prefers intersections).
9. `router.compute_route` — shortest-path segments between snapped nodes, spur removal, loop closure.
10. Iterate steps 4–9 up to 5 times, adjusting scale to converge on target distance.
11. `export.route_to_gpx` + `export.route_to_map` — write `.gpx` and `.html`.

## Key Types

- `ShapePoints(x, y)` — normalized shape coordinates. Properties: `num_points`, `perimeter`.
- `GeoPoints(lat, lon)` — WGS84 coordinates.
- `Route(lat, lon, total_distance_m, skipped_segments)` — final route.
- `SnapResult(node_ids, distances_m)` — snapping results.

## CLI

```
uv run stravart --lat <float> --lon <float> --shape <name> --km <float> \
  [--rotation <degrees>] [--points <int>] [--output <dir>]
```

Defaults: shape=heart, km=5.0, rotation=0.0, points=50, output=output/.

## Adding a Shape

1. Add a `_shapename(num_points) -> ShapePoints` function in `shapes.py`.
2. Add the name to `AVAILABLE_SHAPES` list and the `generators` dict in `generate_shape`.
3. Shapes must return coordinates that `_normalize` maps to [-1, 1]. Closed loops work best.

## Outputs

Each run writes to `output/` (or `--output`):

```
<shape>_<km>km_<lat>_<lon>.gpx
<shape>_<km>km_<lat>_<lon>.html
```

The HTML map shows the ideal shape (blue dashed) and the street route (red solid) with start/end markers.
