# Connects a URL to a view
from django.urls import path

from . import views

urlpatterns = [
    path("", views.welcome, name="home"),
    path("home/", views.home, name="home"),
    path("vote/<int:poll_id>/", views.vote, name="vote"),
    path("results/<int:poll_id>/", views.results, name="results"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("register/name/", views.register_name, name="register_name"),
    path("register/email/", views.register_email, name="register_email"),
    path("welcome/", views.welcome, name="welcome"),
]