"""API routes for the global commodity traffic backend."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import (
    Country, Commodity, BilateralTrade, SyncStatus,
    Region, TradeRoute, TradeRouteSegment, TradeRouteTransit,
)
from app.services.trade_fetcher import start_sync_background, get_current_sync_id

router = APIRouter(prefix="/api")


@router.get("/countries")
def list_countries(db: Session = Depends(get_db)):
    countries = db.query(Country).all()
    return [
        {
            "iso3": c.iso3,
            "name": c.name,
            "centroid_lat": c.centroid_lat,
            "centroid_lng": c.centroid_lng,
        }
        for c in countries
    ]


@router.get("/commodities")
def list_commodities(db: Session = Depends(get_db)):
    commodities = db.query(Commodity).all()
    return [
        {"hs2_code": c.hs2_code, "name": c.name, "category": c.category}
        for c in commodities
    ]


@router.get("/trade/year-range")
def get_year_range(db: Session = Depends(get_db)):
    """Return the min and max years available in the trade data."""
    result = db.query(
        func.min(BilateralTrade.year), func.max(BilateralTrade.year)
    ).first()
    return {"min_year": result[0] or 2000, "max_year": result[1] or 2023}


@router.get("/trade/{iso3}")
def get_trade_for_country(
    iso3: str,
    year: int | None = Query(None),
    year_start: int | None = Query(None),
    year_end: int | None = Query(None),
    commodity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Get bilateral trade records for a country/region.
    Uses own reports if available, otherwise partner-reported data (flipped)."""
    iso = iso3.upper()
    country = db.query(Country).filter_by(iso3=iso).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country/region not found")

    # Check if this country reports its own data
    has_own_reports = db.query(BilateralTrade).filter(
        BilateralTrade.reporter_iso3 == iso
    ).limit(1).first() is not None

    if has_own_reports:
        query = db.query(BilateralTrade).filter(BilateralTrade.reporter_iso3 == iso)
    else:
        query = db.query(BilateralTrade).filter(BilateralTrade.partner_iso3 == iso)

    if year:
        query = query.filter(BilateralTrade.year == year)
    elif year_start and year_end:
        query = query.filter(BilateralTrade.year >= year_start, BilateralTrade.year <= year_end)
    if commodity:
        query = query.filter(BilateralTrade.commodity_code == commodity)

    trades = query.all()

    # Build partner-country lookup for centroids
    partner_isos = set()
    for t in trades:
        partner_isos.add(t.reporter_iso3)
        partner_isos.add(t.partner_iso3)

    countries_map = {
        c.iso3: {"lat": c.centroid_lat, "lng": c.centroid_lng, "name": c.name}
        for c in db.query(Country).filter(Country.iso3.in_(partner_isos)).all()
    }

    results = []
    for t in trades:
        if has_own_reports:
            partner_iso = t.partner_iso3
            exp = t.export_value_usd or 0
            imp = t.import_value_usd or 0
        else:
            # Flip perspective: the reporter is our trade partner
            partner_iso = t.reporter_iso3
            exp = t.import_value_usd or 0  # Their import from us = our export
            imp = t.export_value_usd or 0  # Their export to us = our import

        partner_info = countries_map.get(partner_iso, {})

        results.append({
            "partner_iso3": partner_iso,
            "partner_name": partner_info.get("name", "Unknown"),
            "partner_lat": partner_info.get("lat", 0),
            "partner_lng": partner_info.get("lng", 0),
            "commodity_code": t.commodity_code,
            "year": t.year,
            "export_value_usd": exp,
            "import_value_usd": imp,
            "weight_kg": t.weight_kg or 0,
        })

    return {
        "country": {
            "iso3": country.iso3,
            "name": country.name,
            "lat": country.centroid_lat,
            "lng": country.centroid_lng,
        },
        "trades": results,
    }


@router.get("/trade/{iso3}/summary")
def get_trade_summary(
    iso3: str,
    year: int | None = Query(None),
    year_start: int | None = Query(None),
    year_end: int | None = Query(None),
    commodity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Aggregated trade summary for a country."""
    country = db.query(Country).filter_by(iso3=iso3.upper()).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country/region not found")

    iso = iso3.upper()

    # Check if this country reports its own data
    has_own_reports = db.query(BilateralTrade).filter(
        BilateralTrade.reporter_iso3 == iso
    ).limit(1).first() is not None

    if has_own_reports:
        # Use the country's own reported data
        base_query = db.query(BilateralTrade).filter(
            BilateralTrade.reporter_iso3 == iso
        )
    else:
        # Country doesn't report — use data reported by partners (flipped perspective)
        base_query = db.query(BilateralTrade).filter(
            BilateralTrade.partner_iso3 == iso
        )

    if year:
        base_query = base_query.filter(BilateralTrade.year == year)
    elif year_start and year_end:
        base_query = base_query.filter(BilateralTrade.year >= year_start, BilateralTrade.year <= year_end)
    if commodity:
        base_query = base_query.filter(BilateralTrade.commodity_code == commodity)

    trades = base_query.all()
    total_exports = 0.0
    total_imports = 0.0
    commodity_agg: dict[str, dict] = {}
    partner_agg: dict[str, float] = {}

    for t in trades:
        if has_own_reports:
            exp = t.export_value_usd or 0
            imp = t.import_value_usd or 0
            partner = t.partner_iso3
        else:
            # Flip: partner's export to us = our import, partner's import from us = our export
            exp = t.import_value_usd or 0
            imp = t.export_value_usd or 0
            partner = t.reporter_iso3

        total_exports += exp
        total_imports += imp

        if t.commodity_code not in commodity_agg:
            commodity_agg[t.commodity_code] = {"exports": 0.0, "imports": 0.0}
        commodity_agg[t.commodity_code]["exports"] += exp
        commodity_agg[t.commodity_code]["imports"] += imp

        partner_agg[partner] = partner_agg.get(partner, 0) + exp + imp

    # Top partners
    top_partner_list = sorted(partner_agg.items(), key=lambda x: x[1], reverse=True)[:10]
    partner_isos = [p[0] for p in top_partner_list]
    partner_names = {
        c.iso3: c.name
        for c in db.query(Country).filter(Country.iso3.in_(partner_isos)).all()
    }

    return {
        "country": {"iso3": country.iso3, "name": country.name},
        "total_exports_usd": total_exports,
        "total_imports_usd": total_imports,
        "by_commodity": [
            {
                "commodity_code": code,
                "exports": vals["exports"],
                "imports": vals["imports"],
            }
            for code, vals in sorted(
                commodity_agg.items(),
                key=lambda x: x[1]["exports"] + x[1]["imports"],
                reverse=True,
            )
        ],
        "top_partners": [
            {
                "iso3": p_iso,
                "name": partner_names.get(p_iso, "Unknown"),
                "total_value": p_val,
            }
            for p_iso, p_val in top_partner_list
        ],
    }


@router.post("/trade/sync")
def trigger_sync(year: int | None = Query(None)):
    """Trigger a background sync of trade data from UN Comtrade."""
    if get_current_sync_id():
        raise HTTPException(status_code=409, detail="Sync already in progress")

    sync_id = start_sync_background(year=year)
    if sync_id is None:
        raise HTTPException(status_code=409, detail="Sync already in progress")

    return {"sync_id": sync_id, "status": "started"}


@router.get("/trade/sync/status")
def get_sync_status(db: Session = Depends(get_db)):
    """Get the status of the most recent sync."""
    sync = db.query(SyncStatus).order_by(SyncStatus.id.desc()).first()
    if not sync:
        return {"status": "no_sync_run"}

    return {
        "id": sync.id,
        "status": sync.status,
        "started_at": sync.started_at,
        "completed_at": sync.completed_at,
        "records_fetched": sync.records_fetched,
        "error_message": sync.error_message,
    }


@router.get("/route/{origin_iso3}/{dest_iso3}")
def get_route(origin_iso3: str, dest_iso3: str, db: Session = Depends(get_db)):
    """Get the computed trade route between two countries."""
    o = origin_iso3.upper()
    d = dest_iso3.upper()

    # Routes are stored with sorted keys
    route = db.query(TradeRoute).filter_by(origin_iso3=min(o, d), destination_iso3=max(o, d)).first()
    if not route:
        route = db.query(TradeRoute).filter_by(origin_iso3=o, destination_iso3=d).first()
    if not route:
        route = db.query(TradeRoute).filter_by(origin_iso3=d, destination_iso3=o).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    segments = (
        db.query(TradeRouteSegment)
        .filter_by(route_id=route.id)
        .order_by(TradeRouteSegment.sequence_order)
        .all()
    )

    region_details = []
    for seg in segments:
        region = db.query(Region).filter_by(id=seg.region_id).first()
        if region:
            region_details.append({
                "sequence": seg.sequence_order,
                "region_id": region.id,
                "name": region.name,
                "type": region.type,
                "center_lat": region.center_lat,
                "center_lng": region.center_lng,
            })

    path_coords = json.loads(route.path_coords_json) if route.path_coords_json else []

    return {
        "origin_iso3": route.origin_iso3,
        "destination_iso3": route.destination_iso3,
        "total_cost": route.total_cost,
        "transport_mode": route.transport_mode,
        "path_coords": path_coords,
        "segments": region_details,
    }


@router.get("/routes/{iso3}")
def get_routes_for_country(iso3: str, db: Session = Depends(get_db)):
    """Get all computed routes involving a country (for visualization)."""
    iso = iso3.upper()
    routes = (
        db.query(TradeRoute)
        .filter((TradeRoute.origin_iso3 == iso) | (TradeRoute.destination_iso3 == iso))
        .all()
    )

    if not routes:
        return {"country": iso, "routes": []}

    route_ids = [r.id for r in routes]

    # Batch-fetch all segments for these routes
    all_segments = (
        db.query(TradeRouteSegment)
        .filter(TradeRouteSegment.route_id.in_(route_ids))
        .order_by(TradeRouteSegment.route_id, TradeRouteSegment.sequence_order)
        .all()
    )

    # Batch-fetch all regions
    region_ids = list(set(seg.region_id for seg in all_segments))
    all_regions = db.query(Region).filter(Region.id.in_(region_ids)).all() if region_ids else []
    region_map = {r.id: r for r in all_regions}

    # Group segments by route_id
    segments_by_route: dict[int, list] = {}
    for seg in all_segments:
        segments_by_route.setdefault(seg.route_id, []).append(seg)

    # Batch-fetch all partner countries
    partner_isos = set()
    for route in routes:
        partner = route.destination_iso3 if route.origin_iso3 == iso else route.origin_iso3
        partner_isos.add(partner)
    partner_countries = db.query(Country).filter(Country.iso3.in_(partner_isos)).all()
    country_map = {c.iso3: c.name for c in partner_countries}

    results = []
    for route in routes:
        segs = segments_by_route.get(route.id, [])
        region_names = []
        region_centers = []
        for seg in segs:
            region = region_map.get(seg.region_id)
            if region:
                region_names.append(region.name)
                region_centers.append({"lat": region.center_lat, "lng": region.center_lng})

        partner = route.destination_iso3 if route.origin_iso3 == iso else route.origin_iso3

        results.append({
            "partner_iso3": partner,
            "partner_name": country_map.get(partner, partner),
            "total_cost": route.total_cost,
            "transport_mode": route.transport_mode,
            "region_names": region_names,
            "region_centers": region_centers,
            "path_coords": json.loads(route.path_coords_json) if route.path_coords_json else [],
        })

    return {"country": iso, "routes": results}


@router.get("/regions")
def list_regions(db: Session = Depends(get_db)):
    """List all named regions."""
    regions = db.query(Region).all()
    return [
        {"id": r.id, "name": r.name, "type": r.type, "center_lat": r.center_lat, "center_lng": r.center_lng}
        for r in regions
    ]


@router.get("/region/{region_id}/routes")
def get_routes_through_region(
    region_id: int,
    db: Session = Depends(get_db),
):
    """Get all trade routes that pass through a given region."""
    region = db.query(Region).filter_by(id=region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    segments = db.query(TradeRouteSegment).filter_by(region_id=region_id).all()
    route_ids = list(set(seg.route_id for seg in segments))

    routes = db.query(TradeRoute).filter(TradeRoute.id.in_(route_ids)).all() if route_ids else []

    results = []
    for route in routes:
        origin = db.query(Country).filter_by(iso3=route.origin_iso3).first()
        dest = db.query(Country).filter_by(iso3=route.destination_iso3).first()
        results.append({
            "origin_iso3": route.origin_iso3,
            "origin_name": origin.name if origin else route.origin_iso3,
            "destination_iso3": route.destination_iso3,
            "destination_name": dest.name if dest else route.destination_iso3,
            "total_cost": route.total_cost,
            "transport_mode": route.transport_mode,
            "path_coords": json.loads(route.path_coords_json) if route.path_coords_json else [],
        })

    return {
        "region": {"id": region.id, "name": region.name, "type": region.type},
        "route_count": len(results),
        "routes": results,
    }


@router.get("/region/{region_id}/trade-stats")
def get_trade_stats_through_region(
    region_id: int,
    year_start: int | None = Query(None),
    year_end: int | None = Query(None),
    commodity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregated trade data for all routes passing through a region."""
    region = db.query(Region).filter_by(id=region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    segments = db.query(TradeRouteSegment).filter_by(region_id=region_id).all()
    route_ids = list(set(seg.route_id for seg in segments))

    if not route_ids:
        return {
            "region": {"id": region.id, "name": region.name, "type": region.type},
            "route_count": 0,
            "total_export_usd": 0,
            "total_import_usd": 0,
            "top_pairs": [],
        }

    routes = db.query(TradeRoute).filter(TradeRoute.id.in_(route_ids)).all()

    # Collect all country pairs on these routes
    pairs = [(r.origin_iso3, r.destination_iso3) for r in routes]

    total_exports = 0.0
    total_imports = 0.0
    pair_values = []

    for origin, dest in pairs:
        trade_query = db.query(
            func.sum(BilateralTrade.export_value_usd),
            func.sum(BilateralTrade.import_value_usd),
        ).filter(
            ((BilateralTrade.reporter_iso3 == origin) & (BilateralTrade.partner_iso3 == dest))
            | ((BilateralTrade.reporter_iso3 == dest) & (BilateralTrade.partner_iso3 == origin))
        )

        if year_start and year_end:
            trade_query = trade_query.filter(
                BilateralTrade.year >= year_start, BilateralTrade.year <= year_end
            )
        if commodity:
            trade_query = trade_query.filter(BilateralTrade.commodity_code == commodity)

        result = trade_query.first()
        exp = result[0] or 0
        imp = result[1] or 0
        total_exports += exp
        total_imports += imp
        pair_values.append((origin, dest, exp + imp))

    pair_values.sort(key=lambda x: x[2], reverse=True)
    top_pairs = pair_values[:10]

    country_names = {}
    all_isos = set()
    for o, d, _ in top_pairs:
        all_isos.add(o)
        all_isos.add(d)
    for c in db.query(Country).filter(Country.iso3.in_(all_isos)).all():
        country_names[c.iso3] = c.name

    # Get top 3 commodities per pair with direction (origin→destination export value)
    commodity_names = {c.hs2_code: c.name for c in db.query(Commodity).all()}
    pair_details = []
    for o, d, v in top_pairs:
        # Get top commodities by total volume
        comm_query = db.query(
            BilateralTrade.commodity_code,
            func.sum(BilateralTrade.export_value_usd).label("fwd"),
        ).filter(
            BilateralTrade.reporter_iso3 == o,
            BilateralTrade.partner_iso3 == d,
        )
        if year_start and year_end:
            comm_query = comm_query.filter(
                BilateralTrade.year >= year_start, BilateralTrade.year <= year_end
            )
        if commodity:
            comm_query = comm_query.filter(BilateralTrade.commodity_code == commodity)
        fwd_comms = {row.commodity_code: (row.fwd or 0) for row in comm_query.group_by(BilateralTrade.commodity_code).all()}

        # Reverse direction
        rev_query = db.query(
            BilateralTrade.commodity_code,
            func.sum(BilateralTrade.export_value_usd).label("rev"),
        ).filter(
            BilateralTrade.reporter_iso3 == d,
            BilateralTrade.partner_iso3 == o,
        )
        if year_start and year_end:
            rev_query = rev_query.filter(
                BilateralTrade.year >= year_start, BilateralTrade.year <= year_end
            )
        if commodity:
            rev_query = rev_query.filter(BilateralTrade.commodity_code == commodity)
        rev_comms = {row.commodity_code: (row.rev or 0) for row in rev_query.group_by(BilateralTrade.commodity_code).all()}

        # Merge and rank by total
        all_codes = set(fwd_comms.keys()) | set(rev_comms.keys())
        ranked = []
        for code in all_codes:
            fwd_val = fwd_comms.get(code, 0)
            rev_val = rev_comms.get(code, 0)
            ranked.append((code, fwd_val, rev_val, fwd_val + rev_val))
        ranked.sort(key=lambda x: x[3], reverse=True)

        pair_details.append({
            "origin_iso3": o,
            "origin_name": country_names.get(o, o),
            "destination_iso3": d,
            "destination_name": country_names.get(d, d),
            "total_value": v,
            "top_commodities": [
                {
                    "code": code,
                    "name": commodity_names.get(code, code),
                    "fwd_value": fwd_val,
                    "rev_value": rev_val,
                }
                for code, fwd_val, rev_val, _ in ranked[:3]
            ],
        })

    return {
        "region": {"id": region.id, "name": region.name, "type": region.type},
        "route_count": len(routes),
        "total_export_usd": total_exports,
        "total_import_usd": total_imports,
        "top_pairs": pair_details,
    }


@router.get("/country/{iso3}/transit")
def get_transit_through_country(
    iso3: str,
    year_start: int | None = Query(None),
    year_end: int | None = Query(None),
    commodity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Get routes and trade stats for routes that transit through a country."""
    iso = iso3.upper()
    country = db.query(Country).filter_by(iso3=iso).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country/region not found")

    transits = db.query(TradeRouteTransit).filter_by(transit_iso3=iso).all()
    route_ids = list(set(t.route_id for t in transits))

    if not route_ids:
        return {
            "country": {"iso3": iso, "name": country.name},
            "transit_route_count": 0,
            "total_transit_value": 0,
            "top_pairs": [],
        }

    routes = db.query(TradeRoute).filter(TradeRoute.id.in_(route_ids)).all()

    # Get trade values for each route pair
    commodity_names = {c.hs2_code: c.name for c in db.query(Commodity).all()}
    pair_values = []
    for route in routes:
        trade_query = db.query(
            func.sum(BilateralTrade.export_value_usd + BilateralTrade.import_value_usd),
        ).filter(
            ((BilateralTrade.reporter_iso3 == route.origin_iso3) & (BilateralTrade.partner_iso3 == route.destination_iso3))
            | ((BilateralTrade.reporter_iso3 == route.destination_iso3) & (BilateralTrade.partner_iso3 == route.origin_iso3))
        )
        if year_start and year_end:
            trade_query = trade_query.filter(
                BilateralTrade.year >= year_start, BilateralTrade.year <= year_end
            )
        if commodity:
            trade_query = trade_query.filter(BilateralTrade.commodity_code == commodity)
        total = trade_query.scalar() or 0
        pair_values.append((route.origin_iso3, route.destination_iso3, total))

    pair_values.sort(key=lambda x: x[2], reverse=True)
    total_transit_value = sum(v for _, _, v in pair_values)

    # Top 10 pairs with top 3 commodities each
    country_names = {}
    all_isos = set()
    for o, d, _ in pair_values[:10]:
        all_isos.add(o)
        all_isos.add(d)
    for c in db.query(Country).filter(Country.iso3.in_(all_isos)).all():
        country_names[c.iso3] = c.name

    top_pairs = []
    for o, d, v in pair_values[:10]:
        # Top 3 commodities for this pair
        comm_query = db.query(
            BilateralTrade.commodity_code,
            func.sum(BilateralTrade.export_value_usd + BilateralTrade.import_value_usd).label("total"),
        ).filter(
            ((BilateralTrade.reporter_iso3 == o) & (BilateralTrade.partner_iso3 == d))
            | ((BilateralTrade.reporter_iso3 == d) & (BilateralTrade.partner_iso3 == o))
        )
        if year_start and year_end:
            comm_query = comm_query.filter(BilateralTrade.year >= year_start, BilateralTrade.year <= year_end)
        if commodity:
            comm_query = comm_query.filter(BilateralTrade.commodity_code == commodity)
        top_comms = (
            comm_query.group_by(BilateralTrade.commodity_code)
            .order_by(func.sum(BilateralTrade.export_value_usd + BilateralTrade.import_value_usd).desc())
            .limit(3)
            .all()
        )

        top_pairs.append({
            "origin_iso3": o,
            "origin_name": country_names.get(o, o),
            "destination_iso3": d,
            "destination_name": country_names.get(d, d),
            "total_value": v,
            "top_commodities": [
                {"code": row.commodity_code, "name": commodity_names.get(row.commodity_code, row.commodity_code), "value": row.total or 0}
                for row in top_comms
            ],
        })

    return {
        "country": {"iso3": iso, "name": country.name},
        "transit_route_count": len(route_ids),
        "total_transit_value": total_transit_value,
        "top_pairs": top_pairs,
    }


@router.get("/country/{iso3}/transit-routes")
def get_transit_route_paths(iso3: str, db: Session = Depends(get_db)):
    """Get route path coordinates for all routes transiting through a country."""
    iso = iso3.upper()
    transits = db.query(TradeRouteTransit).filter_by(transit_iso3=iso).all()
    route_ids = list(set(t.route_id for t in transits))

    if not route_ids:
        return {"country": iso, "routes": []}

    routes = db.query(TradeRoute).filter(TradeRoute.id.in_(route_ids)).all()
    results = []
    for route in routes:
        origin = db.query(Country).filter_by(iso3=route.origin_iso3).first()
        dest = db.query(Country).filter_by(iso3=route.destination_iso3).first()
        results.append({
            "origin_iso3": route.origin_iso3,
            "origin_name": origin.name if origin else route.origin_iso3,
            "destination_iso3": route.destination_iso3,
            "destination_name": dest.name if dest else route.destination_iso3,
            "total_cost": route.total_cost,
            "transport_mode": route.transport_mode,
            "path_coords": json.loads(route.path_coords_json) if route.path_coords_json else [],
        })

    return {"country": iso, "routes": results}
