"""Fetch bilateral trade data from UN Comtrade API."""
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import BilateralTrade, Country, SyncStatus

COMTRADE_API_KEY = os.environ.get("COMTRADE_API_KEY", "")

# Rate limit: free tier allows limited calls per minute
API_DELAY_SECONDS = 2
API_TIMEOUT_SECONDS = 60

COMMODITY_CODES = ["27", "10", "72", "26", "31", "44", "17", "76", "74", "39"]

# Top trading nations by comtrade reporter code (covers ~80% of world trade)
TOP_REPORTERS = [
    "842",  # USA
    "156",  # China
    "276",  # Germany
    "392",  # Japan
    "826",  # UK
    "250",  # France
    "380",  # Italy
    "124",  # Canada
    "410",  # South Korea
    "528",  # Netherlands
    "356",  # India
    "036",  # Australia
    "076",  # Brazil
    "643",  # Russia
    "682",  # Saudi Arabia
    "784",  # UAE
    "360",  # Indonesia
    "764",  # Thailand
    "484",  # Mexico
    "710",  # South Africa
]

_sync_lock = threading.Lock()
_current_sync_id: int | None = None


def get_current_sync_id() -> int | None:
    return _current_sync_id


def start_sync_background(year: int | None = None):
    """Launch a background thread to sync trade data."""
    global _current_sync_id

    if not _sync_lock.acquire(blocking=False):
        return None

    db = SessionLocal()
    try:
        sync = SyncStatus(
            started_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            records_fetched=0,
        )
        db.add(sync)
        db.commit()
        db.refresh(sync)
        _current_sync_id = sync.id
    finally:
        db.close()

    target_year = year or datetime.now().year - 2
    thread = threading.Thread(
        target=_run_sync, args=(sync.id, target_year), daemon=True
    )
    thread.start()
    return sync.id


def _build_code_to_iso3_map(db: Session) -> dict[int, str]:
    """Build a mapping from comtrade numeric codes to ISO3."""
    countries = db.query(Country).filter(Country.comtrade_code.isnot(None)).all()
    return {c.comtrade_code: c.iso3 for c in countries}


def _run_sync(sync_id: int, year: int):
    """Execute the sync in a background thread."""
    global _current_sync_id

    # Force-clear proxy settings so requests don't route through a dead VPN proxy
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ.pop(var, None)
    os.environ["NO_PROXY"] = "*"

    db = SessionLocal()
    total_records = 0

    try:
        import comtradeapicall

        code_to_iso3 = _build_code_to_iso3_map(db)
        print(f"[Sync] Mapped {len(code_to_iso3)} comtrade codes to ISO3")

        for i, reporter_code in enumerate(TOP_REPORTERS):
            cmd_codes = ",".join(COMMODITY_CODES)
            print(f"[Sync] Fetching reporter {reporter_code} ({i+1}/{len(TOP_REPORTERS)})...")

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        comtradeapicall.getFinalData,
                        COMTRADE_API_KEY,
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
                    df = future.result(timeout=API_TIMEOUT_SECONDS)
            except FuturesTimeout:
                print(f"[Sync] TIMEOUT for reporter {reporter_code} (>{API_TIMEOUT_SECONDS}s)")
                continue
            except Exception as e:
                print(f"[Sync] Error fetching for reporter {reporter_code}: {e}")
                continue

            if df is None or df.empty:
                print(f"[Sync] No data for reporter {reporter_code}")
                continue

            records = _process_dataframe(df, year, code_to_iso3)
            if records:
                _upsert_records(db, records)
                total_records += len(records)
                print(f"[Sync] +{len(records)} records (total: {total_records})")

            sync_record = db.query(SyncStatus).filter_by(id=sync_id).first()
            if sync_record:
                sync_record.records_fetched = total_records
                db.commit()

            time.sleep(API_DELAY_SECONDS)

        sync_record = db.query(SyncStatus).filter_by(id=sync_id).first()
        if sync_record:
            sync_record.status = "completed"
            sync_record.completed_at = datetime.now(timezone.utc).isoformat()
            db.commit()
        print(f"[Sync] Completed. Total records: {total_records}")

    except Exception as e:
        print(f"[Sync] FAILED: {e}")
        sync_record = db.query(SyncStatus).filter_by(id=sync_id).first()
        if sync_record:
            sync_record.status = "failed"
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.now(timezone.utc).isoformat()
            db.commit()
    finally:
        _current_sync_id = None
        _sync_lock.release()
        db.close()


def _process_dataframe(df, year: int, code_to_iso3: dict[int, str]) -> list[dict]:
    """Convert comtrade dataframe rows into trade records."""
    records = []

    # The free API may not populate reporterISO/partnerISO, so use numeric codes
    use_iso = "reporterISO" in df.columns and df["reporterISO"].notna().any()

    if use_iso:
        grouped = df.groupby(["reporterISO", "partnerISO", "cmdCode", "flowCode"])
        for (reporter_iso, partner_iso, cmd_code, flow_code), group in grouped:
            if not reporter_iso or not partner_iso:
                continue
            if partner_iso == "W00":
                continue
            if len(str(reporter_iso)) != 3 or len(str(partner_iso)) != 3:
                continue
            record = _build_record(
                str(reporter_iso), str(partner_iso),
                cmd_code, flow_code, group, year,
            )
            if record:
                records.append(record)
    else:
        grouped = df.groupby(["reporterCode", "partnerCode", "cmdCode", "flowCode"])
        for (reporter_code, partner_code, cmd_code, flow_code), group in grouped:
            reporter_iso = code_to_iso3.get(int(reporter_code))
            partner_iso = code_to_iso3.get(int(partner_code))
            if not reporter_iso or not partner_iso:
                continue
            record = _build_record(
                reporter_iso, partner_iso,
                cmd_code, flow_code, group, year,
            )
            if record:
                records.append(record)

    return records


def _build_record(
    reporter_iso: str, partner_iso: str,
    cmd_code, flow_code, group, year: int,
) -> dict | None:
    """Build a single trade record dict."""
    cmd_str = str(cmd_code).zfill(2)
    if cmd_str not in COMMODITY_CODES:
        return None

    value = group["primaryValue"].sum() if "primaryValue" in group.columns else 0
    weight = group["netWgt"].sum() if "netWgt" in group.columns else 0

    return {
        "reporter_iso3": reporter_iso,
        "partner_iso3": partner_iso,
        "commodity_code": cmd_str,
        "year": year,
        "export_value_usd": float(value) if flow_code == "X" else 0,
        "import_value_usd": float(value) if flow_code == "M" else 0,
        "weight_kg": float(weight) if weight and weight > 0 else 0,
    }


def _upsert_records(db: Session, records: list[dict]):
    """Insert or update trade records."""
    for record in records:
        existing = (
            db.query(BilateralTrade)
            .filter_by(
                reporter_iso3=record["reporter_iso3"],
                partner_iso3=record["partner_iso3"],
                commodity_code=record["commodity_code"],
                year=record["year"],
            )
            .first()
        )
        if existing:
            if record["export_value_usd"] > 0:
                existing.export_value_usd = record["export_value_usd"]
            if record["import_value_usd"] > 0:
                existing.import_value_usd = record["import_value_usd"]
            if record["weight_kg"] > 0:
                existing.weight_kg = record["weight_kg"]
        else:
            db.add(BilateralTrade(**record))

    db.commit()
