import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from interactions.models import Rating
from movies.models import Movie
from movies.serializers import MovieSearchResultSerializer
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .client import RecommendationServiceError, get_recommendations


def _cache_key(user_id: int, history: list[dict], k: int, variant: str | None) -> str:
    # history/k/variant fully determine the output (the service is stateless
    # and deterministic given the same inputs), so hashing them together is
    # a correct cache key -- a new rating changes `history`, which changes
    # this key, so there's no separate invalidation to manage.
    payload = json.dumps({"history": history, "k": k, "variant": variant}, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"recommendations:{user_id}:{digest}"


class RecommendationsView(APIView):
    """GET /v1/recommendations/?k=<n>

    Recommends movies for the current user: sends their rating history to
    the recommendation service (see /recommendation) and enriches the
    returned item_ids (== Movie.tmdb_id) with local movie data, in the
    service's ranked order. Cached per (user, rating history, k, variant)
    for RECOMMENDATION_CACHE_TTL_SECONDS so repeated calls -- e.g. revisiting
    the recommendations page -- don't re-hit the model on every request.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        try:
            k = int(request.query_params.get("k", settings.RECOMMENDATION_DEFAULT_K))
        except ValueError:
            return Response({"detail": "k must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
        k = max(1, min(k, settings.RECOMMENDATION_MAX_K))

        ratings = Rating.objects.filter(user=request.user).select_related("movie")
        history = [{"item_id": str(r.movie.tmdb_id), "rating": r.score} for r in ratings]

        if not history:
            return Response(
                {
                    "detail": "Rate a few movies first so recommendations have something to work from.",
                    "variant": None,
                    "results": [],
                }
            )

        cache_key = _cache_key(request.user.id, history, k, settings.RECOMMENDATION_SERVICE_VARIANT)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            result = get_recommendations(
                user_id=str(request.user.id),
                history=history,
                k=k,
                variant=settings.RECOMMENDATION_SERVICE_VARIANT,
            )
        except RecommendationServiceError as exc:
            # Not cached -- a transient outage shouldn't lock the user out
            # of recommendations for the full TTL once the service recovers.
            return Response(
                {"detail": "Recommendation service is unavailable.", "error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        items = result.get("items", [])
        rec_by_tmdb_id = {item["item_id"]: item for item in items}

        movies = Movie.objects.filter(tmdb_id__in=rec_by_tmdb_id.keys()).prefetch_related("genres")
        movies_by_tmdb_id = {str(movie.tmdb_id): movie for movie in movies}

        # Preserve the recommendation service's ranking, not the DB's.
        ordered_movies = [
            movies_by_tmdb_id[item["item_id"]] for item in items if item["item_id"] in movies_by_tmdb_id
        ]
        serialized = MovieSearchResultSerializer(ordered_movies, many=True).data

        for movie_data in serialized:
            rec = rec_by_tmdb_id[str(movie_data["tmdb_id"])]
            movie_data["score"] = rec["score"]
            movie_data["explanation"] = rec.get("explanation")

        response_data = {"variant": result.get("variant"), "results": serialized}
        cache.set(cache_key, response_data, timeout=settings.RECOMMENDATION_CACHE_TTL_SECONDS)
        return Response(response_data)
