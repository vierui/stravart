stravart traces shapes on maps using real streets.

give it a location, pick a shape, set a distance — it finds walkable paths that approximate the geometry using OpenStreetMap data.

uv run stravart --lat <latitude> --lon <longitude> --shape <shape> --km <distance>

available shapes: heart, star, infinity, circle, triangle, square, cross, lightning, spiral

outputs a .gpx and an interactive .html map to output/.
