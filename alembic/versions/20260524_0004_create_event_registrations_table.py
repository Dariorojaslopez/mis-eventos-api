"""create event_registrations table

Revision ID: 20260524_0004
Revises: 20260524_0003
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260524_0004"
down_revision: str | None = "20260524_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

registration_status_enum = postgresql.ENUM(
    "registered",
    "cancelled",
    "waitlist",
    name="registration_status",
    create_type=False,
)


def upgrade() -> None:
    registration_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "event_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            registration_status_enum,
            nullable=False,
            server_default="registered",
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_registrations_user_id",
        "event_registrations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_registrations_event_id",
        "event_registrations",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_registrations_status",
        "event_registrations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_event_registrations_user_event_active",
        "event_registrations",
        ["user_id", "event_id"],
        unique=True,
        postgresql_where=sa.text("status = 'registered'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_event_registrations_user_event_active",
        table_name="event_registrations",
    )
    op.drop_index("ix_event_registrations_status", table_name="event_registrations")
    op.drop_index("ix_event_registrations_event_id", table_name="event_registrations")
    op.drop_index("ix_event_registrations_user_id", table_name="event_registrations")
    op.drop_table("event_registrations")
    registration_status_enum.drop(op.get_bind(), checkfirst=True)
