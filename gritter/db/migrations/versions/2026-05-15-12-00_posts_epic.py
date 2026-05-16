"""Posts epic: extend `posts`, add `posts_outbox`, sentiment/age_rating enums.

Revision ID: c8d1f2030002
Revises: a7c9e2f10001
Create Date: 2026-05-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "c8d1f2030002"
down_revision = "a7c9e2f10001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Bring the schema up to Эпик 2 spec (raw SQL for partial indexes)."""
    sentiment = sa.Enum("positive", "neutral", "negative", name="sentiment")
    age_rating = sa.Enum("0+", "12+", "16+", "18+", name="age_rating")
    outbox_status = sa.Enum("pending", "sent", name="outbox_status")
    # sentiment/age_rating idут через op.add_column ниже — для них add_column
    # НЕ запускает CREATE TYPE автоматически, поэтому нужен явный create().
    # outbox_status используется в op.create_table("posts_outbox") — CREATE TYPE
    # сгенерируется автоматически вместе с таблицей; явный create не нужен,
    # иначе будет дубль (DuplicateObjectError на чистой БД).
    sentiment.create(op.get_bind(), checkfirst=True)
    age_rating.create(op.get_bind(), checkfirst=True)

    op.add_column("posts", sa.Column("sentiment", sentiment, nullable=True))
    op.add_column("posts", sa.Column("age_rating", age_rating, nullable=True))
    op.add_column(
        "posts",
        sa.Column(
            "moderation_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("posts", sa.Column("moderated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "posts",
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "posts",
        sa.Column(
            "comments_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_check_constraint(
        "chk_likes_count_nonneg", "posts", "likes_count >= 0"
    )
    op.create_check_constraint(
        "chk_comments_count_nonneg", "posts", "comments_count >= 0"
    )
    op.create_index(
        "idx_posts_status_created", "posts", ["status", "created_at"]
    )
    op.create_index(
        "idx_posts_category_created", "posts", ["category", "created_at"]
    )
    op.execute(
        "CREATE INDEX idx_posts_feed ON posts (created_at DESC) "
        "WHERE status = 'published' AND deleted_at IS NULL"
    )

    op.create_table(
        "posts_outbox",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "status",
            outbox_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX idx_outbox_pending ON posts_outbox (created_at) "
        "WHERE status = 'pending'"
    )


def downgrade() -> None:
    """Revert Эпик 2 schema (drop indexes BEFORE tables)."""
    op.execute("DROP INDEX IF EXISTS idx_outbox_pending")
    op.drop_table("posts_outbox")

    op.execute("DROP INDEX IF EXISTS idx_posts_feed")
    op.drop_index("idx_posts_category_created", table_name="posts")
    op.drop_index("idx_posts_status_created", table_name="posts")
    op.drop_constraint("chk_comments_count_nonneg", "posts", type_="check")
    op.drop_constraint("chk_likes_count_nonneg", "posts", type_="check")
    op.drop_column("posts", "comments_count")
    op.drop_column("posts", "likes_count")
    op.drop_column("posts", "moderated_at")
    op.drop_column("posts", "moderation_attempts")
    op.drop_column("posts", "age_rating")
    op.drop_column("posts", "sentiment")

    sa.Enum(name="outbox_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="age_rating").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sentiment").drop(op.get_bind(), checkfirst=True)
