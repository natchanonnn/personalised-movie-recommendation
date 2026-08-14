# pyrefly: ignore-errors
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from movies.models import Movie

from .models import Rating, Watchlist

User = get_user_model()


class RatingOwnershipTests(APITestCase):
    """The important suite: makes sure one user can never read-write
    another user's rating through the API (IDOR check)."""

    client: APIClient

    def setUp(self):
        self.movie = Movie.objects.create(tmdb_id=1, title="Avengers")
        self.other_movie = Movie.objects.create(tmdb_id=2, title="Interstellar")
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.list_url = reverse("rating-list")

    def test_anonymous_cannot_create_rating(self):
        response = self.client.post(self.list_url, {"movie": self.movie.tmdb_id, "score": 4.5})
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_rating_upserts_not_duplicates(self):
        self.client.force_authenticate(self.alice)
        self.client.post(self.list_url, {"movie": self.movie.tmdb_id, "score": 3.0})
        self.client.post(self.list_url, {"movie": self.movie.tmdb_id, "score": 4.5})

        ratings = Rating.objects.filter(user=self.alice, movie=self.movie)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().score, 4.5)

    def test_user_cannot_edit_another_users_rating(self):
        rating = Rating.objects.create(user=self.alice, movie=self.movie, score=5.0)
        detail_url = reverse("rating-detail", args=[rating.id])

        self.client.force_authenticate(self.bob)
        response = self.client.patch(detail_url, {"score": 0.5})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        rating.refresh_from_db()
        self.assertEqual(rating.score, 5.0)  # untouched

    def test_user_cannot_delete_another_users_rating(self):
        rating = Rating.objects.create(user=self.alice, movie=self.movie, score=5.0)
        detail_url = reverse("rating-detail", args=[rating.id])

        self.client.force_authenticate(self.bob)
        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Rating.objects.filter(id=rating.id).exists())

    def test_anonymous_can_read_ratings_for_a_movie(self):
        Rating.objects.create(user=self.alice, movie=self.movie, score=4.0)
        response = self.client.get(self.list_url, {"movie": self.movie.tmdb_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_mine_filter_excludes_other_users_ratings(self):
        Rating.objects.create(user=self.alice, movie=self.movie, score=4.0)
        Rating.objects.create(user=self.bob, movie=self.other_movie, score=2.0)

        self.client.force_authenticate(self.alice)
        response = self.client.get(self.list_url, {"mine": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["movie"], self.movie.tmdb_id)


class WatchlistTests(APITestCase):
    client: APIClient

    def setUp(self):
        self.movie = Movie.objects.create(tmdb_id=1, title="Avengers")
        self.alice = User.objects.create_user(username="alice", password="pw12345!")
        self.bob = User.objects.create_user(username="bob", password="pw12345!")
        self.list_url = reverse("watchlist-list")

    def test_requires_authentication(self):
        response = self.client.post(self.list_url, {"movie": self.movie.tmdb_id})
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_adding_twice_is_idempotent(self):
        self.client.force_authenticate(self.alice)
        first = self.client.post(self.list_url, {"movie": self.movie.tmdb_id})
        second = self.client.post(self.list_url, {"movie": self.movie.tmdb_id})

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Watchlist.objects.filter(user=self.alice, movie=self.movie).count(), 1)

    def test_list_only_returns_own_entries(self):
        Watchlist.objects.create(user=self.alice, movie=self.movie)
        other_movie = Movie.objects.create(tmdb_id=2, title="Interstellar")
        Watchlist.objects.create(user=self.bob, movie=other_movie)

        self.client.force_authenticate(self.alice)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["movie"], self.movie.tmdb_id)

    def test_cannot_see_or_delete_another_users_entry(self):
        entry = Watchlist.objects.create(user=self.bob, movie=self.movie)
        detail_url = reverse("watchlist-detail", args=[entry.id])

        self.client.force_authenticate(self.alice)
        response = self.client.delete(detail_url)

        # get_queryset() is scoped to request.user, so Alice's queryset
        # never contains Bob's entry -- this 404s rather than 403.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Watchlist.objects.filter(id=entry.id).exists())
