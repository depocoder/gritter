"""FastAPI dependency providing the shared MinIO client from app state."""

from minio import Minio
from starlette.requests import Request


def get_minio_client(request: Request) -> Minio:
    """Return the MinIO client stored in `app.state` by `init_minio`."""
    client: Minio = request.app.state.minio_client
    return client
