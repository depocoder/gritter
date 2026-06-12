"""Outbox publisher (Эпик 6).

Standalone worker that drains rows from `posts_outbox` and publishes them
to RabbitMQ. Run with:

    uv run python -m gritter.services.posts_publisher
"""
