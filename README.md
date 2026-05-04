stravart traces shapes on maps using real streets. give it coordinates, a shape, and a distance — it finds walkable/cyclable paths that approximate the geometry using OpenStreetMap data.

uv run stravart --lat 47.3769 --lon 8.5417 --shape heart --km 10

available shapes: heart, circle, square, lightning, star, triangle, infinity, spiral, cross

outputs .gpx and .html to output/.
