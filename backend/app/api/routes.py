"""API routes for the global commodity traffic backend."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.db.models import (
    Country, Commodity, BilateralTrade, SyncStatus,
    Region, TradeRoute, TradeRouteSegment,
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


@router.get("/trade/{iso3}")
def get_trade_for_country(
    iso3: str,
    year: int | None = Query(None),
    commodity: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Get all bilateral trade records where this country is reporter or partner."""
    country = db.query(Country).filter_by(iso3=iso3.upper()).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    query = db.query(BilateralTrade).filter(
        (BilateralTrade.reporter_iso3 == iso3.upper())
        | (BilateralTrade.partner_iso3 == iso3.upper())
    )

    if year:
        query = query.filter(BilateralTrade.year == year)
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
        partner_iso = (
            t.partner_iso3 if t.reporter_iso3 == iso3.upper() else t.reporter_iso3
        )
        partner_info = countries_map.get(partner_iso, {})

        results.append({
            "partner_iso3": partner_iso,
            "partner_name": partner_info.get("name", "Unknown"),
            "partner_lat": partner_info.get("lat", 0),
            "partner_lng": partner_info.get("lng", 0),
            "commodity_code": t.commodity_code,
            "year": t.year,
            "export_value_usd": t.export_value_usd,
            "import_value_usd": t.import_value_usd,
            "weight_kg": t.weight_kg,
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
    db: Session = Depends(get_db),
):
    """Aggregated trade summary for a country."""
    country = db.query(Country).filter_by(iso3=iso3.upper()).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    base_query = db.query(BilateralTrade).filter(
        BilateralTrade.reporter_iso3 == iso3.upper()
    )
    if year:
        base_query = base_query.filter(BilateralTrade.year == year)

    # Totals
    totals = base_query.with_entities(
        func.sum(BilateralTrade.export_value_usd).label("total_exports"),
        func.sum(BilateralTrade.import_value_usd).label("total_imports"),
    ).first()

    # By commodity
    by_commodity = (
        base_query.with_entities(
            BilateralTrade.commodity_code,
            func.sum(BilateralTrade.export_value_usd).label("exports"),
            func.sum(BilateralTrade.import_value_usd).label("imports"),
        )
        .group_by(BilateralTrade.commodity_code)
        .all()
    )

    # Top partners by export value
    top_partners = (
        base_query.with_entities(
            BilateralTrade.partner_iso3,
            func.sum(
                BilateralTrade.export_value_usd + BilateralTrade.import_value_usd
            ).label("total_value"),
        )
        .group_by(BilateralTrade.partner_iso3)
        .order_by(
            func.sum(
                BilateralTrade.export_value_usd + BilateralTrade.import_value_usd
            ).desc()
        )
        .limit(10)
        .all()
    )

    # Resolve partner names
    partner_isos = [p.partner_iso3 for p in top_partners]
    partner_names = {
        c.iso3: c.name
        for c in db.query(Country).filter(Country.iso3.in_(partner_isos)).all()
    }

    return {
        "country": {"iso3": country.iso3, "name": country.name},
        "total_exports_usd": totals.total_exports or 0,
        "total_imports_usd": totals.total_imports or 0,
        "by_commodity": [
            {
                "commodity_code": row.commodity_code,
                "exports": row.exports or 0,
                "imports": row.imports or 0,
            }
            for row in by_commodity
        ],
        "top_partners": [
            {
                "iso3": row.partner_iso3,
                "name": partner_names.get(row.partner_iso3, "Unknown"),
                "total_value": row.total_value or 0,
            }
            for row in top_partners
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

    results = []
    for route in routes:
        segments = (
            db.query(TradeRouteSegment)
            .filter_by(route_id=route.id)
            .order_by(TradeRouteSegment.sequence_order)
            .all()
        )
        region_names = []
        region_centers = []
        for seg in segments:
            region = db.query(Region).filter_by(id=seg.region_id).first()
            if region:
                region_names.append(region.name)
                region_centers.append({"lat": region.center_lat, "lng": region.center_lng})

        partner = route.destination_iso3 if route.origin_iso3 == iso else route.origin_iso3
        partner_country = db.query(Country).filter_by(iso3=partner).first()

        results.append({
            "partner_iso3": partner,
            "partner_name": partner_country.name if partner_country else partner,
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
