from django.urls import path
 
from .views import MovieSearchView, MovieDetailView
 
urlpatterns = [
    path("search/", MovieSearchView.as_view(), name="movie-search"),
    path("<int:movie_id>/", MovieDetailView.as_view(), name="movie-detail"),
]
 