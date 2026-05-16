"""Profile epic: add follows + posts (minimal, status enum only).

Revision ID: a7c9e2f10001
Revises: f1a2b3c4d5e6
Create Date: 2026-05-14 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a7c9e2f10001"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create `follows` and `posts` tables."""
    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followee_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["follower_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["followee_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("follower_id", "followee_id"),
    )
    op.create_index(
        "idx_follows_followee", "follows", ["followee_id"], unique=False
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.String(length=280), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("on_moderation", "published", name="post_status"),
            server_default="on_moderation",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_posts_user_created",
        "posts",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop `posts` and `follows` (drop indexes BEFORE the tables)."""
    op.drop_index("idx_posts_user_created", table_name="posts")
    op.drop_table("posts")
    sa.Enum(name="post_status").drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_follows_followee", table_name="follows")
    op.drop_table("follows")
