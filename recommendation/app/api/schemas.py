from pydantic import BaseModel, Field, conlist


class HistoryItem(BaseModel):
    item_id: str
    # Only used by the collaborative variant; harmless to include even if the
    # request ends up routed to a content variant, which ignores it.
    rating: float | None = None


class RecommendationRequest(BaseModel):
    user_id: str
    history: conlist(HistoryItem, min_length=1, max_length=200)
    k: int | None = Field(default=None, ge=1, le=500)
    # Debug/QA only: bypass the A/B split and force a specific variant. Gate
    # behind internal auth before exposing beyond localhost.
    variant: str | None = None


class RecommendedItem(BaseModel):
    item_id: str
    score: float
    explanation: str | None = None  # None when history was too short/unknown to explain against


class RecommendationResponse(BaseModel):
    user_id: str
    variant: str
    items: list[RecommendedItem]


class VariantAssignmentResponse(BaseModel):
    user_id: str
    variant: str
    bucket: float


class HealthResponse(BaseModel):
    status: str
    loaded_variants: list[str]
    expected_variants: list[str]