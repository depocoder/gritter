"""Эпик 3: likes and comments tables.

Revision ID: e1a2b3c40003
Revises: c8d1f2030002
Create Date: 2026-05-16 12:00:00.000000

Adds two new tables that drive the user-interaction features:

* ``likes`` — composite PK ``(post_id, user_id)``; ``ON CONFLICT DO NOTHING``
  in the DAO relies on this PK for idempotent toggle semantics.
* ``comments`` — surrogate ``id`` PK plus ``deleted_at`` soft-delete column,
  with an index supporting the ``GET /posts/{id}/comments`` listing.

Counter columns ``posts.likes_count`` and ``posts.comments_count`` were
already created in revision ``c8d1f2030002`` (Эпик 2) together with their
``CHECK >= 0`` constraints, so this migration leaves ``posts`` alone.
"""

import sqlalchemy as sa
from alembic import op

revision = "e1a2b3c40003"
down_revision = "c8d1f2030002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the ``likes`` and ``comments`` tables with their indexes."""
    op.create_table(
        "likes",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            ondelete="CASCADE",
            name="fk_likes_post_id_posts",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_likes_user_id_users",
        ),
        sa.PrimaryKeyConstraint("post_id", "user_id", name="pk_likes"),
    )
    op.create_index("idx_likes_user", "likes", ["user_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
            ondelete="CASCADE",
            name="fk_comments_post_id_posts",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_comments_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
    )
    op.create_index(
        "idx_comments_post_created", "comments", ["post_id", "created_at"]
    )


def downgrade() -> None:
    """Reverse the upgrade in the safe order (indexes first, then tables)."""
    op.drop_index("idx_comments_post_created", table_name="comments")
    op.drop_table("comments")

    op.drop_index("idx_likes_user", table_name="likes")
    op.drop_table("likes")
