from app.core.config import get_settings
from app.core.experiment import assign_variant
from app.services import micro_batcher


async def get_recommendations(
    user_id: str,
    history: list,  # list[tuple[str, float | None]]
    k: int | None,
    forced_variant: str | None = None,
) -> tuple[str, list]:
    settings = get_settings()
    k = min(k or settings.default_k, settings.max_k)
    variant_name = forced_variant or assign_variant(user_id, settings.variants, settings.experiment_salt)

    if micro_batcher.pool is None:
        raise RuntimeError("Micro-batcher pool not started")

    items = await micro_batcher.pool.submit(variant_name, user_id, history, k)
    return variant_name, items
