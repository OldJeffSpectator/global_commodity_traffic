"""Seed the database with countries and commodities."""
import json
import os
from sqlalchemy.orm import Session
from app.db.database import engine, Base, SessionLocal
from app.db.models import Country, Commodity

COMMODITIES = [
    ("27", "Mineral fuels & oils", "Energy"),
    ("10", "Cereals", "Agriculture"),
    ("72", "Iron and steel", "Metals"),
    ("26", "Ores, slag & ash", "Minerals"),
    ("31", "Fertilizers", "Chemicals"),
    ("44", "Wood", "Agriculture"),
    ("17", "Sugar", "Agriculture"),
    ("76", "Aluminium", "Metals"),
    ("74", "Copper", "Metals"),
    ("39", "Plastics", "Chemicals"),
]


def seed_commodities(db: Session):
    for code, name, category in COMMODITIES:
        existing = db.query(Commodity).filter_by(hs2_code=code).first()
        if not existing:
            db.add(Commodity(hs2_code=code, name=name, category=category))
    db.commit()


COMTRADE_CODES = {
    "USA": 842, "CHN": 156, "DEU": 276, "JPN": 392, "GBR": 826,
    "FRA": 250, "ITA": 380, "CAN": 124, "KOR": 410, "NLD": 528,
    "IND": 356, "AUS": 36, "BRA": 76, "RUS": 643, "SAU": 682,
    "ARE": 784, "IDN": 360, "THA": 764, "MEX": 484, "ZAF": 710,
    "SGP": 702, "MYS": 458, "VNM": 704, "TUR": 792, "POL": 616,
    "ESP": 724, "BEL": 56, "CHE": 756, "SWE": 752, "NOR": 578,
    "IRN": 364, "IRQ": 368, "NGA": 566, "EGY": 818, "ARG": 32,
    "CHL": 152, "COL": 170, "PER": 604, "PHL": 608, "PAK": 586,
    "BGD": 50, "KAZ": 398, "QAT": 634, "KWT": 414, "UKR": 804,
}


def seed_countries(db: Session):
    geojson_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "countries.geojson"
    )
    if not os.path.exists(geojson_path):
        print(f"Warning: {geojson_path} not found. Skipping country seed.")
        return

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in data["features"]:
        props = feature["properties"]
        iso3 = props.get("ISO_A3") or props.get("ADM0_A3")
        name = props.get("NAME") or props.get("ADMIN")

        if not iso3 or iso3 == "-99":
            continue

        geometry = feature["geometry"]
        centroid = _compute_centroid(geometry)
        if not centroid:
            continue

        comtrade_code = COMTRADE_CODES.get(iso3)

        existing = db.query(Country).filter_by(iso3=iso3).first()
        if existing:
            if comtrade_code and not existing.comtrade_code:
                existing.comtrade_code = comtrade_code
        else:
            db.add(Country(
                iso3=iso3,
                name=name,
                comtrade_code=comtrade_code,
                centroid_lat=centroid[1],
                centroid_lng=centroid[0],
            ))
    db.commit()


def _compute_centroid(geometry: dict) -> tuple | None:
    """Compute a rough centroid from GeoJSON geometry."""
    coords = []

    def extract_coords(obj):
        if isinstance(obj, list):
            if isinstance(obj[0], (int, float)):
                coords.append(obj)
            else:
                for item in obj:
                    extract_coords(item)

    if geometry["type"] == "Polygon":
        extract_coords(geometry["coordinates"][0])
    elif geometry["type"] == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            extract_coords(polygon[0])
    else:
        return None

    if not coords:
        return None

    avg_lng = sum(c[0] for c in coords) / len(coords)
    avg_lat = sum(c[1] for c in coords) / len(coords)
    return (avg_lng, avg_lat)


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_commodities(db)
        seed_countries(db)
        print("Database seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
