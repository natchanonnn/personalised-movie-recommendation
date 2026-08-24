from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.services import micro_batcher
from app.services.micro_batcher import MicroBatcherPool
from app.services.model_registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry.load(settings)

    micro_batcher.pool = MicroBatcherPool(
        registry=registry,
        max_wait_ms=settings.max_wait_ms,
        max_batch_size=settings.max_batch_size,
        scratch_dir=settings.scratch_dir,
    )
    micro_batcher.pool.start()
    try:
        yield
    finally:
        micro_batcher.pool.stop()


app = FastAPI(title="Recommendation Service", lifespan=lifespan)
app.include_router(router)
