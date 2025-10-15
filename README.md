# Informatik-Projekt

Projekt für die Schule

USEFUL COPY'S:

* TO RUN VENV IN TERMINAL (linux): source .venv/bin/activate

* TO RUN VENV IN TERMINAL (windows): venv\Scripts\activate 

* TO RUN SERVER : python manage.py runserver

* Sending mails on Django: https://docs.djangoproject.com/en/5.2/topics/email/ 

* Django Documentation: https://docs.djangoproject.com/en/5.2/

* Django writing your first app: https://docs.djangoproject.com/en/5.2/intro/tutorial01/

* git cheet sheet: https://training.github.com/downloads/github-git-cheat-sheet.pdf

The migrate command takes all the migrations that haven’t been applied (Django tracks which ones are applied using a special table in your database called django_migrations) and runs them against your database - essentially, synchronizing the changes you made to your models with the schema in the database.

Migrations are very powerful and let you change your models over time, as you develop your project, without the need to delete your database or tables and make new ones - it specializes in upgrading your database live, without losing data. We’ll cover them in more depth in a later part of the tutorial, but for now, remember the three-step guide to making model changes:

Change your models (in models.py).

Run python manage.py makemigrations to create migrations for those changes

Run python manage.py migrate to apply those changes to the database.
