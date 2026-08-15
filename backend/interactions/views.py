from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Interaction, InteractionType, Rating, Watchlist
from .serializers import RatingSerializer, WatchlistSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.id


class RatingViewSet(viewsets.ModelViewSet):
    """
    GET    /api/interactions/ratings/?movie=<tmdb_id>          -- all ratings for a movie (public reviews feed)
    GET    /api/interactions/ratings/?movie=<tmdb_id>&mine=1     -- just the current user's own rating for it
    GET    /api/interactions/ratings/summary/?movie=<tmdb_id>      -- rating counts per star bucket, not the raw rows
    POST   /api/interactions/ratings/                                 -- rate/review a movie; upserts, matching
                                                                          Rating's one-row-per-(user,movie) design
    PATCH  /api/interactions/ratings/<id>/                             -- edit your own rating
    DELETE /api/interactions/ratings/<id>/                              -- remove your own rating
    """

    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Rating.objects.select_related("user", "movie")
        # pyrefly: ignore [missing-attribute]
        movie_id = self.request.query_params.get("movie")
        if movie_id:
            qs = qs.filter(movie__tmdb_id=movie_id)
        # pyrefly: ignore [missing-attribute]
        if self.request.query_params.get("mine") and self.request.user.is_authenticated:
            qs = qs.filter(user=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movie = serializer.validated_data["movie"]

        rating, _created = Rating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={
                "score": serializer.validated_data["score"],
                "review_text": serializer.validated_data.get("review_text", ""),
                "contains_spoilers": serializer.validated_data.get("contains_spoilers", False),
            },
        )
        Interaction.objects.create(user=request.user, movie=movie, interaction_type=InteractionType.RATE)

        output = self.get_serializer(rating)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """GET /v1/interactions/ratings/summary/?movie=<tmdb_id>

        Aggregate rating counts per whole-star bucket (1-5, rounding any
        half-star scores to the nearest star) instead of shipping every
        individual Rating row just to render a distribution -- lighter, and
        doesn't expose other users' review text/usernames for something
        that's only ever displayed as a histogram.
        """
        movie_id = request.query_params.get("movie")
        if not movie_id:
            return Response({"detail": "movie is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            movie_id = int(movie_id)
        except ValueError:
            return Response({"detail": "movie must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        scores = list(Rating.objects.filter(movie__tmdb_id=movie_id).values_list("score", flat=True))
        counts = {str(i): 0 for i in range(1, 6)}
        for score in scores:
            bucket = min(5, max(1, round(score)))
            counts[str(bucket)] += 1

        return Response({"movie": movie_id, "total": len(scores), "counts": counts})


class WatchlistViewSet(viewsets.ModelViewSet):
    """
    GET    /api/interactions/watchlist/                     -- current user's watchlist
    GET    /api/interactions/watchlist/?movie=<tmdb_id>      -- just this movie's entry, if any (0 or 1 rows)
    POST   /api/interactions/watchlist/     -- add a movie (idempotent -- adding twice is a no-op, not an error)
    DELETE /api/interactions/watchlist/<id>/ -- remove
    """

    serializer_class = WatchlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Watchlist.objects.filter(user=self.request.user).select_related("movie")
        # pyrefly: ignore [missing-attribute]
        movie_id = self.request.query_params.get("movie")
        if movie_id:
            qs = qs.filter(movie__tmdb_id=movie_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movie = serializer.validated_data["movie"]

        entry, created = Watchlist.objects.get_or_create(user=request.user, movie=movie)
        if created:
            Interaction.objects.create(user=request.user, movie=movie, interaction_type=InteractionType.WATCHLIST_ADD)

        output = self.get_serializer(entry)
        return Response(output.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def perform_destroy(self, instance):
        Interaction.objects.create(
            user=instance.user, movie=instance.movie, interaction_type=InteractionType.WATCHLIST_REMOVE
        )
        instance.delete()