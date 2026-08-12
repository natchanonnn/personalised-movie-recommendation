from django.urls import path
from .views import RatingViewSet, WatchlistViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("ratings", RatingViewSet, basename="rating")
router.register("watchlist", WatchlistViewSet, basename="watchlist")

urlpatterns = router.urls