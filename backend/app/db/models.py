from sqlalchemy import Column, String, Integer, Float, ForeignKey, UniqueConstraint
from app.db.database import Base


class Country(Base):
    __tablename__ = "countries"

    iso3 = Column(String(3), primary_key=True)
    name = Column(String, nullable=False)
    comtrade_code = Column(Integer, nullable=True)
    centroid_lat = Column(Float, nullable=False)
    centroid_lng = Column(Float, nullable=False)


class Commodity(Base):
    __tablename__ = "commodities"

    hs2_code = Column(String(4), primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)


class BilateralTrade(Base):
    __tablename__ = "bilateral_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    partner_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    commodity_code = Column(String(4), ForeignKey("commodities.hs2_code"), nullable=False)
    year = Column(Integer, nullable=False)
    export_value_usd = Column(Float, default=0.0)
    import_value_usd = Column(Float, default=0.0)
    weight_kg = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint(
            "reporter_iso3", "partner_iso3", "commodity_code", "year",
            name="uq_trade_record"
        ),
    )


class SyncStatus(Base):
    __tablename__ = "sync_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)
    status = Column(String, nullable=False, default="running")
    records_fetched = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
