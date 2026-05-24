"""create sessions table

Revision ID: 20260524_0003
Revises: 20260524_0002
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260524_0003"
down_revision: str | None = "20260524_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

session_status_enum = postgresql.ENUM(
    "scheduled",
    "in_progress",
    "finished",
    "cancelled",
    name="session_status",
    create_type=False,
)


def upgrade() -> None:
    session_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("speaker_name", sa.String(length=255), nullable=False),
        sa.Column("room", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("available_slots", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            session_status_enum,
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint("end_time >= start_time", name="ck_sessions_end_after_start"),
        sa.CheckConstraint("capacity > 0", name="ck_sessions_capacity_positive"),
        sa.CheckConstraint(
            "available_slots >= 0 AND available_slots <= capacity",
            name="ck_sessions_available_slots_bounds",
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_event_id", "sessions", ["event_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)
    op.create_index("ix_sessions_start_time", "sessions", ["start_time"], unique=False)
    op.create_index(
        "ix_sessions_event_speaker",
        "sessions",
        ["event_id", "speaker_name"],
        unique=False,
    )
    op.create_index("ix_sessions_event_room", "sessions", ["event_id", "room"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessions_event_room", table_name="sessions")
    op.drop_index("ix_sessions_event_speaker", table_name="sessions")
    op.drop_index("ix_sessions_start_time", table_name="sessions")
    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_event_id", table_name="sessions")
    op.drop_table("sessions")
    session_status_enum.drop(op.get_bind(), checkfirst=True)
