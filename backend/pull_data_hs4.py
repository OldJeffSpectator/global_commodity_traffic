r"""Pull HS4-level detailed trade data from UN Comtrade API.

Downloads one year at a time. Default: 2023.
Data is stored in bilateral_trades_hs4 table, separate from existing HS2 data.

Usage:
    cd backend
    .venv\Scripts\python pull_data_hs4.py                  # fetch 2023
    .venv\Scripts\python pull_data_hs4.py --year 2022      # fetch 2022
    .venv\Scripts\python pull_data_hs4.py --from-year 2020 --to-year 2023
"""
import os
import sys
import time
import argparse

for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine, Base, SessionLocal
from app.db.models import Country, CommodityDetail, BilateralTradeDetail

API_KEY = os.environ.get("COMTRADE_API_KEY", "3bf9dc83d1834c5f9f262476104a238e")

TOP_REPORTERS = [
    "842", "156", "276", "392", "826", "250", "380", "124", "410", "528",
    "356", "036", "076", "643", "682", "784", "360", "764", "484", "710",
]

# HS4 codes grouped by parent HS2 chapter
# Includes chapter 71 (gold/precious metals) not in the HS2 dataset
HS4_CODES = {
    "27": {
        "2701": "Coal",
        "2709": "Crude petroleum",
        "2710": "Refined petroleum products",
        "2711": "Natural gas (LNG/LPG)",
        "2713": "Petroleum coke & bitumen",
        "2716": "Electrical energy",
    },
    "10": {
        "1001": "Wheat",
        "1003": "Barley",
        "1005": "Corn (maize)",
        "1006": "Rice",
        "1007": "Grain sorghum",
        "1008": "Buckwheat, millet & other cereals",
    },
    "72": {
        "7201": "Pig iron",
        "7207": "Semi-finished iron/steel",
        "7208": "Hot-rolled flat steel (>=600mm)",
        "7209": "Cold-rolled flat steel (>=600mm)",
        "7210": "Plated/coated flat steel",
        "7213": "Hot-rolled bars & rods",
        "7214": "Other bars & rods (forged)",
        "7216": "Angles, shapes & sections",
        "7219": "Stainless steel flat-rolled",
    },
    "26": {
        "2601": "Iron ore",
        "2602": "Manganese ore",
        "2603": "Copper ore",
        "2604": "Nickel ore",
        "2606": "Aluminium ore (bauxite)",
        "2607": "Lead ore",
        "2608": "Zinc ore",
        "2609": "Tin ore",
        "2612": "Uranium/thorium ore",
        "2616": "Precious metal ores (gold/silver)",
    },
    "31": {
        "3102": "Nitrogen fertilizers",
        "3103": "Phosphate fertilizers",
        "3104": "Potassium fertilizers",
        "3105": "Mixed mineral/chemical fertilizers",
    },
    "44": {
        "4401": "Fuel wood & wood chips",
        "4403": "Wood in the rough (logs)",
        "4407": "Sawn lumber",
        "4410": "Particle board",
        "4411": "Fibreboard (MDF)",
        "4412": "Plywood",
    },
    "17": {
        "1701": "Cane or beet sugar",
        "1702": "Other sugars (fructose, glucose)",
        "1703": "Molasses",
        "1704": "Sugar confectionery",
    },
    "76": {
        "7601": "Unwrought aluminium",
        "7602": "Aluminium waste & scrap",
        "7604": "Aluminium bars, rods & profiles",
        "7606": "Aluminium plates, sheets & strips",
        "7607": "Aluminium foil",
    },
    "74": {
        "7401": "Copper matte",
        "7402": "Unrefined copper",
        "7403": "Refined copper (cathodes)",
        "7404": "Copper waste & scrap",
        "7407": "Copper bars, rods & profiles",
        "7408": "Copper wire",
        "7409": "Copper plates, sheets & strips",
    },
    "39": {
        "3901": "Polyethylene",
        "3902": "Polypropylene",
        "3903": "Polystyrene",
        "3904": "PVC (polyvinyl chloride)",
        "3907": "Polyesters & polycarbonates",
        "3920": "Plastic plates, sheets & film",
        "3923": "Plastic containers & packaging",
    },
    "71": {
        "7102": "Diamonds",
        "7106": "Silver",
        "7108": "Gold",
        "7110": "Platinum",
        "7113": "Jewellery",
    },
}

HS2_CATEGORIES = {
    "27": "Energy", "10": "Agriculture", "72": "Metals", "26": "Minerals",
    "31": "Chemicals", "44": "Agriculture", "17": "Agriculture",
    "76": "Metals", "74": "Metals", "39": "Chemicals", "71": "Precious Metals",
}


def seed_hs4_commodities(db):
    """Seed the HS4 commodity lookup table."""
    added = 0
    for hs2, codes in HS4_CODES.items():
        category = HS2_CATEGORIES.get(hs2, "Other")
        for hs4, name in codes.items():
            existing = db.query(CommodityDetail).filter_by(hs4_code=hs4).first()
            if not existing:
                db.add(CommodityDetail(
                    hs4_code=hs4, name=name, parent_hs2=hs2, category=category
                ))
                added += 1
    db.commit()
    total = db.query(CommodityDetail).count()
    print(f"[Seed] HS4 commodities: {total} total ({added} new)")


def fetch_comtrade_direct(api_key, reporter_code, cmd_codes, year, max_retries=3, timeout=90):
    """Fetch from Comtrade REST API directly with explicit timeout."""
    import requests
    import pandas as pd

    base_url = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
    params = {
        "reporterCode": reporter_code,
        "period": str(year),
        "cmdCode": cmd_codes,
        "flowCode": "X,M",
        "partnerCode": None,
        "partner2Code": None,
        "customsCode": None,
        "motCode": None,
        "maxRecords": 100000,
        "includeDesc": "true",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    # Remove None params
    params = {k: v for k, v in params.items() if v is not None}

    for attempt in range(max_retries):
        try:
            resp = requests.get(
                base_url, params=params, headers=headers,
                timeout=(15, timeout),  # (connect, read)
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"RATE_LIMIT(wait {wait}s)", end=" ", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"HTTP{resp.status_code}", end=" ", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return None

            data = resp.json()
            records = data.get("data", [])
            if not records:
                return None
            return pd.DataFrame(records)
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"TIMEOUT({attempt+1})", end=" ", flush=True)
                time.sleep(5)
            else:
                print(f"TIMEOUT(failed)", end=" ")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"ERR({attempt+1}:{e})", end=" ", flush=True)
                time.sleep(5)
            else:
                print(f"ERROR:{e}", end=" ")
                return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Pull HS4-level trade data from UN Comtrade")
    parser.add_argument("--year", type=int, default=2023, help="Single year (default: 2023)")
    parser.add_argument("--from-year", type=int, default=None, help="Start year (overrides --year)")
    parser.add_argument("--to-year", type=int, default=None, help="End year")
    parser.add_argument("--resume-from", type=int, default=0, help="Resume from reporter index (0-based)")
    args = parser.parse_args()

    if args.from_year and args.to_year:
        years = list(range(args.from_year, args.to_year + 1))
    else:
        years = [args.year]

    # All HS4 codes as a flat list
    all_hs4 = []
    for hs2, codes in HS4_CODES.items():
        for hs4 in codes:
            all_hs4.append((hs4, hs2))

    print(f"HS4 Detail Data Pull")
    print(f"{'='*60}")
    print(f"Years: {years[0]}-{years[-1]} ({len(years)} years)")
    print(f"Reporters: {len(TOP_REPORTERS)}")
    print(f"HS4 codes: {len(all_hs4)} (across {len(HS4_CODES)} chapters)")
    print(f"Strategy: 1 call/reporter (all codes), 90s timeout, direct REST API")
    print()

    # Create tables
    Base.metadata.create_all(bind=engine)
    print("[Init] Tables created")

    db = SessionLocal()
    seed_hs4_commodities(db)

    countries = db.query(Country).filter(Country.comtrade_code.isnot(None)).all()
    code_to_iso3 = {c.comtrade_code: c.iso3 for c in countries}
    print(f"[Init] Mapped {len(code_to_iso3)} comtrade codes to ISO3")

    # Build HS4 lookup for quick parent resolution
    hs4_to_parent = {hs4: hs2 for hs4, hs2 in all_hs4}
    all_cmd_codes = ",".join(code for code, _ in all_hs4)

    total_records = 0

    for year_idx, year in enumerate(years):
        print(f"\n{'='*60}")
        print(f"YEAR {year} ({year_idx+1}/{len(years)})")
        print(f"{'='*60}")

        year_added = 0
        for i, reporter_code in enumerate(TOP_REPORTERS):
            if i < args.resume_from:
                continue

            print(f"  [{i+1}/{len(TOP_REPORTERS)}] Reporter {reporter_code}...", end=" ", flush=True)

            df = fetch_comtrade_direct(API_KEY, reporter_code, all_cmd_codes, year)

            if df is None or (hasattr(df, 'empty') and df.empty):
                print("no data")
                time.sleep(2)
                continue

            print(f"{len(df)} rows", end=" ", flush=True)

            records = {}
            for _, row in df.iterrows():
                r_code = row.get("reporterCode")
                p_code = row.get("partnerCode")
                if r_code is None or p_code is None:
                    continue
                reporter_iso = code_to_iso3.get(int(r_code))
                partner_iso = code_to_iso3.get(int(p_code))
                if not reporter_iso or not partner_iso:
                    continue

                cmd_str = str(row.get("cmdCode", "")).zfill(4)
                if cmd_str not in hs4_to_parent:
                    continue

                flow = row.get("flowCode", "")
                value = float(row.get("primaryValue", 0) or 0)
                weight = float(row.get("netWgt", 0) or 0)

                key = (reporter_iso, partner_iso, cmd_str)
                if key not in records:
                    records[key] = {"export": 0, "import": 0, "weight": 0}
                if flow == "X":
                    records[key]["export"] += value
                elif flow == "M":
                    records[key]["import"] += value
                if weight > 0:
                    records[key]["weight"] += weight

            added = 0
            for (rep, par, hs4), vals in records.items():
                existing = (
                    db.query(BilateralTradeDetail)
                    .filter_by(
                        reporter_iso3=rep, partner_iso3=par,
                        commodity_hs4=hs4, year=year,
                    )
                    .first()
                )
                if existing:
                    if vals["export"] > 0:
                        existing.export_value_usd = vals["export"]
                    if vals["import"] > 0:
                        existing.import_value_usd = vals["import"]
                    if vals["weight"] > 0:
                        existing.weight_kg = vals["weight"]
                else:
                    db.add(BilateralTradeDetail(
                        reporter_iso3=rep, partner_iso3=par,
                        commodity_hs4=hs4, parent_hs2=hs4_to_parent[hs4],
                        year=year,
                        export_value_usd=vals["export"],
                        import_value_usd=vals["import"],
                        weight_kg=vals["weight"],
                    ))
                    added += 1

            db.commit()
            year_added += added
            total_records += added
            print(f"+{added}")

            time.sleep(2)

        print(f"\n  Year {year} total: {year_added} new records")

    db.close()
    print(f"\n{'='*60}")
    print(f"Done! Total new records: {total_records}")
    print(f"Database: {os.path.abspath('data/trade.db')}")


if __name__ == "__main__":
    main()
