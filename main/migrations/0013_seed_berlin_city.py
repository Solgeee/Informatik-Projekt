from django.db import migrations


def seed_berlin_city(apps, schema_editor):
    AudienceCategory = apps.get_model('main', 'AudienceCategory')
    AudienceOption = apps.get_model('main', 'AudienceOption')
    city_cat = AudienceCategory.objects.filter(name='City').first()
    if not city_cat:
        return
    AudienceOption.objects.get_or_create(category=city_cat, name='Berlin')


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0012_seed_berlin_bezirk'),
    ]

    operations = [
        migrations.RunPython(seed_berlin_city, migrations.RunPython.noop),
    ]
