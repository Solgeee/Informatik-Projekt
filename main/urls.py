# Connects a URL to a view
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("vote/<int:poll_id>/", views.vote, name="vote"),
    path("results/<int:poll_id>/", views.results, name="results"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),
    path("register/name/", views.register_name, name="register_name"),
    # Old groups route kept for backward compatibility -> now restrictions
    path("register/groups/", views.register_restrictions, name="register_groups"),
    path("register/restrictions/", views.register_restrictions, name="register_restrictions"),
    path("restrictions/", views.register_restrictions, name="restrictions"),
    path("register/email/", views.register_email, name="register_email"),
]