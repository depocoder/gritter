from fastapi.routing import APIRouter

from gritter.web.api import (
    auth,
    docs,
    dummy,
    echo,
    monitoring,
    profile,
    rabbit,
    redis,
)

api_router = APIRouter()
api_router.include_router(monitoring.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router, tags=["profile"])
api_router.include_router(docs.router)
api_router.include_router(echo.router, prefix="/echo", tags=["echo"])
api_router.include_router(dummy.router, prefix="/dummy", tags=["dummy"])
api_router.include_router(redis.router, prefix="/redis", tags=["redis"])
api_router.include_router(rabbit.router, prefix="/rabbit", tags=["rabbit"])
