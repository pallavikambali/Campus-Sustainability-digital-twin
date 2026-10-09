"""Replace Hostel Block with Canteen.

Revision ID: 3cb12a83f43f
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "3cb12a83f43f"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Verify the existing zone before changing the schema.
    connection = op.get_bind()

    hostel_exists = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM zones
                WHERE name = 'Hostel Block'
                  AND type = 'HOSTEL'
            )
            """
        )
    ).scalar()

    if not hostel_exists:
        raise RuntimeError(
            "Expected Hostel Block zone was not found; "
            "Canteen migration was not applied."
        )

    # Allow CANTEEN as a valid zone type.
    op.drop_constraint("ck_zones_type", "zones", type_="check")
    op.create_check_constraint(
        "ck_zones_type",
        "zones",
        "type IN ('ACADEMIC', 'LIBRARY', 'HOSTEL', 'CANTEEN')",
    )

    # Rename the existing zone without changing its UUID.
    connection.execute(
        sa.text(
            """
            UPDATE zones
            SET name = 'Canteen',
                type = 'CANTEEN',
                capacity = 120
            WHERE name = 'Hostel Block'
              AND type = 'HOSTEL'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            UPDATE zones
            SET name = 'Hostel Block',
                type = 'HOSTEL',
                capacity = 250
            WHERE name = 'Canteen'
              AND type = 'CANTEEN'
            """
        )
    )

    op.drop_constraint("ck_zones_type", "zones", type_="check")
    op.create_check_constraint(
        "ck_zones_type",
        "zones",
        "type IN ('ACADEMIC', 'LIBRARY', 'HOSTEL')",
    )