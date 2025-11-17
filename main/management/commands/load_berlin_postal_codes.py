from django.core.management.base import BaseCommand, CommandError
from main.models import AudienceCategory, AudienceOption, BerlinPostalCode
import csv
from pathlib import Path

SAMPLE = {
    # Minimal sample for demonstration. Replace with full dataset.
    '10115': 'Mitte',
    '10243': 'Friedrichshain-Kreuzberg',
    '10405': 'Pankow',
    '10785': 'Mitte',
    '10969': 'Friedrichshain-Kreuzberg',
    '12043': 'Neukölln',
    '13053': 'Lichtenberg',
    '13507': 'Reinickendorf',
    '14052': 'Charlottenburg-Wilmersdorf',
    '14163': 'Steglitz-Zehlendorf',
}

class Command(BaseCommand):
    help = "Load Berlin postal codes and map them to Bezirke (AudienceOptions under 'Berlin Bezirk')."

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, help='Path to CSV with columns: postal_code,bezirk_name')
        parser.add_argument('--clear', action='store_true', help='Clear existing BerlinPostalCode mappings before load')

    def handle(self, *args, **options):
        csv_path = options.get('csv')
        clear = options.get('clear', False)

        cat, _ = AudienceCategory.objects.get_or_create(name='Berlin Bezirk')

        if clear:
            BerlinPostalCode.objects.all().delete()

        rows = []
        if csv_path:
            p = Path(csv_path)
            if not p.exists():
                raise CommandError(f"CSV not found: {csv_path}")
            with p.open(newline='', encoding='utf-8') as fh:
                reader = csv.DictReader(fh)
                for r in reader:
                    code = (r.get('postal_code') or '').strip()
                    bezirk = (r.get('bezirk_name') or '').strip()
                    if not code or not bezirk:
                        continue
                    rows.append((code, bezirk))
        else:
            self.stdout.write(self.style.WARNING('No CSV provided; loading SAMPLE data.'))
            rows = list(SAMPLE.items())

        created_count = 0
        for code, bezirk_name in rows:
            opt, _ = AudienceOption.objects.get_or_create(category=cat, name=bezirk_name)
            obj, created = BerlinPostalCode.objects.get_or_create(code=code, defaults={'bezirk': opt})
            if not created and obj.bezirk_id != opt.id:
                obj.bezirk = opt
                obj.save(update_fields=['bezirk'])
            created_count += 1 if created else 0

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(rows)} postal code mappings; created {created_count} new entries."))
