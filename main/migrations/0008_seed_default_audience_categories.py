from django.db import migrations

def seed_categories(apps, schema_editor):
    AudienceCategory = apps.get_model('main', 'AudienceCategory')
    for name in ['State', 'City']:
        AudienceCategory.objects.get_or_create(name=name)

class Migration(migrations.Migration):
    dependencies = [
        ('main', '0007_audiencecategory_audienceoption_poll_groups'),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
