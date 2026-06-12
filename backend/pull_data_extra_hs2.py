r"""Pull additional HS2-level trade data from UN Comtrade API.

Adds major commodity chapters not in the original 10.
Data goes into the SAME bilateral_trades table as existing data.

Usage:
    cd backend
    .venv\Scripts\python pull_data_extra_hs2.py --year 2023
    .venv\Scripts\python pull_data_extra_hs2.py --from-year 2020 --to-year 2023
"""
import os
import sys
import time
import argparse
import pandas as pd

for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine, Base, SessionLocal
from app.db.models import Country, Commodity, BilateralTrade

API_KEY = os.environ.get("COMTRADE_API_KEY", "3bf9dc83d1834c5f9f262476104a238e")

TOP_REPORTERS = [
    "842", "156", "276", "392", "826", "250", "380", "124", "410", "528",
    "356", "036", "076", "643", "682", "784", "360", "764", "484", "710",
]

# New HS2 chapters to add (not in the original 10)
EXTRA_COMMODITIES = [
    ("84", "Machinery & mechanical appliances", "Machinery"),
    ("85", "Electrical machinery & electronics", "Electronics"),
    ("87", "Vehicles & automobiles", "Vehicles"),
    ("71", "Precious metals (gold, silver, platinum)", "Precious Metals"),
    ("30", "Pharmaceuticals", "Chemicals"),
    ("90", "Optical & medical instruments", "Machinery"),
    ("29", "Organic chemicals", "Chemicals"),
    ("61", "Clothing (knitted)", "Textiles"),
    ("62", "Clothing (woven)", "Textiles"),
    ("03", "Fish & seafood", "Agriculture"),
    ("12", "Oilseeds (soybeans, etc.)", "Agriculture"),
    ("88", "Aircraft & spacecraft", "Vehicles"),
    ("28", "Inorganic chemicals", "Chemicals"),
    ("73", "Articles of iron or steel", "Metals"),
    ("48", "Paper & paperboard", "Agriculture"),
    ("40", "Rubber", "Chemicals"),
    ("52", "Cotton", "Textiles"),
]


def seed_extra_commodities(db):
    """Add new commodity entries to the commodities table."""
    added = 0
    for code, name, category in EXTRA_COMMODITIES:
        existing = db.query(Commodity).filter_by(hs2_code=code).first()
        if not existing:
            db.add(Commodity(hs2_code=code, name=name, category=category))
            added += 1
    db.commit()
    total = db.query(Commodity).count()
    print(f"[Seed] Commodities: {total} total ({added} new)")


def fetch_comtrade(api_key, reporter_code, cmd_codes, year, max_retries=3, timeout=90):
    """Fetch from Comtrade REST API with explicit timeout."""
    import requests
    import pandas as pd

    base_url = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
    params = {
        "reporterCode": reporter_code,
        "period": str(year),
        "cmdCode": cmd_codes,
        "flowCode": "X,M",
        "maxRecords": 100000,
        "includeDesc": "true",
    }
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    for attempt in range(max_retries):
        try:
            resp = requests.get(
                base_url, params=params, headers=headers,
                timeout=(15, timeout),
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
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"ERR({attempt+1})", end=" ", flush=True)
                time.sleep(5)
            else:
                print(f"ERROR:{e}", end=" ")
                return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Pull extra HS2 trade data")
    parser.add_argument("--year", type=int, default=2023, help="Single year (default: 2023)")
    parser.add_argument("--from-year", type=int, default=None)
    parser.add_argument("--to-year", type=int, default=None)
    parser.add_argument("--resume-from", type=int, default=0, help="Reporter index to resume from")
    args = parser.parse_args()

    if args.from_year and args.to_year:
        years = list(range(args.from_year, args.to_year + 1))
    else:
        years = [args.year]

    codes = [c[0] for c in EXTRA_COMMODITIES]

    # Only these reporters historically hit 100K cap — batch only them
    HEAVY_REPORTERS = {"276", "764"}  # Germany, Thailand

    batch1 = codes[:9]   # 84,85,87,71,30,90,29,61,62
    batch2 = codes[9:]   # 03,12,88,28,73,48,40,52
    all_cmd_codes = ",".join(codes)

    print(f"Extra HS2 Data Pull")
    print(f"{'='*60}")
    print(f"Years: {years}")
    print(f"Reporters: {len(TOP_REPORTERS)}")
    print(f"New HS2 codes: {codes}")
    print(f"Strategy: 1 call/reporter, 2 batches only for {list(HEAVY_REPORTERS)}")
    print()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_extra_commodities(db)

    countries = db.query(Country).filter(Country.comtrade_code.isnot(None)).all()
    code_to_iso3 = {c.comtrade_code: c.iso3 for c in countries}
    print(f"[Init] Mapped {len(code_to_iso3)} comtrade codes to ISO3")

    valid_codes = set(codes)
    total_records = 0

    for year in years:
        print(f"\n{'='*60}")
        print(f"YEAR {year}")
        print(f"{'='*60}")

        year_added = 0
        for i, reporter_code in enumerate(TOP_REPORTERS):
            if i < args.resume_from:
                continue

            print(f"  [{i+1}/{len(TOP_REPORTERS)}] Reporter {reporter_code}...", end=" ", flush=True)

            if reporter_code in HEAVY_REPORTERS:
                # Batch fetch for heavy reporters to avoid 100K cap
                frames = []
                print("(batched)", end=" ", flush=True)
                for batch_idx, batch in enumerate([batch1, batch2], 1):
                    batch_codes = ",".join(batch)
                    batch_df = fetch_comtrade(API_KEY, reporter_code, batch_codes, year)
                    if batch_df is not None and not batch_df.empty:
                        frames.append(batch_df)
                    time.sleep(1.5)
                if not frames:
                    print("no data")
                    continue
                df = pd.concat(frames, ignore_index=True)
            else:
                # Single call for normal reporters
                df = fetch_comtrade(API_KEY, reporter_code, all_cmd_codes, year)
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

                cmd_str = str(row.get("cmdCode", "")).zfill(2)
                if cmd_str not in valid_codes:
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
            for (rep, par, cmd), vals in records.items():
                existing = (
                    db.query(BilateralTrade)
                    .filter_by(
                        reporter_iso3=rep, partner_iso3=par,
                        commodity_code=cmd, year=year,
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
                    db.add(BilateralTrade(
                        reporter_iso3=rep, partner_iso3=par,
                        commodity_code=cmd, year=year,
                        export_value_usd=vals["export"],
                        import_value_usd=vals["import"],
                        weight_kg=vals["weight"],
                    ))
                    added += 1

            db.commit()
            year_added += added
            total_records += added
            print(f" +{added}")

        print(f"\n  Year {year} total: {year_added} records")

    db.close()
    print(f"\n{'='*60}")
    print(f"Done! Total new records: {total_records}")


if __name__ == "__main__":
    main()
