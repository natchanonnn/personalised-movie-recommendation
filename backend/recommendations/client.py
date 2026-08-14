"""HTTP client for the recommendation service (see /recommendation).

Talks to the live FastAPI service over plain HTTP -- see recommendation/README.md
for the request/response contract. The service is stateless per-request: it
has no stored interaction history, so callers must supply it directly.
"""

import requests
from django.conf import settings


class RecommendationServiceError(Exception):
    """Raised when the recommendation service can't be reached or errors out."""


def get_recommendations(
    user_id: str,
    history: list[dict],
    k: int | None = None,
    variant: str | None = None,
) -> dict:
    """POST /v1/recommendations.

    `history` items are {"item_id": <Movie.tmdb_id as str>, "rating": <float|None>}.
    Returns the parsed JSON response: {"user_id", "variant", "items": [...]}.
    """
    payload = {"user_id": user_id, "history": history}
    if k is not None:
        payload["k"] = k
    if variant is not None:
        payload["variant"] = variant

    try:
        response = requests.post(
            f"{settings.RECOMMENDATION_SERVICE_URL}/v1/recommendations",
            json=payload,
            timeout=settings.RECOMMENDATION_SERVICE_TIMEOUT,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400 and variant is not None:
            # Most likely cause: RECOMMENDATION_SERVICE_VARIANT is misconfigured
            # (doesn't match one of the service's currently loaded variants).
            raise RecommendationServiceError(
                f"Recommendation service rejected variant override {variant!r}: {exc.response.text}"
            ) from exc
        raise RecommendationServiceError(str(exc)) from exc
    except requests.RequestException as exc:
        raise RecommendationServiceError(str(exc)) from exc

    return response.json()
