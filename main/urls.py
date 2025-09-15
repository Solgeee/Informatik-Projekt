# Connects a URL to a view
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
]