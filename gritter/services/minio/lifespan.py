"""MinIO client lifespan: create client and ensure avatars bucket exists."""

from fastapi import FastAPI
from minio import Minio

from gritter.settings import settings


def init_minio(app: FastAPI) -> None:  # pragma: no cover
    """Create a MinIO client and ensure the avatars bucket exists."""
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    bucket = settings.minio_bucket_avatars
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    app.state.minio_client = client
