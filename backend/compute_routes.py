r"""
Compute optimal trade routes for all country pairs using Dijkstra on the
unified graph (MARNET maritime + land borders + railway corridors).
Then label each route's path with named regions.

Usage:
    cd backend
    .venv\Scripts\python compute_routes.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine, Base, SessionLocal
from app.db.models import Country, BilateralTrade, Region, TradeRoute, TradeRouteSegment
from app.services.route_engine import build_graph
from sqlalchemy import func

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_regions():
    """Load region definitions and seed into DB."""
    regions_path = os.path.join(DATA_DIR, "regions.json")
    with open(regions_path, "r", encoding="utf-8") as f:
        regions_data = json.load(f)

    db = SessionLocal()
    try:
        for r in regions_data:
            existing = db.query(Region).filter_by(id=r["id"]).first()
            if not existing:
                db.add(Region(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    center_lat=r["center_lat"],
                    center_lng=r["center_lng"],
                ))
        db.commit()
        count = db.query(Region).count()
        print(f"[Regions] {count} regions in DB")
    finally:
        db.close()
    return regions_data


def point_in_bounds(lat: float, lng: float, bounds: dict) -> bool:
    """Check if point is within a bounding box. Handles antimeridian crossing."""
    if bounds is None:
        return False
    min_lat, max_lat = bounds["min_lat"], bounds["max_lat"]
    min_lng, max_lng = bounds["min_lng"], bounds["max_lng"]

    if lat < min_lat or lat > max_lat:
        return False

    if min_lng <= max_lng:
        return min_lng <= lng <= max_lng
    else:
        # Crosses antimeridian (e.g., Pacific Ocean: 120 to -100)
        return lng >= min_lng or lng <= max_lng


def classify_point(lat: float, lng: float, regions_data: list[dict]) -> int | None:
    """Find which region a point belongs to. Straits/canals take priority (smaller areas)."""
    # Priority: canal > strait > sea > ocean
    priority_order = ["canal", "strait", "sea", "ocean"]

    for region_type in priority_order:
        for r in regions_data:
            if r["type"] != region_type:
                continue
            if r.get("bounds") and point_in_bounds(lat, lng, r["bounds"]):
                return r["id"]
    return None


def label_route(path_coords: list[tuple[float, float]], regions_data: list[dict]) -> list[int]:
    """
    Given a path as [(lat, lng), ...], return an ordered list of region IDs
    (deduplicated consecutive regions).
    """
    region_sequence = []
    last_region = None

    for lat, lng in path_coords:
        region_id = classify_point(lat, lng, regions_data)
        if region_id and region_id != last_region:
            region_sequence.append(region_id)
            last_region = region_id

    return region_sequence


def main():
    # Create new tables
    Base.metadata.create_all(bind=engine)
    print("[Init] Tables created")

    # Seed regions
    regions_data = load_regions()

    db = SessionLocal()

    # Get all countries with centroids
    countries = db.query(Country).all()
    countries_list = [
        {"iso3": c.iso3, "centroid_lat": c.centroid_lat, "centroid_lng": c.centroid_lng}
        for c in countries
    ]
    print(f"[Init] {len(countries_list)} countries loaded")

    # Get unique country pairs from trade data
    pairs = (
        db.query(BilateralTrade.reporter_iso3, BilateralTrade.partner_iso3)
        .distinct()
        .all()
    )
    unique_pairs = set()
    for rep, par in pairs:
        key = tuple(sorted([rep, par]))
        unique_pairs.add(key)
    print(f"[Init] {len(unique_pairs)} unique country pairs to route")

    # Build graph
    print("\n[Graph] Building unified routing graph...")
    t0 = time.time()
    graph = build_graph(countries_list)
    print(f"[Graph] Built in {time.time()-t0:.1f}s")
    print(f"[Graph] Total nodes: {len(graph.nodes)}, Country ports: {len(graph.country_port_nodes)}")

    # Clear existing routes
    db.query(TradeRouteSegment).delete()
    db.query(TradeRoute).delete()
    db.commit()

    # Compute routes
    print(f"\n[Routing] Computing {len(unique_pairs)} routes via Dijkstra...")
    t0 = time.time()
    computed = 0
    failed = 0

    for i, (iso_a, iso_b) in enumerate(sorted(unique_pairs)):
        result = graph.dijkstra(iso_a, iso_b)

        if result is None:
            failed += 1
            continue

        path, total_cost = result
        path_coords = graph.get_path_coordinates(path)

        # Determine transport mode
        mode = "sea"
        if len(path_coords) <= 3:
            mode = "land"

        # Store route
        route = TradeRoute(
            origin_iso3=iso_a,
            destination_iso3=iso_b,
            total_cost=total_cost,
            transport_mode=mode,
            path_coords_json=json.dumps(
                [[round(lat, 4), round(lng, 4)] for lat, lng in path_coords]
            ),
        )
        db.add(route)
        db.flush()

        # Label segments
        region_ids = label_route(path_coords, regions_data)
        for seq, region_id in enumerate(region_ids):
            db.add(TradeRouteSegment(
                route_id=route.id,
                sequence_order=seq,
                region_id=region_id,
            ))

        computed += 1
        if (i + 1) % 50 == 0:
            db.commit()
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  [{i+1}/{len(unique_pairs)}] {computed} routed, {failed} failed ({rate:.1f} pairs/s)")

    db.commit()
    elapsed = time.time() - t0
    print(f"\n[Done] {computed} routes computed, {failed} failed in {elapsed:.1f}s")
    print(f"[Done] Database: {os.path.abspath(os.path.join(DATA_DIR, 'trade.db'))}")

    # Print some sample routes
    print("\n[Sample Routes]")
    samples = [("USA", "CHN"), ("SAU", "JPN"), ("BRA", "DEU"), ("AUS", "GBR")]
    for orig, dest in samples:
        route = db.query(TradeRoute).filter_by(origin_iso3=min(orig, dest), destination_iso3=max(orig, dest)).first()
        if not route:
            route = db.query(TradeRoute).filter_by(origin_iso3=orig, destination_iso3=dest).first()
        if route:
            segments = (
                db.query(TradeRouteSegment)
                .filter_by(route_id=route.id)
                .order_by(TradeRouteSegment.sequence_order)
                .all()
            )
            region_names = []
            for seg in segments:
                region = db.query(Region).filter_by(id=seg.region_id).first()
                if region:
                    region_names.append(region.name)
            print(f"  {orig} -> {dest}: cost={route.total_cost:.0f}, mode={route.transport_mode}")
            print(f"    Regions: {' -> '.join(region_names)}")
        else:
            print(f"  {orig} -> {dest}: NO ROUTE FOUND")

    db.close()


if __name__ == "__main__":
    main()
