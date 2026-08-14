# pyrefly: ignore-errors
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from interactions.models import Rating
from movies.models import Movie

from .client import RecommendationServiceError

User = get_user_model()


class RecommendationsViewTests(APITestCase):
    client: APIClient

    def setUp(self):
        cache.clear()
        self.url = reverse("recommendations")
        self.user = User.objects.create_user(username="alice", password="pw12345!")
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(tmdb_id=1, title="Avengers")

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_no_rating_history_short_circuits_without_calling_service(self):
        with patch("recommendations.views.get_recommendations") as mock_get:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])
        mock_get.assert_not_called()

    def test_successful_recommendations_are_enriched_with_local_movie_data(self):
        Rating.objects.create(user=self.user, movie=self.movie, score=4.5)
        service_response = {
            "variant": "collaborative",
            "items": [{"item_id": "1", "score": 0.9, "explanation": "Because you liked similar sci-fi."}],
        }

        with patch("recommendations.views.get_recommendations", return_value=service_response) as mock_get:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["variant"], "collaborative")
        self.assertEqual(len(response.data["results"]), 1)
        result = response.data["results"][0]
        self.assertEqual(result["title"], "Avengers")
        self.assertEqual(result["explanation"], "Because you liked similar sci-fi.")
        mock_get.assert_called_once()

    def test_repeated_call_is_served_from_cache(self):
        Rating.objects.create(user=self.user, movie=self.movie, score=4.5)
        service_response = {
            "variant": "collaborative",
            "items": [{"item_id": "1", "score": 0.9, "explanation": "Because you liked similar sci-fi."}],
        }

        with patch("recommendations.views.get_recommendations", return_value=service_response) as mock_get:
            self.client.get(self.url)
            self.client.get(self.url)

        mock_get.assert_called_once()  # second call hit the cache, not the service

    def test_new_rating_invalidates_the_cache_key(self):
        Rating.objects.create(user=self.user, movie=self.movie, score=4.5)
        service_response = {"variant": "collaborative", "items": []}

        with patch("recommendations.views.get_recommendations", return_value=service_response) as mock_get:
            self.client.get(self.url)
            # A new rating changes `history`, which changes the cache key.
            other_movie = Movie.objects.create(tmdb_id=2, title="Interstellar")
            Rating.objects.create(user=self.user, movie=other_movie, score=5.0)
            self.client.get(self.url)

        self.assertEqual(mock_get.call_count, 2)

    def test_service_unavailable_returns_503(self):
        Rating.objects.create(user=self.user, movie=self.movie, score=4.5)

        with patch(
            "recommendations.views.get_recommendations",
            side_effect=RecommendationServiceError("connection refused"),
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_k_is_clamped_to_configured_bounds(self):
        Rating.objects.create(user=self.user, movie=self.movie, score=4.5)
        service_response = {"variant": "collaborative", "items": []}

        with patch("recommendations.views.get_recommendations", return_value=service_response) as mock_get:
            self.client.get(self.url, {"k": "99999"})

        called_kwargs = mock_get.call_args.kwargs
        from django.conf import settings

        self.assertEqual(called_kwargs["k"], settings.RECOMMENDATION_MAX_K)

    def test_invalid_k_returns_400(self):
        response = self.client.get(self.url, {"k": "not-a-number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
