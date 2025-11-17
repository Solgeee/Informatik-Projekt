from django.db import migrations


def seed_berlin_bezirk(apps, schema_editor):
    AudienceCategory = apps.get_model('main', 'AudienceCategory')
    AudienceCategory.objects.get_or_create(name='Berlin Bezirk')


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0011_userprofile'),
    ]

    operations = [
        migrations.RunPython(seed_berlin_bezirk, migrations.RunPython.noop),
    ]
