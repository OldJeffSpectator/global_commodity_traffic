"""Standalone script to pull trade data from UN Comtrade API.
Run from the backend/ directory with venv activated.

Usage:
    python pull_data.py
    python pull_data.py --year 2022
"""
import os
import sys
import time
import argparse

# Clear proxy settings
for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.db.models import Country, BilateralTrade
from app.db.seed import init_db

API_KEY = os.environ.get("COMTRADE_API_KEY", "3bf9dc83d1834c5f9f262476104a238e")
COMMODITY_CODES = ["27", "10", "72", "26", "31", "44", "17", "76", "74", "39"]

TOP_REPORTERS = [
    "842", "156", "276", "392", "826", "250", "380", "124", "410", "528",
    "356", "036", "076", "643", "682", "784", "360", "764", "484", "710",
]


def main():
    parser = argparse.ArgumentParser(description="Pull trade data from UN Comtrade")
    parser.add_argument("--year", type=int, default=None, help="Single year to fetch")
    parser.add_argument("--from-year", type=int, default=2000, help="Start year (default: 2000)")
    parser.add_argument("--to-year", type=int, default=2023, help="End year (default: 2023)")
    args = parser.parse_args()

    if args.year:
        years = [args.year]
    else:
        years = list(range(args.from_year, args.to_year + 1))

    print(f"Will fetch years: {years[0]}-{years[-1]} ({len(years)} years)")
    print(f"Reporters: {len(TOP_REPORTERS)}, Commodities: {len(COMMODITY_CODES)}")
    print(f"Estimated API calls: {len(years) * len(TOP_REPORTERS)}")
    print()

    print(f"Initializing database...")
    init_db()

    import comtradeapicall

    db = SessionLocal()
    countries = db.query(Country).filter(Country.comtrade_code.isnot(None)).all()
    code_to_iso3 = {c.comtrade_code: c.iso3 for c in countries}
    print(f"Mapped {len(code_to_iso3)} comtrade codes to ISO3")

    total_records = 0
    cmd_codes = ",".join(COMMODITY_CODES)

    for year_idx, year in enumerate(years):
        print(f"\n{'='*50}")
        print(f"YEAR {year} ({year_idx+1}/{len(years)})")
        print(f"{'='*50}")

        year_added = 0
        for i, reporter_code in enumerate(TOP_REPORTERS):
            print(f"  [{i+1}/{len(TOP_REPORTERS)}] Reporter {reporter_code}...", end=" ", flush=True)

            try:
                df = comtradeapicall.getFinalData(
                    API_KEY,
                    typeCode="C",
                    freqCode="A",
                    clCode="HS",
                    period=str(year),
                    reporterCode=reporter_code,
                    cmdCode=cmd_codes,
                    flowCode="X,M",
                    partnerCode=None,
                    partner2Code=None,
                    customsCode=None,
                    motCode=None,
                    maxRecords=50000,
                    includeDesc=True,
                )
            except Exception as e:
                print(f"ERROR: {e}")
                continue

            if df is None or df.empty:
                print("no data")
                continue

            print(f"{len(df)} rows")
            # Show first 3 rows as sample
            sample = df.head(3)
            for _, s in sample.iterrows():
                rep = code_to_iso3.get(int(s["reporterCode"]), str(s["reporterCode"]))
                par = code_to_iso3.get(int(s["partnerCode"]), str(s["partnerCode"]))
                flow = s.get("flowCode", "?")
                val = s.get("primaryValue", 0) or 0
                cmd = str(s.get("cmdCode", "")).zfill(2)
                print(f"    {rep}->{par} HS{cmd} [{flow}] ${val:,.0f}")

            # Aggregate rows by (reporter, partner, commodity) before inserting
            records = {}
            for _, row in df.iterrows():
                reporter_iso = code_to_iso3.get(int(row["reporterCode"]))
                partner_iso = code_to_iso3.get(int(row["partnerCode"]))
                if not reporter_iso or not partner_iso:
                    continue

                cmd_str = str(row["cmdCode"]).zfill(2)
                if cmd_str not in COMMODITY_CODES:
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
            print(f"+{added}")

            time.sleep(1)

        print(f"  Year {year} total: {year_added} records")

    db.close()
    print(f"\n{'='*50}")
    print(f"Done! Total new records: {total_records}")
    print(f"Database: {os.path.abspath('data/trade.db')}")


if __name__ == "__main__":
    main()
