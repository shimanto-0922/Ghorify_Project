from django.db import migrations


def phone_as_username(apps, schema_editor):
    # There is no separate username any more: users log in with their phone number
    User = apps.get_model('accounts', 'User')
    for user in User.objects.exclude(phone=''):
        if user.username == user.phone:
            continue
        if User.objects.filter(username=user.phone).exists():
            continue
        if user.is_superuser:
            continue
        user.username = user.phone
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_remove_nid_number'),
    ]

    operations = [
        migrations.RunPython(phone_as_username, migrations.RunPython.noop),
    ]
