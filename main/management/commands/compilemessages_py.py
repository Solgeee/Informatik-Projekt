from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys

class Command(BaseCommand):
    help = "Compile .po files to .mo using polib (no system gettext required)."

    def add_arguments(self, parser):
        parser.add_argument('--locale', '-l', action='append', dest='locales', help='Locale(s) to compile (e.g., de). Defaults to all found locales.')

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError:
            self.stderr.write(self.style.ERROR('polib is not installed. Install requirements first: pip install -r requirements.txt'))
            sys.exit(1)

        verbosity = int(options.get('verbosity', 1))
        target_locales = options.get('locales')

        locales_dirs = list(getattr(settings, 'LOCALE_PATHS', []))
        # Also include app-level locale dirs, if any
        project_base = getattr(settings, 'BASE_DIR', os.getcwd())
        default_locale_dir = os.path.join(project_base, 'locale')
        if os.path.isdir(default_locale_dir):
            locales_dirs.append(default_locale_dir)

        if not locales_dirs:
            self.stdout.write(self.style.WARNING('No LOCALE_PATHS found. Nothing to compile.'))
            return

        compiled = 0
        for root in locales_dirs:
            if not os.path.isdir(root):
                continue
            for dir_name in os.listdir(root):
                if target_locales and dir_name not in target_locales:
                    continue
                lc_messages = os.path.join(root, dir_name, 'LC_MESSAGES')
                if not os.path.isdir(lc_messages):
                    continue
                for fname in os.listdir(lc_messages):
                    if not fname.endswith('.po'):
                        continue
                    po_path = os.path.join(lc_messages, fname)
                    mo_path = po_path[:-3] + '.mo'
                    try:
                        po = polib.pofile(po_path)
                        po.save_as_mofile(mo_path)
                        compiled += 1
                        if verbosity:
                            self.stdout.write(self.style.SUCCESS(f'Compiled {po_path} -> {mo_path}'))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Failed to compile {po_path}: {e}'))
        if compiled == 0:
            self.stdout.write(self.style.WARNING('No .po files compiled.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done. Compiled {compiled} file(s).'))
