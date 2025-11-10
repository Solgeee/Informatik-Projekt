from django.db import migrations

def create_options(apps, schema_editor):
    Poll = apps.get_model('main', 'Poll')
    Option = apps.get_model('main', 'Option')
    for poll in Poll.objects.all():
        if poll.options.exists():
            continue  # already migrated or manually created
        legacy = []
        if poll.option_one:
            legacy.append(('option_one', poll.option_one, poll.option_one_count))
        if poll.option_two:
            legacy.append(('option_two', poll.option_two, poll.option_two_count))
        if poll.option_three:
            legacy.append(('option_three', poll.option_three, poll.option_three_count))
        for order, (_field, text, count) in enumerate(legacy):
            Option.objects.create(poll=poll, text=text, votes=count, order=order)

class Migration(migrations.Migration):
    dependencies = [
        ('main', '0004_alter_vote_choice_option_vote_option'),
    ]

    operations = [
        migrations.RunPython(create_options, migrations.RunPython.noop),
    ]
