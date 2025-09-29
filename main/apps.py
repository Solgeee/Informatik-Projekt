#THIS FOLDER IS ONLY FOR CUSTOMIZATION OF THINGS LIKE NAME OF WEBSITE
from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
class LoginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'login'
