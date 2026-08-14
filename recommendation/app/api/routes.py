from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    HealthResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendedItem,
    VariantAssignmentResponse,
)
from app.core.config import get_settings
from app.core.experiment import assign_variant, bucket_value
from app.services.model_registry import registry
from app.services.recommender import get_recommendations

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    expected = {v.name for v in settings.variants}
    loaded = set(registry.variants.keys())
    return HealthResponse(
        status="ok" if registry.is_loaded else "loading",
        loaded_variants=sorted(loaded),
        expected_variants=sorted(expected),
    )


@router.post("/v1/recommendations", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest) -> RecommendationResponse:
    settings = get_settings()
    if not registry.is_loaded:
        raise HTTPException(status_code=503, detail="Models still loading")
    if request.variant is not None and request.variant not in {v.name for v in settings.variants}:
        raise HTTPException(status_code=400, detail=f"Unknown variant override '{request.variant}'")

    history = [(h.item_id, h.rating) for h in request.history]
    variant_name, items = await get_recommendations(
        request.user_id, history, request.k, forced_variant=request.variant
    )
    return RecommendationResponse(
        user_id=request.user_id,
        variant=variant_name,
        items=[RecommendedItem(**item) for item in items],
    )


@router.get("/v1/experiment/assignment/{user_id}", response_model=VariantAssignmentResponse)
async def experiment_assignment(user_id: str) -> VariantAssignmentResponse:
    settings = get_settings()
    variant_name = assign_variant(user_id, settings.variants, settings.experiment_salt)
    bucket = bucket_value(user_id, settings.experiment_salt)
    return VariantAssignmentResponse(user_id=user_id, variant=variant_name, bucket=bucket)
