from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, TokenRefreshView, LogoutView, MeView,
    PortfolioViewSet, ProjectViewSet,
    UserSessionViewSet, SecurityEventViewSet,
)

router = DefaultRouter()
router.register("portfolio", PortfolioViewSet, basename="portfolio")
router.register("projects", ProjectViewSet, basename="project")
router.register("sessions", UserSessionViewSet, basename="session")
router.register("security-events", SecurityEventViewSet, basename="security-event")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
