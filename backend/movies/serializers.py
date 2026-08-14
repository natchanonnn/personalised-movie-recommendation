from rest_framework import serializers

from .models import CastCredit, CrewCredit, Genre, Movie, Person


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class PersonSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["id", "name"]


class MovieSearchResultSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "release_date", "genres", "tmdb_vote_average", "backdrop_path"]


class CastCreditSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="person.name", read_only=True)

    class Meta:
        model = CastCredit
        fields = ["name", "character_name", "billing_order"]


class CrewCreditSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="person.name", read_only=True)

    class Meta:
        model = CrewCredit
        fields = ["name", "department", "job"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    # Sourced from the through-models (not the `cast`/`crew` M2M fields
    # directly) so character_name/billing_order and department/job come
    # along for free.
    cast = CastCreditSerializer(source="cast_credits", many=True, read_only=True)
    crew = CrewCreditSerializer(source="crew_credits", many=True, read_only=True)

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
            "cast",
            "crew",
        ]