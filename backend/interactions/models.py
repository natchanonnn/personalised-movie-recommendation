from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from movies.models import Movie


class Rating(models.Model):
    """A user's current rating (+ optional written review) for a movie.
    One row per (user, movie) -- rating again updates this row rather than
    creating a new one, matching how most review platforms actually work
    (Letterboxd-style) instead of keeping a full ratings history.

    This is also the model that maps most directly onto the
    recommendation-service's training data shape: (user_id, item_id,
    rating, timestamp). Movie.tmdb_id is that item_id -- exporting this
    table on a schedule is the natural path to refreshing the
    recommendation-service's interactions data with real platform activity
    instead of the original offline dataset it was trained on.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="ratings")
    score = models.FloatField(
        validators=[MinValueValidator(0.5), MaxValueValidator(5.0)],
        help_text="0.5-5.0 stars, half-star increments",
    )
    review_text = models.TextField(blank=True)
    contains_spoilers = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "movie"], name="unique_user_movie_rating"),
        ]
        indexes = [
            models.Index(fields=["movie", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} rated {self.movie} {self.score}"


class InteractionType(models.TextChoices):
    VIEW = "view", "Viewed detail page"
    WATCHLIST_ADD = "watchlist_add", "Added to watchlist"
    WATCHLIST_REMOVE = "watchlist_remove", "Removed from watchlist"
    RATE = "rate", "Rated"  # logged alongside Rating so the activity feed / training export has one place to read from


class Interaction(models.Model):
    """Append-only event log of both implicit signals (viewed a detail
    page) and a record of explicit ones (rated) -- separate from Rating
    (one mutable row per user/movie) since these are a genuinely different
    shape: many rows per user, never updated. Doubles as extra training
    signal for the recommendation-service beyond explicit ratings, and as
    the source for "recently viewed" style features.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interactions")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["movie", "interaction_type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.interaction_type} {self.movie}"


class Watchlist(models.Model):
    """Current watchlist state -- distinct from the WATCHLIST_ADD/_REMOVE
    rows in Interaction (the log of when things changed). Query this to
    render a user's watchlist page; query Interaction for activity history
    or training data. Keeping both avoids "reduce over every add/remove
    event" just to answer "what's on my watchlist right now".
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_entries")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="watchlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "movie"], name="unique_watchlist_entry"),
        ]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.movie} on {self.user}'s watchlist"