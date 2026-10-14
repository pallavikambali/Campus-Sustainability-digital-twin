"""Add persistent incident notification delivery history.

Revision ID: 6dd17f25a8c1
Revises: 3cb12a83f43f
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "6dd17f25a8c1"
down_revision = "3cb12a83f43f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "channel IN ('EMAIL')",
            name="ck_notification_deliveries_channel",
        ),
        sa.CheckConstraint(
            "status IN ('ACCEPTED', 'FAILED')",
            name="ck_notification_deliveries_status",
        ),
        sa.UniqueConstraint(
            "incident_id",
            "channel",
            name="uq_notification_deliveries_incident_channel",
        ),
    )
    op.create_index(
        "ix_notification_deliveries_attempted_at",
        "notification_deliveries",
        ["attempted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_attempted_at",
        table_name="notification_deliveries",
    )
    op.drop_table("notification_deliveries")
