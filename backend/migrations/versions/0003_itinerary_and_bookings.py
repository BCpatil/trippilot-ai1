"""Create itinerary and booking tables.

Revision ID: 0003_itinerary_and_bookings
Revises: 0002_customers_and_trips
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_itinerary_and_bookings"
down_revision = "0002_customers_and_trips"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itinerary_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itinerary_days_organization_id", "itinerary_days", ["organization_id"])
    op.create_index("ix_itinerary_days_trip_id", "itinerary_days", ["trip_id"])

    op.create_table(
        "itinerary_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_day_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("start_time", sa.String(length=10), nullable=True),
        sa.Column("end_time", sa.String(length=10), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("source_label", sa.String(length=60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_day_id"], ["itinerary_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itinerary_items_organization_id", "itinerary_items", ["organization_id"])
    op.create_index("ix_itinerary_items_itinerary_day_id", "itinerary_items", ["itinerary_day_id"])

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_type", sa.String(length=60), nullable=False),
        sa.Column("supplier", sa.String(length=160), nullable=False),
        sa.Column("external_reference", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("booked_date", sa.Date(), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'tentative', 'cancelled')",
            name="ck_booking_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_organization_id", "bookings", ["organization_id"])
    op.create_index("ix_bookings_trip_id", "bookings", ["trip_id"])
    op.create_index("ix_bookings_customer_id", "bookings", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_bookings_customer_id", table_name="bookings")
    op.drop_index("ix_bookings_trip_id", table_name="bookings")
    op.drop_index("ix_bookings_organization_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_itinerary_items_itinerary_day_id", table_name="itinerary_items")
    op.drop_index("ix_itinerary_items_organization_id", table_name="itinerary_items")
    op.drop_table("itinerary_items")
    op.drop_index("ix_itinerary_days_trip_id", table_name="itinerary_days")
    op.drop_index("ix_itinerary_days_organization_id", table_name="itinerary_days")
    op.drop_table("itinerary_days")
