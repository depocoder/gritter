"""Moderation worker.

Consumes `post.*` events from the `posts` topic exchange, classifies posts
with GigaChat, and updates the `posts` row with sentiment + age_rating.

Run with:

    uv run python -m gritter.services.worker
"""
