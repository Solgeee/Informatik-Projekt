from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/main/", permanent=False)),  # Redirect root to /main/
    path("main/", include("main.urls")),
    path("admin/", admin.site.urls),
]