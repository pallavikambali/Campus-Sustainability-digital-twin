"""Create the Phase 1 schema and seed campus zones.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ACADEMIC_BLOCK_ID = "00000000-0000-4000-8000-000000000001"
LIBRARY_ID = "00000000-0000-4000-8000-000000000002"
HOSTEL_BLOCK_ID = "00000000-0000-4000-8000-000000000003"


def upgrade() -> None:
    op.create_table(
        "zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'NORMAL'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("type IN ('ACADEMIC', 'LIBRARY', 'HOSTEL')", name="ck_zones_type"),
        sa.CheckConstraint("status IN ('NORMAL', 'WARNING', 'CRITICAL')", name="ck_zones_status"),
        sa.CheckConstraint("capacity > 0", name="ck_zones_capacity_positive"),
        sa.PrimaryKeyConstraint("id", name="pk_zones"),
        sa.UniqueConstraint("name", name="uq_zones_name"),
    )
    op.create_table(
        "sensor_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("energy_kwh", sa.Numeric(10, 2), nullable=False),
        sa.Column("water_liters", sa.Numeric(10, 2), nullable=False),
        sa.Column("occupancy", sa.Integer(), nullable=False),
        sa.CheckConstraint("energy_kwh >= 0", name="ck_sensor_readings_energy_nonnegative"),
        sa.CheckConstraint("water_liters >= 0", name="ck_sensor_readings_water_nonnegative"),
        sa.CheckConstraint("occupancy >= 0", name="ck_sensor_readings_occupancy_nonnegative"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_sensor_readings_zone_id_zones", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_sensor_readings"),
    )
    op.create_index("ix_sensor_readings_zone_timestamp", "sensor_readings", ["zone_id", "timestamp"])

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("current_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("expected_range", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type IN ('HIGH_ENERGY_CONSUMPTION', 'POSSIBLE_WATER_LEAKAGE', 'ABNORMAL_OCCUPANCY', 'WASTE_ACCUMULATION')", name="ck_incidents_type"),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_incidents_severity"),
        sa.CheckConstraint("status IN ('ACTIVE', 'RESOLVED')", name="ck_incidents_status"),
        sa.CheckConstraint("source IN ('RULE', 'CV')", name="ck_incidents_source"),
        sa.CheckConstraint("(status = 'ACTIVE' AND resolved_at IS NULL) OR (status = 'RESOLVED' AND resolved_at IS NOT NULL)", name="ck_incidents_resolution_timestamp"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_incidents_zone_id_zones", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
    )
    op.create_index("ix_incidents_zone_status", "incidents", ["zone_id", "status"])

    op.create_table(
        "waste_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_path", sa.Text(), nullable=True),
        sa.Column("detected_objects", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("waste_level", sa.String(length=20), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("waste_level IN ('NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_waste_detections_level"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name="fk_waste_detections_zone_id_zones", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_waste_detections"),
    )
    op.create_index("ix_waste_detections_zone_created", "waste_detections", ["zone_id", "created_at"])

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name="fk_recommendations_incident_id_incidents", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_recommendations"),
    )
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("report_type", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("statistics", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("report_type IN ('DAILY', 'WEEKLY')", name="ck_reports_type"),
        sa.CheckConstraint("period_end >= period_start", name="ck_reports_period_order"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
    )

    op.execute(
        sa.text(
            "INSERT INTO zones (id, name, type, capacity) VALUES "
            "(CAST(:academic_id AS UUID), 'Academic Block', 'ACADEMIC', 300), "
            "(CAST(:library_id AS UUID), 'Library', 'LIBRARY', 150), "
            "(CAST(:hostel_id AS UUID), 'Hostel Block', 'HOSTEL', 250)"
        ).bindparams(
            academic_id=ACADEMIC_BLOCK_ID,
            library_id=LIBRARY_ID,
            hostel_id=HOSTEL_BLOCK_ID,
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM zones WHERE id IN ("
            "CAST(:academic_id AS UUID), CAST(:library_id AS UUID), CAST(:hostel_id AS UUID))"
        ).bindparams(
            academic_id=ACADEMIC_BLOCK_ID,
            library_id=LIBRARY_ID,
            hostel_id=HOSTEL_BLOCK_ID,
        )
    )
    op.drop_table("reports")
    op.drop_table("recommendations")
    op.drop_index("ix_waste_detections_zone_created", table_name="waste_detections")
    op.drop_table("waste_detections")
    op.drop_index("ix_incidents_zone_status", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_sensor_readings_zone_timestamp", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_table("zones")
