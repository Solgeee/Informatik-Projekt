# Connects a URL to a view
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("vote/", views.vote, name="vote"),
    path("results/", views.results, name="results"),
    path("login/", views.login, name="login"),
]