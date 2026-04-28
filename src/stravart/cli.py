from __future__ import annotations

import argparse
from pathlib import Path

from stravart.shapes import AVAILABLE_SHAPES


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stravart",
        description="GPS art route generator",
    )
    parser.add_argument("--lat", type=float, required=True, help="Center latitude")
    parser.add_argument("--lon", type=float, required=True, help="Center longitude")
    parser.add_argument(
        "--shape",
        type=str,
        default="heart",
        choices=AVAILABLE_SHAPES,
        help="Shape to trace (default: heart)",
    )
    parser.add_argument(
        "--km",
        type=float,
        default=5.0,
        help="Target route distance in km (default: 5.0)",
    )
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.0,
        help="Shape rotation in degrees (default: 0.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=120,
        help="Number of shape sample points (default: 120)",
    )

    args = parser.parse_args()

    from stravart.main import generate_route

    print(f"stravart: generating {args.shape} route")
    print(f"  center: ({args.lat}, {args.lon})")
    print(f"  target: {args.km} km")
    print()

    result = generate_route(
        center_lat=args.lat,
        center_lon=args.lon,
        shape_name=args.shape,
        target_distance_km=args.km,
        rotation_deg=args.rotation,
        num_points=args.points,
        output_dir=Path(args.output),
    )

    print()
    print(f"Done! Actual distance: {result['actual_distance_km']:.1f} km")
    print(f"  GPX: {result['gpx_path']}")
    print(f"  Map: {result['map_path']}")


if __name__ == "__main__":
    main()
