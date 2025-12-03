# Informatik‑Projekt



End‑to‑end guide to set up and run this Django project on a fresh Windows machine 

## Prerequisites (Windows)
- VS Code is already installed.
- Install required tools using Winget (recommended) or download manually.

### Option A: Install via Winget (recommended)
Run these commands in a Command Prompt (cmd):

```
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e
```

Close and reopen the terminal after installation so PATH updates take effect.

### Option B: Manual installers
- Git for Windows: https://git-scm.com/download/win
- Python 3.12.x (64‑bit): https://www.python.org/downloads/windows/
	- During setup, check “Add Python to PATH”.

Optional.venv\Scripts\activate
python manage.py compilemessages_py -l de:
- Python extension: ms-python.python
- Pylance extension: ms-pytho
n.vscode-pylance

## Get the code
Pick one of the following:

### Clone with Git
```
git clone https://github.com/Solgeee/Informatik-Projekt.git
cd Informatik-Projekt
```

### Or download ZIP
1) Go to the repository page in your browser.
2) Click “Code” → “Download ZIP”.
3) Extract the ZIP and open the folder in VS Code.

## Create and activate a virtual environment
From the project root folder (where `manage.py` is):

```
python -m venv .venv
.venv\Scripts\activate
```

If `python` isn’t found, try:

```
py -3.12 -m venv .venv
.venv\Scripts\activate
```

## Install dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```

This installs Django and tools used by this project (including a Python‑based translation compiler, so you don’t need system gettext).

## Initialize the database
```
python manage.py migrate
```

This sets up SQLite in `db.sqlite3` and seeds core categories (including “Berlin Bezirk” and the City entry via migrations).

## Load Berlin postal‑code → district mappings
To enable automatic user restrictions by postal code and let polls target districts, load the data:

```
python manage.py load_berlin_postal_codes --csv "path\to\berlin_postal_codes.csv" --clear
```

CSV format (headers required):
```
postal_code,bezirk_name
10115,Mitte
10243,Friedrichshain-Kreuzberg
...
```

If you don’t have a CSV yet, you can omit `--csv` to load a small SAMPLE (for local testing only).

## Compile translations (English/German)
The project includes a Python fallback for compiling translations. Run:

```
python manage.py compilemessages_py -l de
```

No system gettext is required.

## Create an admin user (for /admin)
```
python manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

## Run the development server
```
python manage.py runserver
```

Open http://127.0.0.1:8000/main/ in your browser.

## Using the app
- Language toggle: Click the flag in the header to switch EN/DE.
- Register as a user: Provide name, email/username, password, and postal code.
	- If the postal code maps to a Berlin district, your restrictions are auto‑assigned.
	- If other categories are required, you’ll be guided to confirm them.
- Admin (/admin):
	- Login with the superuser you created.
	- Create/edit Polls. Assign target districts (Bezirke) using the “Districts (Bezirke)” dual‑list selector.
	- Users whose postal code maps to assigned districts will see those polls.

## Common issues and fixes
- “python/pip not found”: Close and reopen the terminal after installing Python; or use `py -3.12 -m pip ...`.
- VS Code doesn’t use the venv: In Terminal, ensure you see `(.venv)` prefix; if not, run `.venv\Scripts\activate`.
- Translations didn’t switch: Ensure you ran `compilemessages_py` and refresh the page; cookies/session store language.
- No districts to select in Poll admin: Make sure you ran the `load_berlin_postal_codes` command with your CSV.

## Useful links
- Django docs: https://docs.djangoproject.com/en/5.2/
- First Django app tutorial: https://docs.djangoproject.com/en/5.2/intro/tutorial01/
- Git cheat sheet: https://training.github.com/downloads/github-git-cheat-sheet.pdf

