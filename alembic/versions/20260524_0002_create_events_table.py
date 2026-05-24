"""create events table

Revision ID: 20260524_0002
Revises: 20260523_0001
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260524_0002"
down_revision: str | None = "20260523_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

event_status_enum = postgresql.ENUM(
    "draft",
    "published",
    "cancelled",
    "finished",
    name="event_status",
    create_type=False,
)


def upgrade() -> None:
    event_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.Column("available_slots", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            event_status_enum,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_events_end_after_start"),
        sa.CheckConstraint("max_capacity > 0", name="ck_events_max_capacity_positive"),
        sa.CheckConstraint(
            "available_slots >= 0 AND available_slots <= max_capacity",
            name="ck_events_available_slots_bounds",
        ),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_organizer_id", "events", ["organizer_id"], unique=False)
    op.create_index("ix_events_status", "events", ["status"], unique=False)
    op.create_index("ix_events_start_date", "events", ["start_date"], unique=False)
    op.create_index("ix_events_title_lower", "events", [sa.text("lower(title)")], unique=False)


def downgrade() -> None:
    op.drop_index("ix_events_title_lower", table_name="events")
    op.drop_index("ix_events_start_date", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_index("ix_events_organizer_id", table_name="events")
    op.drop_table("events")
    event_status_enum.drop(op.get_bind(), checkfirst=True)
