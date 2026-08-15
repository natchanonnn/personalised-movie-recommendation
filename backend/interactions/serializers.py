from rest_framework import serializers

from movies.models import Movie
from movies.serializers import MovieSearchResultSerializer

from .models import Rating, Watchlist


class RatingSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    # Keyed on tmdb_id, not Django's internal pk -- consistent with everything
    # else in this platform being addressed by the recommendation-service's
    # item_id space.
    movie = serializers.SlugRelatedField(slug_field="tmdb_id", queryset=Movie.objects.all())
    # Card-ready movie fields (title, genres, backdrop, tmdb rating) so a
    # "my ratings" list view can render MovieCard straight from this
    # response instead of a follow-up fetch per movie.
    movie_detail = MovieSearchResultSerializer(source="movie", read_only=True)

    class Meta:
        model = Rating
        fields = [
            "id", "movie", "movie_detail", "movie_title", "username", "score",
            "review_text", "contains_spoilers", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "username", "movie_title", "movie_detail", "created_at", "updated_at"]


class WatchlistSerializer(serializers.ModelSerializer):
    movie_title = serializers.CharField(source="movie.title", read_only=True)
    movie = serializers.SlugRelatedField(slug_field="tmdb_id", queryset=Movie.objects.all())
    movie_detail = MovieSearchResultSerializer(source="movie", read_only=True)

    class Meta:
        model = Watchlist
        fields = ["id", "movie", "movie_detail", "movie_title", "added_at"]
        read_only_fields = ["id", "movie_title", "movie_detail", "added_at"]