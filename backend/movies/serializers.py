from rest_framework import serializers

from .models import Genre, Movie


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class MovieSearchResultSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "release_date", "genres", "tmdb_vote_average", "backdrop_path"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "release_date",
            "duration_minutes",
            "genres",
            "tmdb_vote_average",
            "backdrop_path",
            "synopsis",
        ]