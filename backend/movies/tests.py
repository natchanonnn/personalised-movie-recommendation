# pyrefly: ignore-errors
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import CastCredit, CrewCredit, Genre, Movie, Person


class MovieSearchTests(APITestCase):
    client: APIClient

    def setUp(self):
        self.search_url = reverse("movie-search")
        action = Genre.objects.create(name="Action")
        drama = Genre.objects.create(name="Drama")

        self.avengers = Movie.objects.create(
            tmdb_id=1, title="Avengers", tmdb_vote_average=8.0, release_date="2012-05-04"
        )
        self.avengers.genres.add(action)

        self.drama_movie = Movie.objects.create(
            tmdb_id=2, title="Quiet Room", tmdb_vote_average=6.0, release_date="2019-01-10"
        )
        self.drama_movie.genres.add(drama)

        self.director = Person.objects.create(name="Jane Director")
        CrewCredit.objects.create(movie=self.avengers, person=self.director, job="Director")

    def test_search_by_title(self):
        response = self.client.get(self.search_url, {"q": "Aveng"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["results"]]
        self.assertIn("Avengers", titles)

    def test_empty_query_returns_top_rated_browse_feed(self):
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ordered by -tmdb_vote_average
        self.assertEqual(response.data["results"][0]["title"], "Avengers")

    def test_filter_by_person(self):
        response = self.client.get(self.search_url, {"person": self.director.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["results"]]
        self.assertEqual(titles, ["Avengers"])

    def test_invalid_limit_returns_400(self):
        response = self.client.get(self.search_url, {"limit": "not-a-number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_year(self):
        response = self.client.get(self.search_url, {"year": 2012})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [r["title"] for r in response.data["results"]]
        self.assertEqual(titles, ["Avengers"])

    def test_invalid_year_returns_400(self):
        response = self.client.get(self.search_url, {"year": "not-a-number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_does_not_n_plus_1_on_genres(self):
        # Regression test for the missing prefetch_related("genres") bug --
        # result count shouldn't change the query count.
        for i in range(3, 13):
            Movie.objects.create(tmdb_id=i, title=f"Filler {i}", tmdb_vote_average=5.0)

        with self.assertNumQueries(2):  # 1 for movies, 1 prefetch for genres
            response = self.client.get(self.search_url, {"limit": 50})
            list(response.data["results"])  # force serialization


class MovieDetailTests(APITestCase):
    client: APIClient

    def setUp(self):
        self.movie = Movie.objects.create(tmdb_id=42, title="Interstellar")
        person = Person.objects.create(name="Matthew M.")
        CastCredit.objects.create(movie=self.movie, person=person, character_name="Cooper", billing_order=1)

    def test_get_existing_movie(self):
        url = reverse("movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Interstellar")
        self.assertEqual(len(response.data["cast"]), 1)

    def test_get_missing_movie_404(self):
        url = reverse("movie-detail", args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PersonSearchTests(APITestCase):
    client: APIClient

    def setUp(self):
        self.search_url = reverse("person-search")
        Person.objects.create(name="Jane Director")

    def test_empty_query_returns_no_results(self):
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_search_by_name(self):
        response = self.client.get(self.search_url, {"q": "Jane"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.data["results"]]
        self.assertIn("Jane Director", names)
