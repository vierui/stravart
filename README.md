 # stravart

`stravart` generates GPS art routes from a map.

give location, shape and target-distance. downloads the local walking network from OpenStreetMap, projects an 'ideal' geometric outline onto nearby streets. exports to `.gpx` and `.html`.

Contributor guide: see `AGENTS.md`.

## Quick Start

```sh
uv sync
```

exemple : heart, 10 km, Zürich:

```sh
uv run stravart --lat 47.3769 --lon 8.5417 --shape heart --km 10
```

current available shapes: `heart`, `circle`, `square`, `lightning`, `star`, `triangle`, `infinity`, `spiral`, `cross`.

## Notes
- distance may differ.
- latitude comes before longitude.
