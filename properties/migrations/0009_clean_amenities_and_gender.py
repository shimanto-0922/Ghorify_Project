from django.db import migrations


def clean_data(apps, schema_editor):
    Amenity = apps.get_model('properties', 'Amenity')
    Property = apps.get_model('properties', 'Property')
    # These amenities are no longer offered
    Amenity.objects.filter(name__in=['Generator backup', 'Prayer space']).delete()
    # "Who can rent" is only used for bachelor posts now
    Property.objects.exclude(category='bachelor').update(tenant_gender='any')


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0008_remove_unused_fields'),
    ]

    operations = [
        migrations.RunPython(clean_data, migrations.RunPython.noop),
    ]
