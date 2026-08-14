from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Movie, Person
from .serializers import MovieDetailSerializer, MovieSearchResultSerializer, PersonSearchResultSerializer


class MovieSearchView(APIView):
    """GET /v1/movies/search/?q=<title>&limit=<n>&person=<person_id>

    Fuzzy/typo-tolerant ranked search via Postgres trigram similarity (see
    the 0002_trigram_search migration) when running on Postgres. Falls back
    to a plain case-insensitive substring match on SQLite, where trigram
    search isn't available -- local dev without Postgres still works, just
    without fuzzy ranking.

    Also doubles as the movie-browsing feed: an empty/missing `q` returns
    the top-rated movies, which is what the frontend's homepage loads.

    `person` (a Person id, e.g. picked via PersonSearchView) narrows results
    to movies where that person appears as cast OR crew -- combinable with
    `q`.

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

        base_queryset = Movie.objects.prefetch_related("genres")
        person_id = request.query_params.get("person")
        if person_id:
            try:
                person_id = int(person_id)
            except ValueError:
                return Response({"detail": "person must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            base_queryset = base_queryset.filter(
                Q(cast_credits__person_id=person_id) | Q(crew_credits__person_id=person_id)
            ).distinct()

        if not query:
            results = base_queryset.order_by("-tmdb_vote_average")[:limit]
        elif connection.vendor == "postgresql":
            from django.contrib.postgres.search import TrigramSimilarity

            results = (
                base_queryset.annotate(similarity=TrigramSimilarity("title", query))
                .filter(Q(similarity__gt=0.2) | Q(title__icontains=query))
                .order_by("-similarity", "title")[:limit]
            )
        else:
            results = base_queryset.filter(title__icontains=query).order_by("title")[:limit]

        serializer = MovieSearchResultSerializer(results, many=True)
        return Response({"query": query, "results": serializer.data})


class PersonSearchView(APIView):
    """GET /v1/movies/people/search/?q=<name>&limit=<n>

    Search cast and crew by name -- both are rows in the same Person table
    (someone can act in one movie and direct another), so this is a single
    unified search rather than separate cast/crew endpoints. Same
    fuzzy/typo-tolerant trigram-on-Postgres, icontains-elsewhere approach as
    MovieSearchView.

    Unlike movie search, an empty `q` returns no results rather than a
    default browse list -- there's no popularity/rating field on Person to
    rank a "top people" feed by.
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
            return Response({"query": query, "results": []})
        elif connection.vendor == "postgresql":
            from django.contrib.postgres.search import TrigramSimilarity

            results = (
                Person.objects.annotate(similarity=TrigramSimilarity("name", query))
                .filter(Q(similarity__gt=0.2) | Q(name__icontains=query))
                .order_by("-similarity", "name")[:limit]
            )
        else:
            results = Person.objects.filter(name__icontains=query).order_by("name")[:limit]

        serializer = PersonSearchResultSerializer(results, many=True)
        return Response({"query": query, "results": serializer.data})


class MovieDetailView(APIView):
    """GET /v1/movies/<id>/"""

    permission_classes = (AllowAny,)

    def get(self, request, movie_id):
        queryset = Movie.objects.prefetch_related(
            "genres", "cast_credits__person", "crew_credits__person"
        )
        movie = get_object_or_404(queryset, id=movie_id)
        serializer = MovieDetailSerializer(movie)
        return Response(serializer.data)