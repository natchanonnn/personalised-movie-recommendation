from django.urls import path

from .views import MovieDetailView, MovieSearchView, PersonSearchView

urlpatterns = [
    path("search/", MovieSearchView.as_view(), name="movie-search"),
    path("people/search/", PersonSearchView.as_view(), name="person-search"),
    path("<int:movie_id>/", MovieDetailView.as_view(), name="movie-detail"),
]
