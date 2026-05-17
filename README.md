# stravart

`stravart` generates GPS art routes from real streets.

Give it a location, a shape, and a target distance. It downloads the local walking network from OpenStreetMap, projects an ideal geometric outline onto nearby streets, and exports both a `.gpx` route and an interactive `.html` map.

## Repository Layout

- `src/stravart/cli.py` command-line interface.
- `src/stravart/main.py` route generation pipeline.
- `src/stravart/shapes.py` parametric shape definitions.
- `src/stravart/geo.py` conversion from normalized shapes to latitude/longitude coordinates.
- `src/stravart/router.py` street-network loading, snapping, corridor filtering, and path computation.
- `src/stravart/export.py` GPX and Folium map export.

## Quick Start

Install dependencies with `uv`:

```sh
uv sync
```

Generate a 5 km heart route around Zürich:

```sh
uv run stravart --lat 47.3769 --lon 8.5417 --shape heart --km 5
```

Rotate the shape and increase the number of sampled points:

```sh
uv run stravart \
  --lat 47.3769 \
  --lon 8.5417 \
  --shape star \
  --km 8 \
  --rotation 25 \
  --points 80
```

Write outputs to a custom directory:

```sh
uv run stravart --lat 47.3769 --lon 8.5417 --shape circle --km 6 --output routes/
```

## Available Shapes

```text
heart, circle, square, lightning, star, triangle, infinity, spiral, cross
```

## How It Works

1. Generate a normalized geometric shape.
2. Scale and rotate the shape around the requested latitude/longitude.
3. Download the local walking network with OSMnx.
4. Filter the graph to a corridor around the ideal outline.
5. Snap shape sample points to nearby graph nodes.
6. Compute shortest-path segments between snapped points.
7. Adjust scale over several iterations to approach the target distance.
8. Export the final route as GPX and render an interactive HTML map.

## CLI Options

```sh
uv run stravart \
  --lat <latitude> \
  --lon <longitude> \
  --shape <shape> \
  --km <distance> \
  --rotation <degrees> \
  --points <sample-points> \
  --output <directory>
```

Key arguments:

* `--lat`, `--lon`: center point of the route.
* `--shape`: shape to trace. Defaults to `heart`.
* `--km`: target route distance in kilometers. Defaults to `5.0`.
* `--rotation`: rotate the shape in degrees. Defaults to `0.0`.
* `--points`: number of sampled points used to trace the shape. Defaults to `50`.
* `--output`: output directory. Defaults to `output/`.

## Outputs

Each run writes two files:

* `.gpx` route file for Strava, Garmin, Komoot, and other GPS tools.
* `.html` interactive Folium map showing the ideal shape and the computed street route.

Example output names:

```text
output/heart_5.0km_47.3769_8.5417.gpx
output/heart_5.0km_47.3769_8.5417.html
```

## Notes

* Route quality depends on the density and geometry of the local walking network.
* Dense city grids usually produce cleaner shapes than sparse rural areas.
* The actual route distance may differ slightly from the requested distance because the route must follow real streets.
* Internet access is required when downloading OpenStreetMap data.
* Latitude comes before longitude.
