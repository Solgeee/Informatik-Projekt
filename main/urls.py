# Connects a URL to a view
from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),  # Root URL now loads login page
    path("vote/", views.vote, name="vote"),
    path("results/", views.results, name="results"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
]