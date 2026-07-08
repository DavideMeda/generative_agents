"""Initial schema — memories table.

Revision ID: 001
Revises: None
Create Date: 2026-07-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column("memory_id", sa.String, primary_key=True),
        sa.Column("agent_id", sa.String, nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("importance", sa.Float, nullable=False),
        sa.Column("created_at", sa.Float, nullable=False),
        sa.Column("last_accessed", sa.Float, nullable=False),
        sa.Column("extra", sa.Text, nullable=False, server_default="{}"),
    )
    op.create_index("idx_memories_agent", "memories", ["agent_id"])
    op.create_index("idx_memories_type", "memories", ["agent_id", "memory_type"])


def downgrade() -> None:
    op.drop_index("idx_memories_type", "memories")
    op.drop_index("idx_memories_agent", "memories")
    op.drop_table("memories")
