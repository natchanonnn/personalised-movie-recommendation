from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Movie
from .serializers import MovieDetailSerializer, MovieSearchResultSerializer


class MovieSearchView(APIView):
    """GET /v1/movies/search/?q=<title>&limit=<n>

    Fuzzy/typo-tolerant ranked search via Postgres trigram similarity (see
    the 0002_trigram_search migration) when running on Postgres. Falls back
    to a plain case-insensitive substring match on SQLite, where trigram
    search isn't available -- local dev without Postgres still works, just
    without fuzzy ranking.

    Also doubles as the movie-browsing feed: an empty/missing `q` returns
    the top-rated movies, which is what the frontend's homepage loads.

    Every result's tmdb_id doubles as the recommendation-service's item_id
    -- usable directly in a /v1/recommendations history entry, no lookup.
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            return Response({"detail": "limit must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
        limit = max(1, min(limit, 50))

        if not query:
            results = Movie.objects.order_by("-tmdb_vote_average")[:limit]
        elif connection.vendor == "postgresql":
            from django.contrib.postgres.search import TrigramSimilarity

            results = (
                Movie.objects.annotate(similarity=TrigramSimilarity("title", query))
                .filter(Q(similarity__gt=0.2) | Q(title__icontains=query))
                .order_by("-similarity", "title")[:limit]
            )
        else:
            results = Movie.objects.filter(title__icontains=query).order_by("title")[:limit]

        serializer = MovieSearchResultSerializer(results, many=True)
        return Response({"query": query, "results": serializer.data})


class MovieDetailView(APIView):
    """GET /v1/movies/<id>/"""

    permission_classes = (AllowAny,)

    def get(self, request, movie_id):
        movie = get_object_or_404(Movie, id=movie_id)
        serializer = MovieDetailSerializer(movie)
        return Response(serializer.data)