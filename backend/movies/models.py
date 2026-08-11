from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return self.name
 
 
class Person(models.Model):
    """Anyone who worked on a movie -- actor or crew (including directors).
    One row per real person; what they did on a given movie (played a
    character, directed, wrote) lives on the credit through-models below,
    not here -- the same person can act in one film and direct another,
    or both on the same one.
    """
 
    name = models.CharField(max_length=300, help_text="Actor/crew member's real name")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return self.name
 
 
class Movie(models.Model):
    tmdb_id = models.PositiveIntegerField(unique=True, db_index=True)
 
    title = models.CharField(max_length=300, db_index=True)
    # original_title = models.CharField(max_length=500, blank=True, help_text="Original title if different from translated title")
    release_date = models.DateField(null=True, blank=True)  # tmdb5000 has real rows missing this
    duration_minutes = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    tmdb_vote_average = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)], help_text="TMDB rating out of 10"
    )
    synopsis = models.TextField(blank=True)
    backdrop_path = models.CharField(
        max_length=255,
        blank=True,
        help_text="TMDB relative image path (e.g. '/8kSerJrhrJWKLk1LViesGcnrUPE.jpg') -- "
        "not a full URL, combine with TMDB's image base URL + a size via backdrop_url()",
    )
    country = models.CharField(max_length=100, blank=True)
    budget_usd = models.BigIntegerField(null=True, blank=True, help_text="Budget in USD")
    revenue_usd = models.BigIntegerField(null=True, blank=True, help_text="Revenue in USD")
 
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    cast = models.ManyToManyField(Person, through="CastCredit", related_name="acting_credits")
    crew = models.ManyToManyField(Person, through="CrewCredit", related_name="crew_credits")
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        year = self.release_date.year if self.release_date else "?"
        return f"{self.title} ({year})"
 
    class Meta:
        ordering = ["-release_date"]
 
 
class CastCredit(models.Model):
    """Who played what, in which movie -- the character belongs here, not on Person."""
 
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="cast_credits")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="+")
    character_name = models.CharField(max_length=300, blank=True)
    billing_order = models.PositiveIntegerField(null=True, blank=True)
 
    class Meta:
        ordering = ["billing_order"]
        constraints = [
            models.UniqueConstraint(fields=["movie", "person", "character_name"], name="unique_cast_credit"),
        ]
 
    def __str__(self):
        return f"{self.person} as {self.character_name} in {self.movie}"
 
 
class CrewCredit(models.Model):
    """Directors, writers, producers, etc. -- one shared shape instead of a
    separate Director model, matching how credits.csv itself is structured
    (one crew list, each row has a job).
    """
 
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="crew_credits")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="+")
    department = models.CharField(max_length=100, blank=True)
    job = models.CharField(max_length=100, blank=True, db_index=True)  # e.g. "Director", "Writer"
 
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["movie", "person", "job"], name="unique_crew_credit"),
        ]
 
    def __str__(self):
        return f"{self.person} ({self.job}) on {self.movie}"
 
 
# class UserFavoriteMovie(models.Model):
#     # TODO: change to custom user model
#     user_id = models.IntegerField()
#     movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='favorited_by')
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ['user_id', 'movie']
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"User {self.user_id} favorited {self.movie.title}"


# class Rating(models.Model):
#     # TODO: change to custom user model
#     user_id = models.IntegerField()
#     movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='ratings')
#     rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
#     comment = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         unique_together = ['user_id', 'movie']
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"User {self.user_id} rated {self.movie.title} {self.rating}/10"


# class Comment(models.Model):
#     # TODO: change to custom user model
#     user_id = models.IntegerField()
#     movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
#     text = models.TextField()
#     is_spoiler = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['created_at']

#     def __str__(self):
#         return f"Comment by User {self.user_id} on {self.movie.title}"
