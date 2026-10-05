from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("name", name="uq_zones_name"),
        CheckConstraint(
            "type IN ('ACADEMIC', 'LIBRARY', 'HOSTEL')", name="ck_zones_type"
        ),
        CheckConstraint(
            "status IN ('NORMAL', 'WARNING', 'CRITICAL')", name="ck_zones_status"
        ),
        CheckConstraint("capacity > 0", name="ck_zones_capacity_positive"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'NORMAL'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        CheckConstraint("energy_kwh >= 0", name="ck_sensor_readings_energy_nonnegative"),
        CheckConstraint("water_liters >= 0", name="ck_sensor_readings_water_nonnegative"),
        CheckConstraint("occupancy >= 0", name="ck_sensor_readings_occupancy_nonnegative"),
        Index("ix_sensor_readings_zone_timestamp", "zone_id", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    zone_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    water_liters: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    occupancy: Mapped[int] = mapped_column(Integer, nullable=False)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('HIGH_ENERGY_CONSUMPTION', 'POSSIBLE_WATER_LEAKAGE', "
            "'ABNORMAL_OCCUPANCY', 'WASTE_ACCUMULATION')",
            name="ck_incidents_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_incidents_severity"
        ),
        CheckConstraint("status IN ('ACTIVE', 'RESOLVED')", name="ck_incidents_status"),
        CheckConstraint("source IN ('RULE', 'CV')", name="ck_incidents_source"),
        CheckConstraint(
            "(status = 'ACTIVE' AND resolved_at IS NULL) OR "
            "(status = 'RESOLVED' AND resolved_at IS NOT NULL)",
            name="ck_incidents_resolution_timestamp",
        ),
        Index("ix_incidents_zone_status", "zone_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    zone_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_range: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'ACTIVE'")
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WasteDetection(Base):
    __tablename__ = "waste_detections"
    __table_args__ = (
        CheckConstraint(
            "waste_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_waste_detections_level",
        ),
        Index("ix_waste_detections_zone_created", "zone_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    zone_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False
    )
    image_path: Mapped[str | None] = mapped_column(Text)
    detected_objects: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    waste_level: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    incident_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL")
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("report_type IN ('DAILY', 'WEEKLY')", name="ck_reports_type"),
        CheckConstraint("period_end >= period_start", name="ck_reports_period_order"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
