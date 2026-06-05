from sqlalchemy import Column, String, Integer, Float, ForeignKey, UniqueConstraint, Text
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


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ocean, sea, strait, canal, land_corridor
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)


class TradeRoute(Base):
    __tablename__ = "trade_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    destination_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    total_cost = Column(Float, nullable=False)
    transport_mode = Column(String, nullable=False, default="sea")
    path_coords_json = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("origin_iso3", "destination_iso3", name="uq_trade_route"),
    )


class TradeRouteSegment(Base):
    __tablename__ = "trade_route_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("trade_routes.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    segment_cost = Column(Float, default=0.0)
