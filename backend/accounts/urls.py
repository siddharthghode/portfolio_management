from django.urls import path
from .views import RegisterView, MeView, PortfolioView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
]