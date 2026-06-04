"""Fetch bilateral trade data from UN Comtrade API."""
import os
import threading
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from app.db.database import SessionLocal
from app.db.models import BilateralTrade, Country, SyncStatus

COMTRADE_API_KEY = os.environ.get("COMTRADE_API_KEY", "")

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


def _run_sync(sync_id: int, year: int):
    """Execute the sync in a background thread."""
    global _current_sync_id
    db = SessionLocal()
    total_records = 0

    try:
        import comtradeapicall

        for reporter_code in TOP_REPORTERS:
            cmd_codes = ",".join(COMMODITY_CODES)
            try:
                df = comtradeapicall.getFinalData(
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
            except Exception as e:
                print(f"Error fetching for reporter {reporter_code}: {e}")
                continue

            if df is None or df.empty:
                continue

            records = _process_dataframe(df, year)
            if records:
                _upsert_records(db, records)
                total_records += len(records)

            sync_record = db.query(SyncStatus).filter_by(id=sync_id).first()
            if sync_record:
                sync_record.records_fetched = total_records
                db.commit()

        sync_record = db.query(SyncStatus).filter_by(id=sync_id).first()
        if sync_record:
            sync_record.status = "completed"
            sync_record.completed_at = datetime.now(timezone.utc).isoformat()
            db.commit()

    except Exception as e:
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


def _process_dataframe(df, year: int) -> list[dict]:
    """Convert comtrade dataframe rows into trade records."""
    records = []
    grouped = df.groupby(["reporterISO", "partnerISO", "cmdCode", "flowCode"])

    for (reporter_iso, partner_iso, cmd_code, flow_code), group in grouped:
        if not reporter_iso or not partner_iso:
            continue
        if partner_iso == "W00":  # "World" aggregate
            continue
        if len(reporter_iso) != 3 or len(partner_iso) != 3:
            continue

        cmd_str = str(cmd_code).zfill(2)
        if cmd_str not in COMMODITY_CODES:
            continue

        value = group["primaryValue"].sum() if "primaryValue" in group.columns else 0
        weight = group["netWgt"].sum() if "netWgt" in group.columns else 0

        record = {
            "reporter_iso3": reporter_iso,
            "partner_iso3": partner_iso,
            "commodity_code": cmd_str,
            "year": year,
            "export_value_usd": value if flow_code == "X" else 0,
            "import_value_usd": value if flow_code == "M" else 0,
            "weight_kg": weight if weight and weight > 0 else 0,
        }
        records.append(record)

    return records


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
