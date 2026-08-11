import ast
import csv
import json
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from movies.models import CastCredit, CrewCredit, Genre, Movie, Person
from tqdm import tqdm

# credits.cast/credits.crew routinely exceed the csv module's default
# 131072-byte field limit for movies with large ensembles -- raise it.
# sys.maxsize can overflow the underlying C long on some platforms, so back
# off by an order of magnitude until it's accepted rather than assuming it works.
_max_field_size = sys.maxsize
while True:
    try:
        csv.field_size_limit(_max_field_size)
        break
    except OverflowError:
        _max_field_size //= 10


def parse_json_field(raw):
    """List/dict-valued columns in this dataset are JSON-looking strings.
    Most are valid JSON; some export tools re-save these with single quotes
    / Python literal syntax instead -- try json.loads first, fall back to
    ast.literal_eval before giving up.
    """
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return []


def parse_number(raw, cast):
    if raw in (None, "", "nan"):
        return None
    try:
        return cast(float(raw))
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = (
        "Import movies from a consolidated TMDB CSV export -- one file with "
        "cast/crew flattened into credits.cast / credits.crew columns on the "
        "same row, rather than the old separate movies.csv + credits.csv split."
    )

    def add_arguments(self, parser):
        parser.add_argument("movies_csv", help="Path to the consolidated movies CSV")
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Only process the first N rows (useful for a quick test run)",
        )

    def handle(self, *args, **options):
        path = options["movies_csv"]
        limit = options["limit"]

        movie_count = 0
        cast_count = 0
        crew_count = 0

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in tqdm(enumerate(reader)):
                if limit is not None and i >= limit:
                    break
                c, r = self._import_row(row)
                movie_count += 1
                cast_count += c
                crew_count += r

        self.stdout.write(
            self.style.SUCCESS(f"Imported/updated {movie_count} movies, {cast_count} cast credits, {crew_count} crew credits")
        )

    @transaction.atomic
    def _import_row(self, row):
        tmdb_id = int(row["id"])

        # production_countries is a JSON list of {"iso_3166_1": "US", "name": "..."};
        # Movie.country is a single CharField -- lossy on purpose, takes just
        # the first listed country. Co-productions lose everything after that.
        countries = parse_json_field(row.get("production_countries", ""))
        country = countries[0]["name"] if countries else ""

        movie, _created = Movie.objects.update_or_create(
            tmdb_id=tmdb_id,
            defaults={
                "title": (row.get("title") or "").strip(),
                # "original_title": (row.get("original_title") or "").strip(),
                "release_date": row.get("release_date") or None,
                "duration_minutes": parse_number(row.get("runtime"), int),
                "tmdb_vote_average": parse_number(row.get("vote_average"), float),
                "synopsis": (row.get("overview") or "").strip(),
                "backdrop_path": (row.get("backdrop_path") or "").strip(),
                "country": country[:100],
                "budget_usd": parse_number(row.get("budget"), int),
                "revenue_usd": parse_number(row.get("revenue"), int),
            },
        )

        # Columns present in this CSV with no home in the current schema yet --
        # skipped, not silently mismapped:
        #   adult, homepage, imdb_id, origin_country, original_language,
        #   popularity, poster_path, production_companies, spoken_languages,
        #   status, tagline, video, vote_count, softcore
        #   belongs_to_collection.{id,name,poster_path,backdrop_path} -- would need
        #     a Collection/franchise model to hold these
        #   keywords.keywords -- would need the Keyword model back

        genre_names = [g["name"] for g in parse_json_field(row.get("genres", "")) if "name" in g]
        genres = [Genre.objects.get_or_create(name=name)[0] for name in genre_names]
        movie.genres.set(genres)

        cast_created = self._import_cast(movie, row.get("credits.cast", ""))
        crew_created = self._import_crew(movie, row.get("credits.crew", ""))
        return cast_created, crew_created

    def _import_cast(self, movie, raw):
        # NOTE: Person has no tmdb_id field, so dedup below is by name only --
        # two different real people who happen to share an exact name will
        # collide into one Person row. entry["id"] here IS TMDB's person id;
        # add a tmdb_id field to Person and dedup on that instead if this
        # becomes a real problem (it will, eventually, at large enough scale).
        created = 0
        for entry in parse_json_field(raw):
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            person, _ = Person.objects.get_or_create(name=name)
            CastCredit.objects.update_or_create(
                movie=movie, person=person, character_name=(entry.get("character") or "").strip(),
                defaults={"billing_order": entry.get("order")},
            )
            created += 1
        return created

    def _import_crew(self, movie, raw):
        created = 0
        for entry in parse_json_field(raw):
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            person, _ = Person.objects.get_or_create(name=name)
            CrewCredit.objects.update_or_create(
                movie=movie, person=person, job=(entry.get("job") or "").strip(),
                defaults={"department": (entry.get("department") or "").strip()},
            )
            created += 1
        return created