# ============================================================
# PHASE 2: URLs using DefaultRouter
# ============================================================
# BEFORE (Generic Views): 4 manual path() entries for portfolio + projects.
#
# AFTER (DefaultRouter): 1 router.register() per resource.
# The router generates all 6 RESTful URL patterns automatically.
#
# Generated URLs:
#   GET    /api/portfolio/        → PortfolioViewSet.list()
#   POST   /api/portfolio/        → PortfolioViewSet.create()
#   GET    /api/portfolio/<pk>/   → PortfolioViewSet.retrieve()
#   PUT    /api/portfolio/<pk>/   → PortfolioViewSet.update()
#   PATCH  /api/portfolio/<pk>/   → PortfolioViewSet.partial_update()
#   DELETE /api/portfolio/<pk>/   → PortfolioViewSet.destroy()
#   (same pattern for /api/projects/)
#
# RegisterView and MeView are not ViewSets, so they stay as manual path() entries.
# ============================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, MeView, PortfolioViewSet, ProjectViewSet

# DefaultRouter also generates a browsable API root at /api/
router = DefaultRouter()
router.register("portfolio", PortfolioViewSet, basename="portfolio")
router.register("projects", ProjectViewSet, basename="project")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    # Include all router-generated URLs
    path("", include(router.urls)),
]
